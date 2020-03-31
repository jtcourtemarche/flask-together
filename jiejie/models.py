#!/usr/bin/python
from collections import Counter
from datetime import datetime

from flask_login import UserMixin
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash

from extensions import pipe

db = SQLAlchemy()
ma = Marshmallow()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

    # LastFM settings
    fm_name = db.Column(db.String(), nullable=True, default='')
    fm_sk = db.Column(db.String(32), nullable=True, default='')

    # videos played by user
    videos = db.relationship(
        'Video', backref='user', cascade='all,delete', order_by='-Video.id', lazy=True)

    def setpass(self, password):
        self.password = generate_password_hash(password)

    def checkpass(self, password):
        return check_password_hash(self.password, password)

    @property
    def lastfm_connected(self):
        return bool(self.fm_sk != '')

    def join_room(self, room):
        room.users.append(self)
        db.session.commit()

    def leave_room(self, room):
        room.users.remove(self)

        # if no users left in room, delete room
        if len(room.users) <= 0:
            db.session.delete(room)

        db.session.commit()

    @property
    def most_played_video(self):
        if self.videos:
            most_played = Counter(
                [video.watch_id for video in self.videos]).most_common(1)

            most_played = Video.query.filter_by(
                watch_id=most_played[0][0]).first()

            return most_played
        return None

    def __repr__(self):
        return '<User %r>' % self.name


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    watch_id = db.Column(db.String(25), unique=False,
                         nullable=False)  # YouTube watch ID
    title = db.Column(db.String(100), unique=False, nullable=False)
    thumbnail = db.Column(db.String, unique=False, nullable=True)
    date = db.Column(db.DateTime, default=datetime.now())  # Date watched

    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return '<Video: %r, %r>' % (self.watch_id, self.title)


# Allows room video history to be serialized to JSON
class HistorySchema(ma.Schema):
    class Meta:
        model = Video
        fields = ('id', 'watch_id', 'title', 'thumbnail', 'date', 'user_id')


class UserSchema(ma.Schema):
    class Meta:
        model = User
        fields = ('id', 'name')


# many to many relationship btwn user & room
users = db.Table('users',
                 db.Column('room_id', db.Integer, db.ForeignKey(
                     'room.id'), primary_key=True),
                 db.Column('user_id', db.Integer, db.ForeignKey(
                     'user.id'), primary_key=True)
                 )


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=False, nullable=False)

    # TODO: Owner field?

    # use Room.query.with_parent(user_object) to get user's rooms
    # use Room.users to get users in room
    users = db.relationship(
        'User', secondary=users, lazy='subquery', backref=db.backref('joined_users', lazy=True))

    # videos played in room
    videos = db.relationship(
        'Video', backref='room', cascade='all,delete', order_by='-Video.id', lazy=True)

    public = db.Column(db.Boolean, default=True,
                       server_default='t', nullable=False)

    @property
    def online_users(self):
        online_users = pipe.smembers(
            'room:' + str(self.id)
        ).execute()

        if len(online_users) <= 0:
            return []

        return list(online_users[0])

    # Retrieve most recent object from history
    @property
    def most_recent_video(self):
        schema = HistorySchema()

        if self.videos:
            data, errors = schema.dump(self.videos[0])
            if not errors:
                return data

        return dict() 

    # Retrieve last 20 objects from history
    @property
    def recent_history(self):
        schema = HistorySchema(many=True)

        data, errors = schema.dump(reversed(self.videos[:20]))
        if not errors:
            return data 

        return dict() 

    def __repr__(self):
        return '<Room: %r, %r>' % (self.id, self.name)
