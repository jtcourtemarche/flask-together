#!/usr/bin/python

from app import db, ma
import json
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

    def setpass(self, password):
        self.password = generate_password_hash(password)

    def checkpass(self, password):
        return check_password_hash(self.password, password)

    # When you print the user it returns this
    def __repr__(self):
        return '<User %r>' % self.username

class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.String(11), unique=False, nullable=False)
    data = db.Column(db.Text, unique=False, nullable=False)
    date = db.Column(db.DateTime, default=datetime.now())

    user_id = db.Column(db.Integer, db.ForeignKey(User.id),  nullable=False)
    user = db.relationship('User', foreign_keys='History.user_id')

    def __repr__(self):
        return '<History %r>' % self.id

class HistorySchema(ma.ModelSchema):
    class Meta:
        model = History