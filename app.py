#!/usr/bin/python
from flask import Flask
from flask import render_template
from flask_migrate import Migrate

import jiejie.models as models
from config import POSTGRES
from config import SECRET_KEY
from config import DEBUG
from extensions import fm
from extensions import login_manager
from extensions import pipe
from extensions import redis_connected
from extensions import socketio
from jiejie.views import urls

# Initialize APP

APP = Flask(__name__)

APP.config.update(
    TEMPLATES_AUTO_RELOAD=True,
    SERVER_HOST='0.0.0.0:5000',
    DEBUG=DEBUG,
    TESTING=False,
    SECRET_KEY=SECRET_KEY,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)

APP.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://%(user)s:\
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

# Start DB
models.db.init_app(APP)
models.ma.init_app(APP)

migrate = Migrate(
    APP, models.db,
    # allow migrate to notice string length changes
    compare_type=True
)

# Tests
# TODO: make this not just one test before views registered
if redis_connected:
    # Register program's standard views
    APP.register_blueprint(urls)
elif not redis_connected:
    # Show only error page
    @APP.route('/', defaults={'path': ''})
    @APP.route('/<path:path>')
    def redis_handler(path):
        return render_template('redis.html')

# Tie extensions to APP

fm.init_app(APP, pipe)
login_manager.init_app(APP)
socketio.init_app(APP)

import jiejie.events  # noqa

if __name__ == '__main__':
    socketio.run(APP)
