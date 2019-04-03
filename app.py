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

from flask import Flask, redirect, render_template
import redis

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

"""
# Logging
import logging

# Write errors to error.log
logging.basicConfig(
    filename='error.log',
    level=logging.ERROR
)
"""

# Load modules
import extensions

from lib import models
from lib import sockets
from lib.views import urls

# Make sure everything works before running
try:
    extensions.r.ping()
    redis_connected = True
except redis.exceptions.ConnectionError:
    redis_connected = False

@extensions.login_manager.user_loader
def load_user(user_id):
    return models.User.query.get(int(user_id))


if redis_connected:
    # Register program's standard views
    app.register_blueprint(urls)
else:
    @app.route('/', defaults={'path':''})
    @app.route('/<path:path>')
    def redis_handler(path):
        return render_template('redis.html')


@app.errorhandler(404)
def page_not_found(error):
    return redirect('/')


if __name__ == '__main__':
    extensions.socketio.run(app)
