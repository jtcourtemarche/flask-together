from app import APP
from app import models

# Manager is designed to make simple database commands easily accessible


class Manager:
    def __init__(self):
        self.commands = {
            'init_db': self.init_db,
            'wipe_db': self.wipe_db,
            'add_user': self.add_user,
            'del_user': self.del_user,
            'list_users': self.list_users,
            'exit': self.exit,
        }

        print("""
            Welcome to the Locke manager
            Access the following commands:

            * init_db => initializes database
            * wipe_db => wipes database
            * add_user => add a user to the database
                - params: username, password
            * del_user => remove a user from the database
                - params: username
            * list_users => list all registered users
            * exit => exit program
        """)

    def run(self):
        print('Enter a command\n')
        io = input('>>> ')

        try:
            self.commands[io]()
        except Exception as e:
            print('Error ', e)
            exit()

    def exit(self):
        exit()

    def printc(self, msg):
        print(msg)
        print('!!! Complete')

    def init_db(self):
        models.db.create_all()
        models.db.session.commit()
        self.printc('Initialized database')

    def wipe_db(self):
        models.db.drop_all()
        models.db.session.commit()
        self.printc('Wiped database')

    def add_user(self):
        username = input('Username: ')
        password = input('Password: ')

        u = models.User(name=username)
        u.setpass(password)

        models.db.session.add(u)
        models.db.session.commit()

        self.printc(f'Added user: {u}')

    def add_users(self, users):
        # Deprecated
        # Requires [('username', 'password'), ...] parameter
        for user in users:
            u = models.User(name=user[0])
            u.setpass(user[1])

            models.db.session.add(u)

        models.db.session.commit()

        users = [user[0] for user in users]

        self.printc(f'Added users: {users}')

    def del_user(self):
        username = input('Username: ')

        user = models.User.query.filter_by(name=username).first()

        if user:
            models.db.session.delete(user)
            models.db.session.commit()
            self.printc(f'Deleted user: {user}')
        else:
            print(f'Could not find username {username}')

    def list_users(self):
        users = models.User.query.all()
        users = [user.name for user in users]
        self.printc(', '.join(users))


if __name__ == '__main__':
    with APP.app_context():
        mgr = Manager()

        while 1:
            mgr.run()
