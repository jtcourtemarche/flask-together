import jiejie.models as models


def test_user_model():
    user = models.User(
        name='test9999'
    )
    models.db.session.add(user)
    models.db.session.commit()

    user.setpass('password123')

    # test password
    if not user.checkpass('password123'):
        models.db.session.delete(user)
        models.db.session.commit()
        exit('setting password failed')

    return user


def test_video_model(user):
    video = models.Video(
        unique_id='dQw4w9WgXcQ',
        title='Rick Astley - Never Gonna Give You Up (Video)',
        thumbnail='',
        user=user,
        player='youtube'
    )
    models.db.session.add(video)
    models.db.session.commit()

    return video


def test_room_model():
    user = test_user_model()
    video = test_video_model(user)

    room = models.Room()

    # test room methods

    print('room.get_most_recent_video():')
    print(room.get_most_recent_video())

    print('room.get_online_users():')
    # room.get_online_users()

    print('room.get_recent_history():')
    print(room.get_recent_history())

    # delete objects created
    models.db.session.delete(user)
    models.db.session.delete(video)
    models.db.session.delete(room)
    models.db.session.commit()
