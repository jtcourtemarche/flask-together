# Manager is designed to make simple database commands easily accessible

class Manager:
    def __init__(self, db, models):
        self.db = db
        self.models = models

        print("""
            Welcome to the Locke manager
            Access the following commands using app.mgr.*()

            * init_db => initializes database
            * wipe_db => wipes database
            * add_user => add a user to the database
                - params: username, password
            * del_user => remove a user from the database
                - params: username
            * list_users => list all registered users
        """)

    def printc(self, msg):
        print(msg)
        print('!!! Complete')

    def init_db(self):
        self.db.create_all()
        self.db.session.commit()
        self.printc('Initialized database')

    def wipe_db(self):
        self.db.drop_all()
        self.db.session.commit()
        self.printc('Wiped database')

    def add_user(self, username, password):
        u = self.models.User(username=username)
        u.setpass(password)

        self.db.session.add(u)
        self.db.session.commit()

        self.printc(f'Added user: {u}')

    def add_users(self, users):
        # Deprecated
        # Requires [('username', 'password'), ...] parameter
        for user in users:
            u = self.models.User(username=user[0])
            u.setpass(user[1])

            self.db.session.add(u)
        self.db.session.commit()

        users = [user[0] for user in users]

        self.printc(f'Added users: {users}')

    def del_user(self, username):
        if username:
            u = self.models.User.query.filter_by(username=username).first()

            if u != None:
                self.db.session.delete(u)
                self.db.session.commit()
                self.printc(f'Deleted user: {u}')
            else:
                print(f'Could not find username {username}')
        else:
            print('Invalid parameters!')

    def list_users(self):
        users = self.models.User.query.all()
        users = [user.username for user in users]
        self.printc(', '.join(users))