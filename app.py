#!/usr/bin/python

"""
    youtube de locke
    by jtcourtemarche
"""

from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, session
from flask_socketio import SocketIO, emit, join_room
from flask_login import LoginManager, current_user
from flask_marshmallow import Marshmallow
import sqlite3
import re
import tools
import os

from api import SECRET_KEY

app = Flask(__name__)

app.config.update(
    TEMPLATES_AUTO_RELOAD=True,
    SERVER_HOST='0.0.0.0:5000',
    DEBUG=True,
    TESTING=True,
    SECRET_KEY=SECRET_KEY,
)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///watch.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

login_manager = LoginManager()
login_manager.session_protection = "basic"
login_manager.init_app(app)

db = SQLAlchemy(app)
ma = Marshmallow(app)
socketio = SocketIO(app)

# Sockets -------------------------------------------------->
import models

clients = []
logged_in = []

@socketio.on('joined')
def handle_connect():
    # New connection handler
    clients.append(request.sid)
    room = session.get('room')
    join_room(room)

    if current_user.is_authenticated:
        logged_in.append(current_user.username)
    
    active_users = [()]
    for user in models.User.query.all():
        if user.username in logged_in:
            active_users.append((user.username, 1))
        else:
            active_users.append((user.username, 0))

    emit('new-user', {
        'active_users': active_users
    }, broadcast=True)

    history_schema = models.HistorySchema()

    try:
        most_recent = models.History.query.order_by(models.History.date).all()[-1]
        most_recent = history_schema.dump(most_recent).data
    except:
        most_recent = None

    history_schema = models.HistorySchema(many=True)
    history = models.History.query.order_by('date').all()
    history = history_schema.dump(history).data

    emit('new-user-sync', {
        'most_recent': most_recent,
        'history': history,
    }, room=clients[-1])

@socketio.on('disconnect')
def handle_dc():
    for i in enumerate(logged_in):
        if current_user.username == i[1]:
            del logged_in[i[0]]

    active_users = [()]
    for user in models.User.query.all():
        if user.username in logged_in:
            active_users.append((user.username, 1))
        else:
            active_users.append((user.username, 0))

    emit('user-disconnected', {'username':current_user.username, 'active_users':active_users}, broadcast=True)
    
    cin = clients.index(request.sid)
    del clients[cin]

# Play / Pause
@socketio.on('client-play')
def play(data):
    emit('server-play', data["time"], broadcast=True)
    #print('Play @ ' + str(data["time"]))

@socketio.on('client-pause')
def pause(data):
    emit('server-pause', data["time"], broadcast=True)
    #print('Pause @ ' + str(data["time"]))

@socketio.on('client-play-new')
def play_new(data):
    # Extract video id from yt url
    yt_re = r'(https?://)?(www\.)?youtube\.(com|nl|ca)/watch\?v=([-\w]+)'
    yt_id = re.findall(yt_re, data["url"])

    # Check if valid youtube url, if not serve search results
    if yt_id != []:
        yt = tools.check_yt(yt_id[0][3])['items'][0]
        h = models.History(
            video_id = yt['id'],
            video_date = yt['snippet']['publishedAt'],
            video_title = yt['snippet']['title'],
            video_thumbnail = yt['snippet']['thumbnails']['default']['url'],
            user_id=data['user']['id'],
        )

        db.session.add(h)
        db.session.commit()

        history_schema = models.HistorySchema(many=True)

        history = models.History.query.all()
        history = history_schema.dump(history).data

        emit('server-play-new', {'id': h.video_id, 'history': history, 'user': data['user']['id']},  broadcast=True)
    elif '/channel/' in data['url']:
        results = tools.check_channel_yt(data['url'])
        emit('server-serve-list', results, room=request.sid)
    else:
        results = tools.search_yt(data['url'])
        emit('server-serve-list', results, room=request.sid)

@socketio.on('client-rate')
def handle_rate(data):
    emit('server-rate', data["rate"], broadcast=True)

@socketio.on('client-skip')
def handle_skip_to(data):
    emit('server-skip', data["time"], broadcast=True)

@socketio.on('client-skip')
def handle_skip(data):
    emit('server-skip', data["time"], broadcast=True)

# Error handling
@socketio.on_error()
def error_handler(e):
    print(e)

from views import urls

app.register_blueprint(urls)

@login_manager.user_loader
def load_user(user_id):
    return models.User.query.get(int(user_id))

if __name__ == '__main__':
    socketio.run(app)
