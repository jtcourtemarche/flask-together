#!/usr/bin/python

import hashlib

import requests
import json
from flask import Blueprint, g, redirect, render_template, request
from flask_login import current_user, login_required, login_user, logout_user

from api import LASTFM_KEY, LASTFM_SECRET

from extensions import db, fm
import lib.models

urls = Blueprint('urls', __name__)

@urls.before_request
def before_request():
    g.user = current_user

@urls.route('/login', methods=['GET', 'POST'])
def login():
    if g.user.is_authenticated:
        return redirect('/watch')
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

# ------------------------------------------

@urls.route('/')
def root():
    if g.user.is_authenticated:
        return redirect('/watch')

    return render_template('login.html')

@urls.route('/watch')
@login_required
def index():
    return render_template('index.html')

import numpy
from scipy.stats import mode
from skimage import io

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

        if hmap != []:
            most_played_id = mode(hmap, axis=None)[0].tolist()[-1]
            most_played = lib.models.History.query.filter_by(
                video_id=most_played_id).first()

            # Get avg color of thumbnail
            thumb = io.imread(most_played.video_thumbnail)
            avg_rows = numpy.average(thumb, axis=0)
            avg = numpy.average(avg_rows, axis=0)
            avg = avg.tolist()
            avg = [int(round(x)) for x in avg]

            if ((avg[2] * 0.299) + (avg[1] * 0.587) + (avg[0] * 0.114)) > 186:
                fg_color = '#000000'
            else:
                fg_color = '#FFFFFF'

            avg = [str(x) for x in avg]
            avg = ', '.join(reversed(avg))
        else:
            most_played = None
            most_played_id = None
            avg = 'white'
            fg_color = 'black'

        return render_template('profile.html',
                               user=user,
                               history=enumerate(history),
                               count=len(history),
                               most_played=(
                                   most_played, hmap.count(most_played_id)),
                               colors=(avg, fg_color),
                               lastfm=lastfm_data
                            )

    return 'Not a valid user.'
