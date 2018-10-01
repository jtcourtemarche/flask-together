from flask_login import LoginManager
from flask_marshmallow import Marshmallow
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask import redirect

from app import app

import redis

# Flask login
login_manager = LoginManager()
login_manager.session_protection = "basic"
login_manager.init_app(app)

# Flask SQLAlchemy
db = SQLAlchemy(app)

# Flask Marshmallow
ma = Marshmallow(app)

# Redis
r = redis.StrictRedis(host='localhost', port=6379, db=0)
pipe = r.pipeline()

# Flask migrate
migrate = Migrate(app, db)

# Flask socketio
socketio = SocketIO(app)

# Must be loaded after redis server is initialized
from lib.lastfm import FM

# LastFM
fm = FM()