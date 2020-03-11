import redis
from flask_login import LoginManager
from flask_socketio import SocketIO

from jiejie.lastfm import LastFMAPI

# In this file, objects will be initialized and then later tied to the APP object in apps.py

# Redis
r = redis.StrictRedis(
    host='localhost',
    port='6379',
    db=0,
    decode_responses=True
)
pipe = r.pipeline()

# Test Redis connection
try:
    r.ping()
    redis_connected = True
except redis.exceptions.ConnectionError:
    redis_connected = False

# LastFM API
fm = LastFMAPI()

# Login manager
login_manager = LoginManager()
login_manager.session_protection = 'basic'

# SocketIO
socketio = SocketIO()
