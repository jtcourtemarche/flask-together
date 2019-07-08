#!/usr/bin/python

from datetime import datetime

from extensions import db, ma
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

    fm_name = db.Column(db.String(), nullable=True, default='')
    fm_sk = db.Column(db.String(32), nullable=True, default='')

    def setpass(self, password):
        self.password = generate_password_hash(password)

    def checkpass(self, password):
        return check_password_hash(self.password, password)

    def lastfm_connected(self):
        if self.fm_sk != '':
            return True
        return False

    # When you print the User model it returns this
    def __repr__(self):
        return '<User %r>' % self.username


class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    player = db.Column(db.String, unique=False, nullable=True) # Player (youtube or twitch)

    # Youtube/Twitch data
    video_id = db.Column(db.String(25), unique=False, nullable=False) # Twitch channel / Youtube watch id
    video_title = db.Column(db.String(100), unique=False, nullable=False) # Twitch stream title / Youtube video title
    video_thumbnail = db.Column(db.String, unique=False, nullable=False) # Twitch stream thumbnail / Youtube video thumbnail

    # Twitch data
    twitch_avatar = db.Column(db.String, unique=False, nullable=True)

    # User data
    date = db.Column(db.DateTime, default=datetime.now()) # Date watched
    user_id = db.Column(db.Integer, db.ForeignKey(User.id),  nullable=False) # User who selected the video's primary key
    user = db.relationship('User', foreign_keys='History.user_id') # User who selected the video's object

    # When you print the History model it returns this
    def __repr__(self):
        return '["'+self.video_title+'", '+self.video_id+']'

class HistorySchema(ma.ModelSchema):
    class Meta:
        model = History
