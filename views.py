#!/usr/bin/python

import models
from app import db
from flask import Blueprint, render_template, request, g, redirect
from flask_login import login_required, current_user, login_user, logout_user

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
    logout_user(g.user)
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
        return render_template('profile.html', user=user, history=enumerate(history), count=len(history))
    else:
        return redirect('/')

@urls.errorhandler(404)
def page_not_found(error):
    return redirect('/')