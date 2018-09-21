#!/usr/bin/python

import re
import time
import json
from flask import request, session
from flask_login import current_user
from flask_socketio import emit, join_room

import utils
from app import db, fm, socketio, pipe
import models

clients = []
logged_in = []

def get_active_users():
    active_users = [(current_user.username, 1)]
    
    for user in models.User.query.all():
        if user.username in logged_in and user.username != current_user.username:
            active_users.append((user.username, 1))
        elif user.username != current_user.username:
            active_users.append((user.username, 0))

    return active_users

@socketio.on('user:joined')
def handle_connect():
    # New connection handler
    clients.append(request.sid)
    room = session.get('room')
    join_room(room)

    if current_user.is_authenticated and current_user.username not in logged_in:
        logged_in.append(current_user.username)

    active_users = get_active_users()

    emit('server:new-user', {
        'active_users': active_users
    }, broadcast=True)

    history_schema = models.HistorySchema()

    try:
        most_recent = models.History.query.order_by(db.text('-id')).first()
        most_recent = history_schema.dump(most_recent).data
        most_recent_username = models.User.query.get(
            most_recent['user']).username
    except:
        most_recent = None
        most_recent_username = None

    history_schema = models.HistorySchema(many=True)
    history = models.History.query.order_by('date').limit(20).all()
    history = history_schema.dump(history).data

    emit('server:sync', {
        'most_recent': most_recent,
        'most_recent_username': most_recent_username,
        'history': history[:20], 
        'sid': request.sid,
    }, room=clients[-1])


@socketio.on('user:init-preload')
def init_preload():
    if [x for x in clients if x != request.sid] != []:
        emit('server:request-data', {
            'sid': request.sid,
        }, broadcast=True, include_self=False)


@socketio.on('user:preload-info')
def preload(data):
    emit('server:preload', data, room=data['sid'])


@socketio.on('disconnect', namespace='/')
def handle_dc():
    # Update list of active users
    for i in enumerate(logged_in):
        if current_user.username == i[1]:
            del logged_in[i[0]]

    active_users = get_active_users()

    # Clear LastFM cache for user
    pipe.set(current_user.username, '')
    pipe.execute()

    emit('server:disconnected', {'username': current_user.username,
                               'active_users': active_users}, broadcast=True)

    cin = clients.index(request.sid)
    del clients[cin]

# Play / Pause

@socketio.on('user:play')
def play(data):
    emit('server:play', data["time"], broadcast=True)


@socketio.on('user:pause')
def pause(data):
    emit('server:pause', data["time"], broadcast=True)


@socketio.on('user:play-new')
def play_new(data):
    # Extract video id from yt url
    yt_re = r'(https?://)?(www\.)?youtube\.(com|nl|ca)/watch\?v=([-\w]+)'
    yt_id = re.findall(yt_re, data["url"])

    # Check if valid youtube url, if not serve search results
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
        history_schema = models.HistorySchema(many=True)
        history = models.History.query.limit(20).all()
        history = history_schema.dump(history).data

        emit('server:play-new', {
            'id': items['id'],
            'title': items['snippet']['title'],
            'history': history, 
            'user': user.username,
            'content': content,
        }, broadcast=True)

    elif '/channel/' in data['url']:
        results = utils.check_channel_yt(data['url'])
        emit('server:serve-list', results, room=request.sid)
    else:
        results = utils.search_yt(data['url'])
        emit('server:serve-list', results, room=request.sid)

@socketio.on('user:play-callback')
def play_new_handler(d):
    # Scrobbling
    pipe.get(current_user.username)
    get_cache = pipe.execute()

    d = json.loads(d['data'])

    if get_cache != [b'']:
        # Send scrobble to API then clear from cache
        fm.scrobble(current_user.username)
        pipe.set(current_user.username, '')
        pipe.execute()
    
    if len(d['title'].split(' - ')) == 2:
        # Check if song
        title = d['title'].split(' - ')
        artist = title[0]
        name = re.sub(r'\([^)]*\)', '', title[1])

        emit('server:play-new-artist', {
            'artist': fm.get_artist(artist),
        }, broadcast=True)

        # Handle scrobbling after playing video

        if current_user.lastfm_connected():
            duration = d['content']['contentDetails']['duration']
            fm.update_now_playing(artist, name, current_user, duration)
    else:
        # Denote that nothing is being scrobbled anymore
        pipe.set(current_user.username, '')
        pipe.execute()    

@socketio.on('user:rate')
def handle_rate(data):
    emit('server:rate', data["rate"], broadcast=True)

@socketio.on('user:skip')
def handle_skip(data):
    emit('server:skip', data["time"], broadcast=True)

# Error handling

@socketio.on_error()
def error_handler(e):
    print(e.args, type(e).__name__)
