from app import db
from models import User
import sqlite3
import os

# Initializes Sqlite3 Database
def init_db():
    with sqlite3.connect('watch.db') as conn:
        conn.commit()

    db.create_all()
    u = User(username='test')
    u.setpass('test')
    db.session.add(u)
    db.session.commit()

def destroy_db():
    os.remove('watch.db')
    print 'Complete'
