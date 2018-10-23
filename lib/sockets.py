#!/usr/bin/python

import json
import re
import time
import traceback

from extensions import db, fm, socketio, pipe, r
from flask import request, session
from flask_login import current_user
from flask_socketio import emit, join_room
import lib.models as models
import lib.utils as utils

"""

    USERS

"""

# Generate a list of currently online/offline users from cache 'server:logged'
# Every item in list contains tuple 
#   1: username
#   2: online status (0 = offline, 1 = online)
#
def get_active_users():
    active_users = []
    
    # Retrieve server:logged from cache    
    logged_in = pipe.lrange('server:logged', 0, -1).execute()[0]
    # Decode byte string from redis to Python string
    logged_in = [user.decode('utf-8') for user in logged_in]
    # Generate list of online/offline users
    #   1 => Online
    #   2 => Offline
    for user in models.User.query.all():
        if user.username in logged_in:
            active_users.append((user.username, 1))
        else:
            active_users.append((user.username, 0))

    return active_users


# Retrieve last 20 objects from history
def get_recent_history():
    history_schema = models.HistorySchema(many=True)
    history = models.History.query.order_by(db.text('id')).all()
    history = history_schema.dump(history).data

    # Load only 20 videos if there are more than 20 DB entries
    if len(history) > 20:
        history = history[-20:]

    return history


# Handle when a user joins
@socketio.on('user:joined')
def handle_connect():
    # New connection handler
    room = session.get('room')
    join_room(room)

    logged_in = pipe.lrange('server:logged', 0, -1).execute()

    if logged_in == []:
        # Checks if no users are cached
        pipe.lpush('server:logged', current_user.username).execute()
    elif current_user.username not in logged_in[0]:
        pipe.lpush('server:logged', current_user.username).execute()

    active_users = get_active_users()

    emit('server:new-user', {
        'active_users': active_users
    }, broadcast=True)

    history_schema = models.HistorySchema()

    try:
        # Get most recent ID
        most_recent = models.History.query.order_by(db.text('-id')).first()
        most_recent = history_schema.dump(most_recent).data
        most_recent_username = models.User.query.get(most_recent['user']).username
    except KeyError:
        most_recent = None
        most_recent_username = None

    emit('server:sync', {
        'history': get_recent_history(), 
        'most_recent_username': most_recent_username,
        'most_recent': most_recent,
        'sid': request.sid,
    }, room=request.sid)


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
def init_preload():
    emit('server:request-data', {
        'sid': request.sid,
    }, broadcast=True, include_self=False)


# Gather then send preload data to the newly joined user
@socketio.on('user:preload-info')
def preload(data):
    emit('server:preload', data, room=data['sid'])


# Handle when a user disconnects
@socketio.on('disconnect', namespace='/')
def handle_dc():
    # Update list of active users
    logged_in = pipe.lrange('server:logged', 0, -1).execute()[0]

    # Convert to regular string
    logged_in = [user.decode('utf-8') for user in logged_in]

    if current_user.username in logged_in:
        # remove all matching keys from redis 
        pipe.lrem('server:logged', 0, current_user.username).execute()

    # Clear LastFM cache for user
    pipe.set(current_user.username, '').execute()

    active_users = get_active_users()
    
    emit('server:disconnected', {
        'active_users': active_users,
        'username': current_user.username,
    }, broadcast=True)

"""

    YOUTUBE

"""

# Process new video being played.
@socketio.on('user:play-new')
def play_new(data):
    if 'twitch.tv' in data['url']:
        channel = data['url'].split('/')[-1]

        emit('server:play-new', {
            'channel': channel,
            'history': get_recent_history(),
            'player': 'twitch',
        }, broadcast=True)
    else:
        # Extract video id from Youtube url
        yt_re = r'(https?://)?(www\.)?youtube\.(com|nl|ca)/watch\?v=([-\w]+)'
        yt_id = re.findall(yt_re, data['url'])

        # Play specific video ID
        if yt_id != []:
            yt = utils.check_yt(yt_id[0][3])

            items = yt.get_items()
            content = yt.get_content()

            h = models.History(
                video_id=items['id'],
                video_date=items['snippet']['publishedAt'],
                video_title=items['snippet']['title'],
                video_thumbnail=items['snippet']['thumbnails']['default']['url'],
                user_id=data['user']['id'],
            )

            user = models.User.query.get(data['user']['id'])
            db.session.add(h)
            db.session.commit()

            emit('server:play-new', {
                'author': items['snippet']['channelTitle'],
                'content': content,
                'history': get_recent_history(), 
                'id': items['id'],
                'player': 'youtube',
                'title': items['snippet']['title'],
                'user': user.username,
            }, broadcast=True)
        # Channel URL entered into search bar
        elif '/channel/' in data['url']:
            results = utils.check_channel_yt(data['url'])
            emit('server:serve-list', results, room=request.sid)
        # Standard Youtube search
        else:
            results = utils.search_yt(data['url'])
            emit('server:serve-list', results, room=request.sid)


# This is for managing cache for LastFM scrobbling
@socketio.on('user:play-callback')
def play_new_handler(d):
    # Scrobbling
    get_cache = pipe.get(current_user.username).execute()

    d = json.loads(d['data'])

    if get_cache != [b''] and get_cache != [None]:
        # Send scrobble to API then clear from cache
        fm.scrobble(current_user.username)
        pipe.set(current_user.username, '').execute()
    
    if len(d['title'].split(' - ')) == 2 or \
       len(d['title'].split('- ')) == 2 or \
       ' - Topic' in d['author']:

        if len(d['title'].split(' - ')) == 2:
            # Check if song
            title = d['title'].split(' - ')
            track = re.sub(r'\([^)]*\)', '', title[1])
            artist = title[0]
        elif len(d['title'].split('- ')) == 2:
            # Check if song
            title = d['title'].split('- ')
            track = re.sub(r'\([^)]*\)', '', title[1])
            artist = title[0]
        elif ' - Topic' in d['author']:
            # Youtube "Topic" music videos
            track = d['title']
            artist = d['author'].strip(' - Topic')            

        emit('server:play-new-artist', {
            'artist': fm.get_artist(artist),
        }, broadcast=True)

        # Handle scrobbling after playing video
        if current_user.lastfm_connected():
            duration = d['content']['contentDetails']['duration']
            fm.update_now_playing(artist, track, current_user, duration)
    else:
        # Denote that nothing is being scrobbled anymore
        pipe.set(current_user.username, '').execute()

"""

    CONTROLS

"""

# Play
@socketio.on('user:play')
def play(data):
    emit('server:play', {'time':data["time"]}, broadcast=True)


# Pause
@socketio.on('user:pause')
def pause(data):
    # Pausing video locally for user who requested pause makes interface slightly smoother
    emit('server:pause', {'time':data["time"]}, broadcast=True, include_self=False)


# Playback rate
@socketio.on('user:rate')
def handle_rate(data):
    emit('server:rate', {'rate':data["rate"]}, broadcast=True)


# Skip
@socketio.on('user:skip')
def handle_skip(data):
    emit('server:skip', {'time':data["time"]}, broadcast=True)


# Error handling
@socketio.on_error()
def error_handler(e):
    print(e.args, type(e).__name__)
    traceback.print_exc()
