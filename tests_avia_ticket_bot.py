import datetime
import logging

import pytest

import unittest.mock

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from pony.orm import db_session, rollback

import handlers
import states
from handlers import handlers_config
from models import UserState, Registration
from generate_ticket import draw_ticket

handlers.log.setLevel(logging.WARN)
USER_ID = 1234567890
USERNAME = 'Вася'
_flight_date = (datetime.datetime.today() + datetime.timedelta(days=256)).strftime('%d-%m-%Y')

TEST_MESSAGES_CORRECT = [
    'Москваа',
    'Москва',
    'Екатеринбургр',
    'Екатеринбург',
    '123456',
    _flight_date,
    '0',
    '5',
    '0',
    '5',
    '',
    'comment123',
    'Да',
    '1234',
    '88005553535',
]

TEST_MESSAGES_CITY_FROM_INVALID_TWICE = [
    'Самараа',
    'Самараа',
]

TEST_MESSAGES_CITY_TO_INVALID_TWICE = [
    ('Крым', handlers_config['state_handlers'][1],),
    ('Бакуу', handlers_config['state_handlers'][2],),
    ('Бакуу', handlers_config['state_handlers'][2],),
]

TEST_MESSAGES_SAME_CITIES = [
    ('Крым', handlers_config['state_handlers'][1]),
    ('Крым', handlers_config['state_handlers'][3]),
]

TEST_MESSAGES_VALIDATE_CANCEL = [
    ('Ереван', handlers_config['state_handlers'][1]),
    ('Пекин', handlers_config['state_handlers'][3]),
    (_flight_date, handlers_config['state_handlers'][5]),
    ('1', handlers_config['state_handlers'][7]),
    ('1', handlers_config['state_handlers'][9]),
    ('comment123', handlers_config['state_handlers'][11]),
    ('Нет', handlers_config['state_handlers'][12]),
]


def isolate_db(test_func):
    async def wrapper(*args, **kwargs):
        with db_session:
            user = UserState(user_id=USER_ID, username=USERNAME, user_state='default')
            await test_func(*args, **kwargs)
            rollback()

    return wrapper


class TestEchoBot(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.bot = unittest.mock.AsyncMock(Bot)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(self.bot, storage=self.storage)
        self.state = FSMContext(storage=self.storage, chat=USER_ID, user=USER_ID)
        handlers.register_handlers(self.dp, config=handlers_config)

    @pytest.mark.asyncio
    @isolate_db
    async def test_send_welcome_handler(self):
        text = '/start'
        if text == '/' + handlers_config['command_handlers'][0][1]:
            message_mock = unittest.mock.AsyncMock(text=text)
            message_mock.chat.first_name = USERNAME
            message_mock.chat.username = USERNAME
            message_mock.chat.id = USER_ID
            await handlers.send_welcome(message=message_mock, state=self.state)
            message_mock.answer.assert_called_with(f'Доступные команды: /ticket, /help, /cancel')
        else:
            raise ValueError('Ошибка в проверке команды test_send_welcome_handler')

    @pytest.mark.asyncio
    @isolate_db
    async def test_send_help(self):
        text = '/help'
        if text == '/' + handlers_config['command_handlers'][1][1]:
            message_mock = unittest.mock.AsyncMock(text=text)
            message_mock.chat.first_name = USERNAME
            message_mock.chat.username = USERNAME
            message_mock.chat.id = USER_ID
            await handlers.send_help(message=message_mock)
            message_mock.answer.assert_called_with(
                f'Я бот AirTicketLaggyBot. Доступные команды: /start, /ticket, /help, /cancel')
        else:
            raise ValueError('Ошибка в проверке команды test_send_help')

    @pytest.mark.asyncio
    @isolate_db
    async def test_cancel_command(self):
        text = '/cancel'
        if text == '/' + handlers_config['command_handlers'][2][1]:
            message_mock = unittest.mock.AsyncMock(text=text)
            message_mock.chat.first_name = USERNAME
            message_mock.chat.username = USERNAME
            message_mock.chat.id = USER_ID
            await self.state.set_state(states.Steps.city_from)
            await handlers.cancel_command(message=message_mock, state=self.state)
            assert await self.state.get_state() is None
        else:
            raise ValueError('Ошибка в проверке команды test_cancel_command')

    @pytest.mark.asyncio
    @isolate_db
    async def test_ticket_start(self):
        text = '/ticket'
        if text == '/' + handlers_config['command_handlers'][3][1]:
            message_mock = unittest.mock.AsyncMock(text=text)
            message_mock.chat.first_name = USERNAME
            message_mock.chat.username = USERNAME
            message_mock.chat.id = USER_ID
            await handlers.ticket_start(message=message_mock, state=self.state)
            assert str(await self.storage.get_state(user=USER_ID, chat=USER_ID)) == 'Steps:city_from'
        else:
            raise ValueError('Ошибка в проверке команды test_ticket_start')

    @pytest.mark.asyncio
    @isolate_db
    async def test_ticket_state_correct(self):
        message_text = '/ticket'
        if message_text == '/' + handlers_config['command_handlers'][3][1]:
            message_mock = unittest.mock.AsyncMock(text=message_text)
            message_mock.chat.first_name = USERNAME
            message_mock.chat.username = USERNAME
            message_mock.chat.id = USER_ID
            await handlers.ticket_start(message=message_mock, state=self.state)
            del handlers_config['state_handlers'][12]
            for i, message_text in enumerate(TEST_MESSAGES_CORRECT):
                message_mock = unittest.mock.AsyncMock(text=message_text)
                message_mock.chat.first_name = USERNAME
                message_mock.chat.username = USERNAME
                message_mock.chat.id = USER_ID
                if handlers_config['state_handlers'][i][1](message_mock):
                    try:
                        await handlers_config['state_handlers'][i][0](message=message_mock,
                                                                      state=self.state)
                    except TypeError:
                        await handlers_config['state_handlers'][i][0](message=message_mock)
                else:
                    raise ValueError('Ошибка в проверке сценария TEST_MESSAGES')
            message_mock.answer.assert_called_with('Ваш электронный билет:')
        else:
            raise ValueError('Ошибка в команде /ticket')

    @pytest.mark.asyncio
    @isolate_db
    async def test_ticket_from_invalid_twice(self):
        message_text = '/ticket'
        if message_text == '/' + handlers_config['command_handlers'][3][1]:
            message_mock = unittest.mock.AsyncMock(text=message_text)
            message_mock.chat.first_name = USERNAME
            message_mock.chat.username = USERNAME
            message_mock.chat.id = USER_ID
            await handlers.ticket_start(message=message_mock, state=self.state)
            for message_text in TEST_MESSAGES_CITY_FROM_INVALID_TWICE:
                message_mock = unittest.mock.AsyncMock(text=message_text)
                if handlers_config['state_handlers'][0][1](message_mock):
                    await handlers_config['state_handlers'][0][0](message=message_mock,
                                                                  state=self.state)
                else:
                    raise ValueError('Ошибка в проверке сценария TEST_MESSAGES_CITY_FROM_INVALID_TWICE')
            message_mock.answer.assert_called_with(
                'Из указанного города нет рейсов\nДля повторного запуска бота - /ticket',
                reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            raise ValueError('Ошибка в команде /ticket')

    @pytest.mark.asyncio
    @isolate_db
    async def test_ticket_to_invalid_twice(self):
        message_text = '/ticket'
        if message_text == '/' + handlers_config['command_handlers'][3][1]:
            message_mock = unittest.mock.AsyncMock(text=message_text)
            message_mock.chat.first_name = USERNAME
            message_mock.chat.username = USERNAME
            message_mock.chat.id = USER_ID
            await handlers.ticket_start(message=message_mock, state=self.state)
            for message_data in TEST_MESSAGES_CITY_TO_INVALID_TWICE:
                message_mock = unittest.mock.AsyncMock(text=message_data[0])
                if message_data[1][1](message_mock):
                    await message_data[1][0](message=message_mock, state=self.state)
                else:
                    raise ValueError('Ошибка в проверке сценария TEST_MESSAGES_CITY_TO_INVALID_TWICE')
            message_mock.answer.assert_called_with(
                'В указанный город нет рейсов\nДля повторного запуска бота - /ticket',
                reply_markup=types.ReplyKeyboardRemove())

    @pytest.mark.asyncio
    @isolate_db
    async def test_ticket_same_cities(self):
        message_text = '/ticket'
        if message_text == '/' + handlers_config['command_handlers'][3][1]:
            message_mock = unittest.mock.AsyncMock(text=message_text)
            message_mock.chat.first_name = USERNAME
            message_mock.chat.username = USERNAME
            message_mock.chat.id = USER_ID
            await handlers.ticket_start(message=message_mock, state=self.state)
            for message_data in TEST_MESSAGES_SAME_CITIES:
                message_mock = unittest.mock.AsyncMock(text=message_data[0])
                if message_data[1][1](message_mock):
                    await message_data[1][0](message=message_mock, state=self.state)
                else:
                    raise ValueError('Ошибка в проверке сценария TEST_MESSAGES_SAME_CITIES')
            message_mock.answer.assert_called_with(
                'Города отправления и город назначения должны быть разными\n'
                'Для повторного запуска бота введите /ticket',
                reply_markup=types.ReplyKeyboardRemove()
            )

    @pytest.mark.asyncio
    @isolate_db
    async def test_validate_cancel(self):
        message_text = '/ticket'
        if message_text == '/' + handlers_config['command_handlers'][3][1]:
            message_mock = unittest.mock.AsyncMock(text=message_text)
            message_mock.chat.first_name = USERNAME
            message_mock.chat.username = USERNAME
            message_mock.chat.id = USER_ID
            await handlers.ticket_start(message=message_mock, state=self.state)
            for message_data in TEST_MESSAGES_VALIDATE_CANCEL:
                message_mock = unittest.mock.AsyncMock(text=message_data[0])
                if message_data[1][1](message_mock):
                    await message_data[1][0](message=message_mock, state=self.state)
                else:
                    raise ValueError('Ошибка в проверке сценария TEST_MESSAGES_VALIDATE_CANCEL')
            message_mock.answer.assert_called_with(
                'Для повторного заказа билетов введите /ticket', reply_markup=types.ReplyKeyboardRemove()
            )

    @pytest.mark.asyncio
    @isolate_db
    async def test_draw_ticket(self):
        test_ticket = Registration(
            user_id='1234',
            username='testuser',
            chosen_flight='testflight',
            sits='6',
            comment='test',
            phone_number='88005553535',
        )
        ticket_file = await draw_ticket('1234')
        with open('files/aviaticket_example.png', 'rb') as expected_file:
            expected_bytes = expected_file.read()
        assert ticket_file.read() == expected_bytes


if __name__ == '__main__':
    unittest.main()
