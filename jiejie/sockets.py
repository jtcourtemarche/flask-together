#!/usr/bin/python
import json
import re
import traceback

from flask import request
from flask import session
from flask_login import current_user
from flask_socketio import emit
from flask_socketio import join_room

import jiejie.models as models
from extensions import db
from extensions import fm
from extensions import pipe
from extensions import socketio
from jiejie.utils import TwitchAPI
from jiejie.utils import Video
from jiejie.utils import YoutubeAPI

"""

    USERS

"""

# Generate a list of currently online/offline users from cache 'server:logged'
# Every item in list contains tuple
#   1: username
#   2: online status (0 = offline, 1 = online)
# Triggered whenever a user joins or leaves the page


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

# Retrieve most recent object from history


def get_most_recent_video():
    history_schema = models.HistorySchema()
    history = models.History.query.order_by(db.text('-id')).first()
    history = history_schema.dump(history).data

    # Return last item
    return history

# Retrieve last 20 objects from history


def get_recent_history():
    history_schema = models.HistorySchema(many=True)
    history = models.History.query.order_by(db.text('id')).all()
    history = history_schema.dump(history).data[20:]
    """
    # Load only 20 videos if there are more than 20 DB entries
    if len(history) > 20:
        history = history[-20:]
    """
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

    most_recent_video = get_most_recent_video()

    if most_recent_video['player'] == 'twitch':
        emit('server:sync', {
            'history': get_recent_history(),
            'most_recent': most_recent_video,
            'sid': request.sid,
        }, room=request.sid)
    else:
        emit('server:sync', {
            'history': get_recent_history(),
            'most_recent': most_recent_video,
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
    # Check what player the link is:
    if 'twitch.tv/' in data['url']:
        player = 'twitch'
    else:
        # Extract video id from Youtube url
        yt_re = r'(https?://)?(www\.)?youtube\.(com|nl|ca)/watch\?v=([-\w]+)'
        user_input = re.findall(yt_re, data['url'])

        player = 'youtube'

    # Check if user wants to play a specific video link
    if player == 'twitch':
        channel = data['url'].split('twitch.tv/')[1].strip()
        channel_data = TwitchAPI.get_channel_data(channel)

        if not channel_data:
            channel_title = channel
            channel_thumbnail = 'https://static-cdn.jtvnw.net/ttv-static/404_preview-320x180.jpg'
        else:
            channel_title = channel_data['title']
            channel_thumbnail = channel_data['thumbnail_url'].replace(
                '{width}', '320').replace('{height}', '180')

        channel_avatar = TwitchAPI.get_channel_avatar(channel)

        # Create history object
        history = models.History(
            video_id=channel,
            video_title=channel_title,
            video_thumbnail=channel_thumbnail,
            twitch_avatar=channel_avatar,
            user_id=data['user']['id'],
            player='twitch',
        )

        db.session.add(history)
        db.session.commit()

        emit('server:play-new', {
            'player': player,
            'channel': channel,
            'title': channel_title,
            'avatar': channel_avatar,
            'history': get_most_recent_video(),
        }, broadcast=True)
    elif user_input != []:
        if player == 'youtube':
            # Create video object
            video = Video(user_input[0][3])

            # Create history object
            history = models.History(
                video_id=video.id,
                video_title=video.title,
                video_thumbnail=video.thumbnail,
                user_id=data['user']['id'],
                player='youtube'
            )

            db.session.add(history)
            db.session.commit()

            emit('server:play-new', {
                'author': video.author,
                'content': video.content,
                'history': get_most_recent_video(),
                'id': video.id,
                'title': video.title,
                'player': player,
            }, broadcast=True)
    # Channel URL entered into search bar
    elif '/channel/' in data['url']:
        results = YoutubeAPI.check_channel(data['url'])
        emit('server:serve-list', results, room=request.sid)
    # Standard Youtube search query
    else:
        results = YoutubeAPI.search(data['url'], (0, 10))
        emit('server:serve-list', (results, False, 1), room=request.sid)


# Handles loading more results for a Youtube search
@socketio.on('user:search-load-more')
def search_load_more(data):
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
    get_cache = pipe.get(current_user.username).execute()

    d = json.loads(d['data'])

    scrobbleable = False

    # Checks if the video played can be scrobbled
    if get_cache != [b''] and get_cache != [None]:
        # Send scrobble to API then clear from cache
        fm.scrobble(current_user.username)
        pipe.set(current_user.username, '').execute()
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
        pipe.set(current_user.username, '').execute()


"""

    CONTROLS

"""

# Play
@socketio.on('user:play')
def play(data):
    emit('server:play', {'time': data['time']}, broadcast=True)


# Pause
@socketio.on('user:pause')
def pause(data):
    # Pausing video locally for user who requested pause makes interface slightly smoother
    emit('server:pause', {'time': data['time']}, broadcast=True)


# Playback rate
@socketio.on('user:rate')
def handle_rate(data):
    emit('server:rate', {'rate': data['rate']}, broadcast=True)


# Skip
@socketio.on('user:skip')
def handle_skip(data):
    emit('server:skip', {'time': data['time']}, broadcast=True)


# Error handling
@socketio.on_error()
def error_handler(e):
    print(e.args, type(e).__name__)
    traceback.print_exc()
