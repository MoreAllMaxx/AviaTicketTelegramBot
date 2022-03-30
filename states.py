from aiogram.dispatcher.filters.state import StatesGroup, State


class Steps(StatesGroup):
    city_from = State()
    city_to = State()
    flight_date = State()
    flight_choice = State()
    sits_number = State()
    comment = State()
    validate_data = State()
    phone_number = State()