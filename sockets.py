#!/usr/bin/python

import re
from flask import request, session
from flask_login import current_user
from flask_socketio import emit, join_room

import utils
from app import db, fm, socketio
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

@socketio.on('joined')
def handle_connect():
    # New connection handler
    clients.append(request.sid)
    room = session.get('room')
    join_room(room)

    if current_user.is_authenticated and current_user.username not in logged_in:
        logged_in.append(current_user.username)

    active_users = get_active_users()

    emit('new-user', {
        'active_users': active_users
    }, broadcast=True)

    history_schema = models.HistorySchema()

    try:
        most_recent = models.History.query.order_by(
            models.History.date).all()[-1]
        most_recent = history_schema.dump(most_recent).data
        most_recent_username = models.User.query.get(
            most_recent['user']).username
    except:
        most_recent = None

    history_schema = models.HistorySchema(many=True)
    history = models.History.query.order_by('date').all()
    history = history_schema.dump(history).data

    emit('new-user-sync', {
        'most_recent': most_recent,
        'most_recent_username': most_recent_username,
        'history': history,
        'sid': request.sid,
    }, room=clients[-1])


@socketio.on('init-preload')
def init_preload():
    if [x for x in clients if x != request.sid] != []:
        emit('request-data', {
            'sid': request.sid,
        }, broadcast=True, include_self=False)


@socketio.on('preload-info')
def preload(data):
    emit('preload', data, room=data['sid'])


@socketio.on('disconnect', namespace='/')
def handle_dc():
    for i in enumerate(logged_in):
        if current_user.username == i[1]:
            del logged_in[i[0]]

    active_users = get_active_users()

    emit('user-disconnected', {'username': current_user.username,
                               'active_users': active_users}, broadcast=True)

    cin = clients.index(request.sid)
    del clients[cin]

# Play / Pause

@socketio.on('client-play')
def play(data):
    emit('server-play', data["time"], broadcast=True)


@socketio.on('client-pause')
def pause(data):
    emit('server-pause', data["time"], broadcast=True)


@socketio.on('client-play-new')
def play_new(data):
    # Extract video id from yt url
    yt_re = r'(https?://)?(www\.)?youtube\.(com|nl|ca)/watch\?v=([-\w]+)'
    yt_id = re.findall(yt_re, data["url"])

    # Check if valid youtube url, if not serve search results
    if yt_id != []:
        yt = utils.check_yt(yt_id[0][3])['items'][0]

        h = models.History(
            video_id=yt['id'],
            video_date=yt['snippet']['publishedAt'],
            video_title=yt['snippet']['title'],
            video_thumbnail=yt['snippet']['thumbnails']['default']['url'],
            user_id=data['user']['id'],
        )

        user = models.User.query.get(data['user']['id'])
        db.session.add(h)
        db.session.commit()
        history_schema = models.HistorySchema(many=True)
        history = models.History.query.all()
        history = history_schema.dump(history).data

        emit('server-play-new', {
            'id': h.video_id,
            'history': history, 
            'user': user.username,
        }, broadcast=True)

        if " - " in yt['snippet']['title']:
            # Check if song
            title = yt['snippet']['title'].split(' - ')
            artist = title[0]
            name = title[1]

            emit('server-play-new-artist', {
                'artist': fm.get_artist(artist),
            }, broadcast=True)

    elif '/channel/' in data['url']:
        results = utils.check_channel_yt(data['url'])
        emit('server-serve-list', results, room=request.sid)
   
    else:
        results = utils.search_yt(data['url'])
        emit('server-serve-list', results, room=request.sid)

@socketio.on('client-rate')
def handle_rate(data):
    emit('server-rate', data["rate"], broadcast=True)

@socketio.on('client-skip')
def handle_skip(data):
    emit('server-skip', data["time"], broadcast=True)

# Error handling

@socketio.on_error()
def error_handler(e):
    print(e)
