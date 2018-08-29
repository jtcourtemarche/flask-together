#!/usr/bin/python

from statistics import mode

from flask import Blueprint, g, redirect, render_template, request
from flask_login import current_user, login_required, login_user, logout_user

from app import db
import models

urls = Blueprint('urls', __name__)

@urls.before_request
def before_request():
    g.user = current_user

@urls.route('/login', methods=['GET', 'POST'])
def login():
    if g.user.is_authenticated:
        return redirect('/watch')
    else:
        username = models.User.query.filter_by(username=request.form['username']).first()            
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
def user_profile(username):
    user = models.User.query.filter_by(username=username).first()
    if user:
        history = models.History.query.filter_by(user_id=user.id).order_by(db.text('-id')).all()

        hmap = map(lambda x: x.video_id, history)
        most_played_id = max(set(hmap), key=hmap.count)
        most_played = models.History.query.filter_by(video_id=most_played_id).first()

        return render_template('profile.html', 
            user=user, 
            history=enumerate(history), 
            count=len(history), 
            most_played=(most_played, hmap.count(most_played_id)))
    else:
        return redirect('/')

