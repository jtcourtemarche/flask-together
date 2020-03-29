#!/usr/bin/python
from functools import wraps
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
import jiejie.youtube as youtube
from extensions import fm
from extensions import pipe
from extensions import socketio

# TODO: namespaces
# TODO: fix broken disconnect events

# DECORATORS 

def login_required(event):
    @wraps(event)
    def inner(*args, **kwargs):
        if not current_user.is_authenticated:
            disconnect()
        else:
            return event(*args, **kwargs)
    return inner 


def room_exists(event):
    @wraps(event)
    def inner(room_id, *args, **kwargs):
        if type(room_id) is int:
            room = models.Room.query.get(room_id)

            # TODO: check if room is private and current_user is in it
            if room and room.public:
                return event(str(room_id), room=room, *args, **kwargs)
        disconnect()
    return inner

# USER HANDLERS

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
    # disconnect from all rooms
    for room in models.Room.query.with_parent(current_user):
        # remove from active users
        pipe.srem(
            'room:' + str(room.id),
            current_user.name
        )

        # notify room that user disconnected
        emit('server:disconnected', {
            'user_name': current_user.name,
        }, room=str(room.id))

    # clear lastfm cache for user
    if fm.enabled:
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
@socketio.on('user:signal-preload')
@login_required
@room_exists
def signal_preload(room_id, room=None):
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
        wrapper = youtube.VideoWrapper(user_input[0][3])
        if not wrapper:
            return # do nothing if can't connect to youtube api

        # create video object
        video = models.Video(
            watch_id=wrapper.watch_id,
            title=wrapper.title,
            thumbnail=wrapper.thumbnail,
            user_id=data['user']['id'],
            room_id=room_id
        )

        # save video object to database
        models.db.session.add(video)
        models.db.session.commit()

        emit('server:play-new', {
            'most_recent': room.get_most_recent_video(),
            'metadata': wrapper.return_as_dict()
        }, room=room_id)
    elif '/channel/' in data['url']:
        # channel URL entered into search bar
        results = youtube.check_channel(data['url'])
        emit('server:serve-list', results, room=request.sid)
    else:
        # standard Youtube search query
        results = youtube.search(data['url'], (0, 10))
        emit('server:serve-list', (results, False, 1), room=request.sid)


# Handles loading more results for a Youtube search
@socketio.on('user:search-load-more')
@room_exists
def search_load_more(room_id, data, room=None):
    p = data['page']
    if p != 0:
        results = youtube.search(data['url'], (p * 10, ((p)+1) * 10))
    else:
        results = youtube.search(data['url'], (0, 10))

    emit('server:serve-list', (results, True, p+1), room=request.sid)


# This is for managing cache for LastFM scrobbling
@socketio.on('user:play-callback')
def play_new_handler(d):
    # Scrobbling
    if fm.enabled:
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
        if fm.enabled:
            if current_user.lastfm_connected():
                duration = d['duration']
                fm.update_now_playing(artist, track, current_user, duration)
            else:
                # Denote that nothing is being scrobbled anymore
                pipe.set(current_user.name, '').execute()


# VIDEO CONTROLS 

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
