#!/usr/bin/python

import hashlib
import requests
import json
import colorgram
from flask import Blueprint, g, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from api import LASTFM_KEY, LASTFM_SECRET

from extensions import db, fm, pipe
import lib.models

urls = Blueprint('urls', __name__)


@urls.before_request
def before_request():
    g.user = current_user


@urls.route('/login', methods=['POST'])
def login():
    # Retrieve server:logged from cache    
    logged_in = pipe.lrange('server:logged', 0, -1).execute()[0]
    # Decode byte string from redis to Python string
    logged_in = [user.decode('utf-8') for user in logged_in]

    if g.user.is_authenticated:
        return redirect('/watch')
    elif request.form['username'] in logged_in:
        return render_template('login.html', error='User is already logged in')
    else:
        username = lib.models.User.query.filter_by(
            username=request.form['username']).first()
        if username:
            if username.checkpass(request.form['password']):
                login_user(username)
                return redirect('/watch')
            else:
                return render_template('login.html', error='Invalid password')
        else:
            return render_template('login.html', error='Invalid username')


@urls.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


# LastFM
@urls.route('/auth/lastfm')
@login_required
def auth_lastfm():
    if not current_user.lastfm_connected():
        return redirect(f'http://www.last.fm/api/auth/?api_key={LASTFM_KEY}&cb={request.url_root}register')

    return f'Your account {current_user.fm_name} is already connected'


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

            db.session.commit()

            return '<span>Registered {}</span><br/><a href="/">Take me back</a>'.format(resp[1]['name'])
        else:
            return 'Error connecting to your LastFM account: {}'.format(resp[1]['message'])
    else:
        return 'Failed to connect to your LastFM'


@urls.route('/')
def root():
    if g.user.is_authenticated:
        return redirect('/watch')

    return render_template('login.html')


@urls.route('/watch')
@login_required
def index():
    return render_template('index.html')

@urls.route('/user/<string:username>')
@login_required
def user_profile(username):
    user = lib.models.User.query.filter_by(username=username).first()
    if user:
        if user.lastfm_connected():
            lastfm_data = fm.get_user(user.fm_name)
        else:
            lastfm_data = None

        history = lib.models.History.query.filter_by(
            user_id=user.id).order_by(db.text('-id')).all()
        hmap = [x.video_id for x in history]

        # If there are > 0 videos played by this user
        if hmap != []:
            # Get mode of hmap to find most played video
            most_played_id = max(set(hmap), key=hmap.count)
            # Get most_played video object from DB
            most_played = lib.models.History.query.filter_by(
                video_id=most_played_id).first()

            cached_mp = pipe.get(f'profile-mp:{user.username}').execute()

            # If this id is already stored in cache
            if cached_mp[0] != None and cached_mp[0].decode('utf-8') == most_played_id:
                dom_color = pipe.get(f'profile-bgcolor:{user.username}').execute()[0].decode('utf-8')
                fg_color = pipe.get(f'profile-fgcolor:{user.username}').execute()[0].decode('utf-8')
            else:
                print('Regenerating Palettes')
                # Get avg color of thumbnail
                r = requests.get(most_played.video_thumbnail)
                # Download to /tmp/ directory on Linux
                with open('/tmp/thumb.jpg', 'wb') as f:
                    for chunk in r.iter_content(chunk_size=128):
                        f.write(chunk)
                # Use kmeans cluster algorithm to get most dominant color
                colors = colorgram.extract('/tmp/thumb.jpg', 1)

                dom = colors[0].rgb

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
