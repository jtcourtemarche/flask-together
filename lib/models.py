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

    # When you print the user model it returns this
    def __repr__(self):
        return '<User %r>' % self.username


class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # Video data
    video_id = db.Column(db.String(11), unique=False, nullable=False)
    video_date = db.Column(db.String(24), unique=False, nullable=False)
    video_title = db.Column(db.String(100), unique=False, nullable=False)
    video_thumbnail = db.Column(db.String, unique=False, nullable=False)

    # User data
    date = db.Column(db.DateTime, default=datetime.now())
    user_id = db.Column(db.Integer, db.ForeignKey(User.id),  nullable=False)
    user = db.relationship('User', foreign_keys='History.user_id')

    def __repr__(self):
        return '["'+self.video_title+'", '+self.video_id+']'

class HistorySchema(ma.ModelSchema):
    class Meta:
        model = History
