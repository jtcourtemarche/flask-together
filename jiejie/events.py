#!/usr/bin/python
import functools
import json
import re
import traceback

from flask import request
from flask_login import current_user
from flask_socketio import disconnect
from flask_socketio import emit
from flask_socketio import join_room
from flask_socketio import leave_room

import jiejie.models as models
from extensions import fm
from extensions import pipe
from extensions import socketio
from jiejie.youtube import YoutubeAPI
from jiejie.youtube import YoutubeVideoWrapper

# TODO: namespaces
# TODO: fix broken disconnect events

# decorators

# tests if current_user is logged in


def login_required(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            disconnect()
        else:
            return f(*args, **kwargs)
    return wrapped

# tests if passed room_id is valid, returns string room_id and room object


def room_exists(f):
    @functools.wraps(f)
    def wrapped(room_id, *args, **kwargs):
        if not type(room_id) is int:
            disconnect()
            return None

        room = models.Room.query.get(room_id)

        # TODO: check if room is private and current_user is in it
        if not room or not room.public:
            disconnect()
            return None

        return f(str(room_id), room=room, *args, **kwargs)
    return wrapped

# user handlers

# handle when a user joins
@socketio.on('user:connected')
@login_required
@room_exists
def handle_connect(room_id, room=None):
    join_room(room_id)

    # add to active users
    pipe.sadd(
        'room:' + room_id,
        current_user.name
    ).execute()

    # notify active users in room that a user has joined
    emit('server:user-joined',
         {'online_users': room.get_online_users()},
         room=room_id,
         include_self=False
         )

    # sync new user w/ room
    emit('server:sync', {
        'most_recent': room.get_most_recent_video(),
        'online_users': room.get_online_users()
    }, room=request.sid)


# Handle when a user disconnects
@socketio.on('disconnected')
@login_required
def handle_disconnect():
    # leave all rooms
    for room in models.Room.query.with_parent(current_user):
        room_id = str(room.id)

        leave_room(room_id)

        # remove from active users
        pipe.srem(
            'room:' + room_id,
            current_user.name
        )

        emit('server:disconnected', {
            'user_name': current_user.name,
        }, room=room_id)

    # Clear LastFM cache for user
    pipe.set('lastfm:'+current_user.name, '')
    pipe.execute()


"""
    This is the path that preloaded data takes:

    New User -------> Server --------> Online User
        ^                                   |
        |                                   |
        ------------- Server <--------------|

    Initialize a request to an online user to get the currently playing video's time
    If there are no online users, the video will play at 0:00 by default.
"""
@socketio.on('user:init-preload')
@login_required
@room_exists
def init_preload(room_id, room=None):
    emit('server:request-data', {
        'sid': request.sid,
    }, room=room_id, include_self=False)


# Gather then send preload data to the newly joined user
@socketio.on('user:preload-info')
@login_required
def preload(data):
    emit('server:preload', data, room=data['sid'])


# process new video being played.
@socketio.on('user:play-new')
@login_required
@room_exists
def play_new(room_id, data, room=None):
    # extract unique_id from Youtube url
    yt_regex = r'(https?://)?(www\.)?youtube\.(com|nl|ca)/watch\?v=([-\w]+)'
    user_input = re.findall(yt_regex, data['url'])

    # check if user wants to play a specific video link
    if user_input:
        # create video wrapper to parse video data
        wrapper = YoutubeVideoWrapper(user_input[0][3])

        # create video object
        video = models.Video(
            watch_id=wrapper.id,
            title=wrapper.title,
            thumbnail=wrapper.thumbnail,
            user_id=data['user']['id'],
            room_id=room_id
        )

        # save video object to database
        models.db.session.add(video)
        models.db.session.commit()

        emit('server:play-new', {
            'author': wrapper.author,
            'content': wrapper.content,
            'most_recent': room.get_most_recent_video(),
            'id': wrapper.id,
            'title': wrapper.title,
        }, room=room_id)
    elif '/channel/' in data['url']:
        # channel URL entered into search bar
        results = YoutubeAPI.check_channel(data['url'])
        emit('server:serve-list', results, room=request.sid)
    else:
        # standard Youtube search query
        results = YoutubeAPI.search(data['url'], (0, 10))
        emit('server:serve-list', (results, False, 1), room=request.sid)


# Handles loading more results for a Youtube search
@socketio.on('user:search-load-more')
@room_exists
def search_load_more(room_id, data, room=None):
    p = data['page']
    if p != 0:
        results = YoutubeAPI.search(data['url'], (p * 10, ((p)+1) * 10))
    else:
        results = YoutubeAPI.search(data['url'], (0, 10))

    emit('server:serve-list', (results, True, p+1), room=request.sid)


# This is for managing cache for LastFM scrobbling
@socketio.on('user:play-callback')
def play_new_handler(d):
    # Scrobbling
    get_cache = pipe.get(current_user.name).execute()

    d = json.loads(d['data'])

    scrobbleable = False

    # Checks if the video played can be scrobbled
    if get_cache != [b''] and get_cache != [None]:
        # Send scrobble to API then clear from cache
        fm.scrobble(current_user.name)
        pipe.set(current_user.name, '').execute()
    elif len(d['title'].split(' - ')) == 2:
        # Check if song
        title = d['title'].split(' - ')
        track = re.sub(r'\([^)]*\)', '', title[1])
        artist = title[0]
        scrobbleable = True
    elif len(d['title'].split('- ')) == 2:
        # Check if song
        title = d['title'].split('- ')
        track = re.sub(r'\([^)]*\)', '', title[1])
        artist = title[0]
        scrobbleable = True
    elif ' - Topic' in d['author']:
        # Youtube "Topic" music videos
        track = d['title']
        artist = d['author'].rstrip(' - Topic')
        scrobbleable = True

    if scrobbleable:
        emit('server:play-new-artist', {
            'artist': fm.get_artist(artist),
        }, broadcast=True)

    # Handle scrobbling after playing video
    if current_user.lastfm_connected():
        duration = d['duration']
        fm.update_now_playing(artist, track, current_user, duration)
    else:
        # Denote that nothing is being scrobbled anymore
        pipe.set(current_user.name, '').execute()


# video controls

# Play
@socketio.on('user:play')
@room_exists
def play(room_id, data, room=None):
    emit('server:play', {'time': data['time']}, room=room_id)


# Pause
@socketio.on('user:pause')
@room_exists
def pause(room_id, data, room=None):
    # Pausing video locally for user who requested pause makes interface slightly smoother
    emit('server:pause', {'time': data['time']}, room=room_id)


# Playback rate
@socketio.on('user:rate')
@room_exists
def handle_rate(room_id, data, room=None):
    emit('server:rate', {'rate': data['rate']}, room=room_id)


# Skip
@socketio.on('user:skip')
@room_exists
def handle_skip(room_id, data, room=None):
    emit('server:skip', {'time': data['time']}, room=room_id)


# Error handling
@socketio.on_error()
def error_handler(e):
    print(e.args, type(e).__name__)
    traceback.print_exc()
