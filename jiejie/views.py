#!/usr/bin/python
import os
import random

import colorgram
import requests
from flask import Blueprint
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask_login import current_user
from flask_login import login_required
from flask_login import login_user
from flask_login import logout_user

import jiejie.models as models
from config import LASTFM_KEY
from extensions import fm
from extensions import login_manager
from extensions import pipe

# Register these views with app
urls = Blueprint('urls', __name__)

# Login manager user handler
@login_manager.user_loader
def load_user(user_id):
    return models.User.query.get(int(user_id))

# Make current_user a global variable
@urls.before_request
def before_request():
    g.user = current_user

# Index page
@urls.route('/')
def root():
    if g.user.is_authenticated:
        return redirect('/watch')

    return render_template('login.html')

# Standard viewing page
@urls.route('/watch')
@login_required
def index():
    return render_template('index.html')

# User history
@urls.route('/~<string:username>/history/<int:index>')
@urls.route('/~<string:username>/history')
@login_required
def user_history(username, index=1):
    user = models.User.query.filter_by(username=username).first()
    if user:
        history = models.History.query.filter_by(
            user_id=user.id).order_by(models.db.text('-id')).all()

        return render_template(
            'history.html',
            history=history[25*(index-1):25*index]
        )
    else:
        return 'User ' + user + ' does not exist.'

# User profiles
@urls.route('/~<string:username>')
@login_required
def user_profile(username):
    user = models.User.query.filter_by(username=username).first()
    if user:
        if user.lastfm_connected():
            lastfm_data = fm.get_user(user.fm_name)
        else:
            lastfm_data = None

        history = models.History.query.filter_by(
            user_id=user.id).order_by(models.db.text('-id')).all()
        hmap = [x.video_id for x in history]

        # If there are > 0 videos played by this user
        if hmap != []:
            # Get mode of hmap to find most played video
            most_played_id = max(set(hmap), key=hmap.count)
            # Get most_played video object from DB
            most_played = models.History.query.filter_by(
                video_id=most_played_id).first()

            cached_mp = pipe.get(f'profile-mp:{user.username}').execute()

            # If this id is already stored in cache
            if cached_mp[0] is not None and cached_mp[0].decode('utf-8') == most_played_id:
                dom_color = pipe.get(
                    f'profile-bgcolor:{user.username}').execute()[0].decode('utf-8')
                fg_color = pipe.get(
                    f'profile-fgcolor:{user.username}').execute()[0].decode('utf-8')
            else:
                # Get avg color of thumbnail
                r = requests.get(most_played.video_thumbnail)

                key = random.randint(1, 9999)

                # Download to /tmp/ directory on Linux
                with open(f'/tmp/thumb-{key}.jpg', 'wb') as f:
                    for chunk in r.iter_content(chunk_size=128):
                        f.write(chunk)

                # Use kmeans cluster algorithm to get most dominant color
                # Retrieve 2 clusters
                colors = colorgram.extract(f'/tmp/thumb-{key}.jpg', 2)

                # Clear temp thumbnail
                os.remove(f'/tmp/thumb-{key}.jpg')

                # Get the second most dominant color because the first is generally black
                # due to the black bars in Youtube thumbnails
                dom = colors[1].rgb

                if ((dom.g * 0.299) + (dom.b * 0.587) + (dom.r * 0.114)) > 186:
                    fg_color = '#000000'
                else:
                    fg_color = '#FFFFFF'

                # Convert to CSS rgb
                dom = [str(c) for c in dom]
                dom_color = ', '.join(dom)

                # Cache colors so they don't have to be generated them until most played id changes
                pipe.set(f'profile-bgcolor:{user.username}', dom_color)
                pipe.set(f'profile-fgcolor:{user.username}', fg_color)
                pipe.set(f'profile-mp:{user.username}', most_played_id)
                pipe.execute()
        else:
            # Defaults
            most_played = None
            most_played_id = None
            dom_color = 'white'
            fg_color = 'black'

        return render_template(
            'profile.html',
            user=user,
            history=enumerate(history),
            count=len(history),
            most_played=(
                most_played, hmap.count(most_played_id)),
            colors=(dom_color, fg_color),
            lastfm=lastfm_data
        )

    return 'Not a valid user.'


# Login view
@urls.route('/login', methods=['POST'])
def login():
    # Retrieve server:logged from cache
    logged_in = pipe.lrange('server:logged', 0, -1).execute()[0]
    # Decode byte string from redis to Python string
    logged_in = [user.decode('utf-8') for user in logged_in]

    if g.user.is_authenticated:
        return redirect('/watch')
    # elif request.form['username'] in logged_in:
    #    return render_template('login.html', error='User is already logged in')
    else:
        username = models.User.query.filter_by(
            username=request.form['username']).first()
        if username:
            if username.checkpass(request.form['password']):
                login_user(username)
                return redirect('/watch')
            else:
                return render_template('login.html', error='Invalid password')
        else:
            return render_template('login.html', error='Invalid username')


# Logout view
@urls.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


# Redirect user to LastFM authentication page
@urls.route('/auth/lastfm')
@login_required
def auth_lastfm():
    if not current_user.lastfm_connected():
        return redirect(f'http://www.last.fm/api/auth/?api_key={LASTFM_KEY}')

    return f'Your account {current_user.fm_name} is already connected'


# Register LastFM credentials into ytdl database
@urls.route('/register', methods=['GET'])
@login_required
def register():
    if 'token' in request.args and len(request.args['token']) == 32:
        token = request.args['token']

        resp = fm.get_session(token)

        if resp[0]:
            # Register LastFM in DB
            current_user.fm_name = resp[1]['name']
            current_user.fm_token = token
            current_user.fm_sk = resp[1]['key']

            models.db.session.commit()

            return '<span>Registered {}</span><br/><a href="/">Take me back</a>'.format(resp[1]['name'])
        else:
            return 'Error connecting to your LastFM account: {}'.format(resp[1]['message'])
    else:
        return 'Failed to connect to your LastFM'


# Page errors


@urls.errorhandler(404)
def page_not_found(error):
    return redirect('/')


@urls.errorhandler(401)
def unauthorized(error):
    return redirect('/')
