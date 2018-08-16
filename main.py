#!/usr/bin/python

"""
    YT de Locke

    Libraries required:
    eventlet, flask, flask_socketio, gdata
"""

from flask import Flask, render_template, Blueprint, request, session
from flask_socketio import SocketIO, send, emit, join_room
import sqlite3, datetime, re, urllib, urllib2, json, operator
from api import API_KEY

app = Flask(__name__)

app.config.update(
    TEMPLATES_AUTO_RELOAD=True,
    SERVER_HOST='0.0.0.0:5000'
)

def search_yt(query):
    query = str(urllib.quote(query))
    url = "https://www.googleapis.com/youtube/v3/search?maxResults=20&type=video&order=relevance&q="+query+"&key="+API_KEY+"&part=id%2Csnippet"
    feed = urllib2.urlopen(url).read()
    return json.loads(feed)["items"]

# Tool that checks if valid youtube video
def check_yt(id):
    url = "https://www.googleapis.com/youtube/v3/videos?id="+id+"&key="+API_KEY+"&part=snippet"
    feed = urllib2.urlopen(url).read()
    res = json.loads(feed)
    if res != []:
        return feed
    else:
        return False

socketio = SocketIO(app)

# TODO: Cache volume slider, Loading page, Video quality, Cleanup

clients = []

def init_db():
    with sqlite3.connect('watch.db') as conn:
        conn.cursor().execute('''CREATE TABLE history
            (date date, id text, video_data text)''')
        conn.commit()

@app.route('/')
def index():
    return render_template('index.html')

# deprecated
"""
@app.route('/stats')
def stats():
    with sqlite3.connect('watch.db') as conn:
        history = conn.cursor().execute("SELECT * FROM history ORDER BY id ASC").fetchall()
        hdict = dict()

        cur = history[0][1]
        x = 0 
        y = 0
        title = ''
        for h in history:
            if x <= 10:
                if h[1] == cur:
                    y += 1
                    if title == '':
                        title = check_yt(h[1])
                    hdict.update({title: y+1})
                else:
                    # Reset
                    title = ''
                    y = 0
                    x += 1
                cur = h[1]
            else:
                break

        return render_template('stats.html', history=hdict)
"""

@socketio.on('joined')
def handle_connect():
    # New connection handler
    clients.append(request.sid)

    room = session.get('room')
    join_room(room)

    with sqlite3.connect('watch.db') as conn:
        history = conn.cursor().execute("SELECT * FROM history ORDER BY date DESC").fetchall()
        last_id = conn.cursor().execute("SELECT * FROM history ORDER BY date DESC").fetchall()[0][1]

    emit('new-user-sync', {
        'history': history,
        'id': last_id,
    }, room=clients[-1])

@socketio.on('disconnect')
def handle_dc():
    i = 0
    print '-------------------------------'
    print request.sid + ' has disconnected'
    print '-------------------------------'
    for client in clients:
        i += 1
        if client == request.sid:
            print client
            del clients[i] 

# Play / Pause
@socketio.on('client-play')
def play(data):
    emit('server-play', data["time"], broadcast=True)
    print('Play @ ' + str(data["time"]))

@socketio.on('client-pause')
def pause(data):
    emit('server-pause', data["time"], broadcast=True)
    print('Pause @ ' + str(data["time"]))

@socketio.on('client-play-new')
def play_new(data):
    # Extract video id from yt url
    yt_re = r'(https?://)?(www\.)?youtube\.(com|nl)/watch\?v=([-\w]+)'
    yt_id = re.findall(yt_re, data["url"])

    # Check if valid youtube url, if not serve search results
    if yt_id == []:
        emit('server-serve-list', {'results': search_yt(data["url"])}, room=request.sid)
    else:
        with sqlite3.connect('watch.db') as conn:
            conn.text_factory = str
            history = conn.cursor().execute("SELECT * FROM history ORDER BY date DESC").fetchall()
            conn.cursor().execute('INSERT INTO history VALUES (?,?,?)',
                [datetime.datetime.now(), yt_id[0][3], str(check_yt(yt_id[0][3]))])
            conn.commit()

        emit('server-play-new', {'id': yt_id[0][3], 'history':history}, broadcast=True)

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

@app.errorhandler(404)
def page_not_found(error):
    return error

if __name__ == '__main__':
    socketio.run(app)