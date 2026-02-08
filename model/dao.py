from data.base import BaseDAO
from model.user import User
from model.spec_equipment import Spec_Equipment


class UsersDAO(BaseDAO):
    model = User

class Spec_Equipment_DAO(BaseDAO):
    model = Spec_Equipment