#!/usr/bin/python
import json
import re
import traceback
from functools import wraps

from flask import request
from flask_login import current_user
from flask_socketio import disconnect
from flask_socketio import emit
from flask_socketio import join_room

import flask_together.models as models
import flask_together.youtube as youtube
from extensions import fm
from extensions import pipe
from extensions import socketio

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
def on_connect(room_id, room=None):
    join_room(room_id)

    # add to active users
    pipe.sadd(
        'room:' + room_id,
        current_user.name
    ).execute()

    # notify active users in room that a user has joined
    emit('server:user-joined',
         {'online_users': room.online_users, 'sid':  request.sid},
         room=room_id,
         include_self=False,
         callback=time_state_sync
         )
    # wait for proper time/state sync from user
    pipe.set(f'time-state-sync:{request.sid}', 'waiting').execute()

    # sync new user w/ room
    emit('server:sync', {
        'history': room.recent_history,
        'most_recent': room.most_recent_video,
        'online_users': room.online_users
    }, room=request.sid)


"""
    This is the path that time and state data takes:

    New User -------> Room ----------> Online User
        ^                                   |
        |                                   |
        ------------- Server <--------------| callback function

    Initialize a request to an online user to get the currently playing video's time
    If there are no online users, the video will play at 0:00 by default.
"""


def time_state_sync(time, state, sid):
    # ignore data saying video is unplayed
    if time != 0 and state != -1:
        if pipe.get(f'time-state-sync:{sid}').execute()[0]:
            pipe.delete(f'time-state-sync:{sid}').execute()

            emit('server:time-state-sync', {
                'time': time,
                'state': state,
            }, room=sid)


# Handle when a user disconnects
@socketio.on('disconnected')
@login_required
def on_disconnect():
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


# TODO: split search and play-new into different events
# process new video being played.
@socketio.on('user:play-new')
@login_required
@room_exists
def play_new(room_id, url, room=None):
    # play new types: direct link, channel, query
    # TODO: playlists with auto-play?

    # extract unique_id from Youtube url
    yt_regex = r'(https?://)?(www\.)?youtube\.(com|nl|ca)/watch\?v=([-\w]+)'
    user_input = re.findall(yt_regex, url)

    # check if user wants to play a specific video link
    if user_input:
        # create video wrapper to parse video data
        wrapper = youtube.VideoWrapper(user_input[0][3])
        if not wrapper:
            return  # do nothing if can't connect to youtube api

        # create video object
        video = models.Video(
            watch_id=wrapper.watch_id,
            title=wrapper.title,
            thumbnail=wrapper.thumbnail,
            user_id=current_user.id,
            room_id=room_id
        )

        # save video object to database
        models.db.session.add(video)
        models.db.session.commit()

        emit('server:play-new', {
            'most_recent': room.most_recent_video,
            'video': wrapper.return_as_dict()
        }, room=room_id)
    elif '/channel/' in url:
        # channel URL entered into search bar
        results = youtube.check_channel(url)
        emit('server:serve-list', {'results': results,
                                   'append': False, 'page': 1}, room=request.sid)
    else:
        # standard Youtube search query
        results = youtube.search(url, (0, 10))
        emit('server:serve-list', {'results': results,
                                   'append': False, 'page': 1}, room=request.sid)


# Handles loading more results for a Youtube search
@socketio.on('user:search-load-more')
@login_required
@room_exists
def search_load_more(room_id, url, page, room=None):
    if page != 0:
        results = youtube.search(url, (page * 10, ((page)+1) * 10))
    else:
        results = youtube.search(url, (0, 10))

    emit('server:serve-list', {'results': results,
                               'append': True, 'page': page + 1}, room=request.sid)


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
            if current_user.lastfm_connected:
                duration = d['duration']
                fm.update_now_playing(artist, track, current_user, duration)
            else:
                # Denote that nothing is being scrobbled anymore
                pipe.set(current_user.name, '').execute()


# VIDEO CONTROLS

@socketio.on('user:play')
@login_required
@room_exists
def control_play(room_id, time, room=None):
    emit('server:play', {'time': time}, room=room_id)


@socketio.on('user:pause')
@login_required
@room_exists
def control_pause(room_id, time, room=None):
    emit('server:pause', {'time': time}, room=room_id)


@socketio.on('user:rate')
@login_required
@room_exists
def control_playback_rate(room_id, rate, room=None):
    emit('server:rate', {'rate': rate}, room=room_id)


@socketio.on('user:skip')
@login_required
@room_exists
def control_skip(room_id, time, room=None):
    emit('server:skip', {'time': time}, room=room_id)


# Error handling
@socketio.on_error()
def error_handler(e):
    print(e.args, type(e).__name__)
    traceback.print_exc()
