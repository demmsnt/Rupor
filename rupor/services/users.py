"""Users service stub"""
USERS = {
    'ivanof': {
        'password': 'ivanof123'},
    'petrof': {
        'password': 'petrof123'}
}


class UsersSvc():
    def __init__(self):
        self.users = USERS

    def check_password(self, user, password):
        usr = self.users.get(user)
        if usr:
            return usr['password'] == password
        return False
