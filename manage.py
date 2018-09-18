#!/usr/bin/python

import os
import sqlite3

import models
from app import db

# Initializes Sqlite3 Database
def init_db():
    db.create_all()
    db.session.commit()
    print('Complete')

def destroy_db():
    os.remove('watch.db')
    print('Complete')

def add_user(username, password):
    u = models.User(username=username)
    u.setpass(password)

    db.session.add(u)
    db.session.commit()

    print('Added user: {}'.format(u))

def del_user(username='', user_id=None):
    if username:
        u = models.User.query.filter_by(username=username).first()

        db.session.delete(u)
        db.session.commit()
    elif user_id:
        u = models.User.query.get(user_id)

        db.session.delete(u)
        db.session.commit()
    else:
        print('Invalid parameters')

