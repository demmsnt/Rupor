"""Users service stub"""
from uuid import uuid4
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
        """Проверка пароля"""
        usr = self.users.get(user)
        if usr:
            return usr['password'] == password
        return False

    def get_user(self, request):
        """Вернет user_id по реквесту или None для анонимуса"""
        return uuid4().hex
