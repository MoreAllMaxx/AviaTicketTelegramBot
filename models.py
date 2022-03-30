from pony.orm import Database, Required, Optional, db_session

try:
    from settings import DB_CONFIG
except ImportError:
    exit('DO cp setting.py.default settings.py and set DB_CONFIG.')

db = Database()
db.bind(**DB_CONFIG)


class UserState(db.Entity):
    user_id = Required(int, unique=True)
    username = Required(str, sql_default="''")
    user_state = Optional(str, sql_default="''")


class Registration(db.Entity):
    user_id = Required(int)
    username = Required(str)
    chosen_flight = Required(str)
    sits = Required(int)
    comment = Required(str)
    phone_number = Required(str)


async def create_user(user_id, username, user_state):
    user_id = int(user_id)
    with db_session:
        if not UserState.get(user_id=user_id):
            UserState(user_id=user_id, username=username, user_state=user_state)
        else:
            UserState.get(user_id=user_id).delete()
            UserState(user_id=user_id, username=username, user_state=user_state)


async def update_user(user_id, user_state):
    with db_session:
        user = UserState.get(user_id=int(user_id))
        if not user:
            UserState(user_id=int(user_id), user_state=user_state)
            user = UserState.get(user_id=int(user_id))
        user.user_state = user_state


async def delete_user(user_id):
    with db_session:
        if UserState.get(user_id=int(user_id)):
            UserState.get(user_id=int(user_id)).delete()


async def register_user(data):
    with db_session:
        user_id, username, chosen_flight, sits, comment, phone_number = data
        new_ticket = Registration(
            user_id=user_id,
            username=username,
            chosen_flight=chosen_flight,
            sits=sits,
            comment=comment,
            phone_number=phone_number,
        )


db.generate_mapping(create_tables=True)
