Platform built on Flask that synchronizes Youtube videos using websockets.

**Tested for Python 3.7.0+**

## Setup

This application requires that you have a PostgreSQL & Redis server already set up.
Put your credentials in the config.py file:

```python
# Example postgres import

POSTGRES = {
    'user': 'postgres',
    'password': 'password',
    'dbname': 'mydatabase',
    'host': 'localhost',
    'port': '5432',
}
```

It is assumed that you are running Redis on the default port.

All of your API keys belong in the config.py file as well.
Your config.py file setup should look similar to this:

```python
YOUTUBE_KEY = "<youtube api key>"
SECRET_KEY = "<secret key for flask>"

# If you want LastFM integration (these are optional)
LASTFM_ENABLED = True
LASTFM_KEY = "<lastfm api key>"
LASTFM_SECRET = "<lastfm secret key>"
```
Python setup is as follows:

```
$ pip install -r requirements.txt

$ python manager.py
>> init_db

$ python manager.py
>> add_user

# Initialize migrations
$ flask db init

# Run locally
$ python app.py 

# Or run w/ Gunicorn
$ gunicorn app:app --bind 0.0.0.0:5000 --reload -k "geventwebsocket.gunicorn.workers.GeventWebSocketWorker"
```

## Developer Notes

### Disconnection Issue:
  - A disconnect event will not fire immediately if you are not using web sockets. This can make users appear online long after they have left the room:
    https://github.com/miguelgrinberg/Flask-SocketIO/issues/291
