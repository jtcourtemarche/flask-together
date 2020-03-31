import jiejie.models as models
from app import APP


def test_user_model(db):
    user = models.User(
        name='test9999'
    )
    user.setpass('password123')

    # test password
    if not user.checkpass('password123'):
        db.session.delete(user)
        db.session.commit()
        exit('setting password failed')

    db.session.add(user)
    db.session.commit()

    return user


def test_video_model(db, user, room):
    video = models.Video(
        watch_id='dQw4w9WgXcQ',
        title='Rick Astley - Never Gonna Give You Up (Video)',
        thumbnail='',
        user_id=user.id,
        room_id=room.id
    )
    db.session.add(video)
    db.session.commit()

    return video


def test_room_model(db):
    user = test_user_model(db)

    room = models.Room(name='my cool new room')
    db.session.add(room)
    db.session.commit()

    video1 = test_video_model(db, user, room)
    test_video_model(db, user, room)

    # method tests
    try:
        print('user: {0}\nroom: {1}\nvideo: {2}'.format(user, room, video1))

        print('\nvideos played in room: ', room.videos)

        # room related methods
        print()

        print('user.join_room()')
        user.join_room(room)

        print('users in room: ', room.users)

        print('user.leave_room()')
        user.leave_room(room)

        print('users in room: ', room.users)

        # test room methods
        print()

        print('room.most_recent_video:')
        print(room.most_recent_video.data)

        print('room.online_users')
        room.online_users

        print('room.recent_history:')
        print(room.recent_history.data)
    except Exception as error:
        print('!! FAILED: ', error)

    # delete objects created
    print()
    print('cleaning up...')

    db.session.delete(user)
    db.session.delete(room)
    db.session.commit()

    print('success!!!')


if __name__ == '__main__':
    with APP.app_context():
        test_room_model(models.db)
