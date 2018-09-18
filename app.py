#!/usr/bin/python

"""

    youtube de locke
    by jtcourtemarche

"""

import os
import re
import sqlite3

from flask import Flask, redirect
from flask_login import LoginManager, current_user
from flask_marshmallow import Marshmallow
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from api import SECRET_KEY, POSTGRES

# Initializers

app = Flask(__name__)

app.config.update(
    TEMPLATES_AUTO_RELOAD=True,
    SERVER_HOST='0.0.0.0:5000',
    DEBUG=True,
    TESTING=True,
    SECRET_KEY=SECRET_KEY,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)

"""
Example postgres import

POSTGRES = {
    'user': 'postgres',
    'pw': 'password',
    'db': 'database name',
    'host': 'localhost',
    'port': '5432',
}
"""

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://%(user)s:\
%(pw)s@%(host)s:%(port)s/%(db)s' % POSTGRES

import logging

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

login_manager = LoginManager()
login_manager.session_protection = "basic"
login_manager.init_app(app)

db = SQLAlchemy(app)
ma = Marshmallow(app)

migrate = Migrate(app, db)

socketio = SocketIO(app)

# Main imports

from lastfm import FM
fm = FM()

import models
import sockets
from views import urls

app.register_blueprint(urls)

@login_manager.user_loader
def load_user(user_id):
    return models.User.query.get(int(user_id))

@app.errorhandler(404)
def page_not_found(error):
    return redirect('/')

if __name__ == '__main__':
    socketio.run(app)
