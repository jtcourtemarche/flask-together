#!/usr/bin/python

"""

    youtube de locke
    by jtcourtemarche

    MMMMMMMMNNMMMMMNNMMMMMMMM
    MMMMMMMMs:ys+ys:yMMMMMMMM
    MMMMMMMMhoo: +o+dMMMMMMMM
    MMMMMMMNoos::ssooNMMMMMMM
    MMMMMNdyoooohsoooymNMMMMM
    MMMNyo++++ooyyo+++osdMMMM
    MMMso++++++++++++++oodMMM
    MMmoo+++++++++++++++osMMM
    MMmoo+++++++++++++++osMMM
    MMMyo++++++++++++++oomMMM
    MMMNho++++++++++++osmMMMM
    MMMMMNmhhhhhhhhhhdmMMMMMM
    
"""

import os
import re

from flask import Flask, redirect

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

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://%(user)s:\
%(password)s@%(host)s:%(port)s/%(dbname)s' % POSTGRES

# Logging
import logging

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Load modules
import extensions

from lib import models
from lib import sockets
from lib.views import urls

# App import functions
def init_db():
    extensions.db.create_all()
    extensions.db.session.commit()
    print('Complete')

def destroy_db():
    extensions.db.drop_all()
    extensions.db.session.commit()
    print('Complete')

def add_user(username, password):
    u = models.User(username=username)
    u.setpass(password)

    extensions.db.session.add(u)
    extensions.db.session.commit()

    print('Added user: {}'.format(u))

def del_user(username='', user_id=None):
    if username:
        u = models.User.query.filter_by(username=username).first()

        extensions.db.session.delete(u)
        extensions.db.session.commit()
    elif user_id:
        u = models.User.query.get(user_id)

        extensions.db.session.delete(u)
        extensions.db.session.commit()
    else:
        print('Invalid parameters')

# Register views
app.register_blueprint(urls)

@extensions.login_manager.user_loader
def load_user(user_id):
    return models.User.query.get(int(user_id))

@app.errorhandler(404)
def page_not_found(error):
    return redirect('/')

if __name__ == '__main__':
    socketio.run(app)
