import logging
import re

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.utils import markdown as md
from aiogram.types import ParseMode
from random import sample
from datetime import datetime, timedelta
from generate_ticket import draw_ticket

import utils
import models

from config import CITIES_AND_FLIGHT_TIME as SFT
from states import Steps

log = logging.getLogger('avia_ticket_bot')


def configure_logging(log):
    """Настройка логирования"""
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%d/%m/%Y %H:%M'))
    stream_handler.setLevel(logging.INFO)

    file_handler = logging.FileHandler('aviaticketbot_messages.log', encoding='utf8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%d/%m/%Y %H:%M'))
    file_handler.setLevel(logging.INFO)

    if log.hasHandlers():
        log.handlers.clear()

    log.addHandler(stream_handler)
    log.addHandler(file_handler)

    log.setLevel(logging.INFO)


configure_logging(log)


async def send_welcome(message: types.Message, state: FSMContext):
    """Ответ на команду /start"""
    current_state = await state.get_state()
    if current_state is not None:
        await state.finish()
        await models.delete_user(message.chat.id)
    log.info(f'{message.chat.first_name} подключился к боту. ID {message.chat.id}\n')
    await message.reply(f'Привет {message.chat.first_name}! Я бот AirTicketLaggyBot.',
                        reply_markup=types.ReplyKeyboardRemove())
    await message.answer(f'Я создан для обработки заказов на авиарейсы.')
    await message.answer(f'Доступные команды: /ticket, /help, /cancel')


async def send_help(message: types.Message):
    await message.answer(f'Я бот AirTicketLaggyBot. Доступные команды: /start, /ticket, /help, /cancel')


async def cancel_command(message: types.Message, state: FSMContext):
    """Ответ на команду /cancel"""
    current_state = await state.get_state()
    if current_state is None:
        return
    log.debug('Отмена состояний %r', current_state)
    await state.finish()
    await message.answer('Отменено.', reply_markup=types.ReplyKeyboardRemove())
    await models.delete_user(message.chat.id)


async def ticket_start(message: types.Message, state: FSMContext):
    """Ответ на команду /ticket"""
    current_state = await state.get_state()
    if current_state is not None:
        await state.finish()
        await models.delete_user(message.chat.id)
    log.debug('Начат сценарий покупки билетов')
    await state.set_state(Steps.city_from)
    await message.answer('Введите город отправления (на русском)', reply_markup=types.ReplyKeyboardRemove())
    await models.create_user(message.chat.id, message.chat.username, 'Город отправления')


async def ticket_from_invalid(message: types.Message, state: FSMContext):
    """Город отправления введен некорректно"""
    async with state.proxy() as data:
        if all([not data.get('city_from_check'), message.text.title()[:-1] in SFT.keys()]):
            data['city_from_check'] = True
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
            markup.add(message.text.title()[:-1])
            await message.answer('Подтвердите город отправления (на русском)', reply_markup=markup)
        elif not data.get('city_from_check'):
            data['city_from_check'] = True
            cities = sample(SFT.keys(), 5)
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
            markup.add(cities[0], cities[1], cities[2])
            markup.add(cities[3], cities[4])
            await message.answer('Из указанного города нет рейсов. Вы можете выбрать город из предложенных',
                                 reply_markup=markup)
        else:
            await state.finish()
            await message.answer('Из указанного города нет рейсов\nДля повторного запуска бота - /ticket',
                                 reply_markup=types.ReplyKeyboardRemove())
            await models.delete_user(message.chat.id)


async def ticket_from(message: types.Message, state: FSMContext):
    """Город отправления введен корректно"""
    async with state.proxy() as data:
        data['city_from'] = message.text.title()
        log.debug(f'{data}')

    await state.set_state(Steps.city_to)
    await message.answer('Введите город назначения (на русском)', reply_markup=types.ReplyKeyboardRemove())
    await models.update_user(message.chat.id, 'Город назначения')


async def ticket_to_invalid(message: types.Message, state: FSMContext):
    """Город назначения введен некорректно"""
    async with state.proxy() as data:
        if all([not data.get('city_to_check'), message.text.title()[:-1] in SFT.keys()]):
            data['city_to_check'] = True
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
            markup.add(message.text.title()[:-1])
            await message.answer('Подтвердите город назначения (на русском)', reply_markup=markup)
        elif not data.get('city_to_check'):
            data['city_to_check'] = True
            cities = sample(SFT.keys(), 5)
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
            markup.add(cities[0], cities[1], cities[2])
            markup.add(cities[3], cities[4])
            await message.answer('В указанный город нет рейсов. Вы можете выбрать город из предложенных',
                                 reply_markup=markup)
        else:
            await state.finish()
            await message.answer('В указанный город нет рейсов\nДля повторного запуска бота - /ticket',
                                 reply_markup=types.ReplyKeyboardRemove())
            await models.delete_user(message.chat.id)


async def ticket_to(message: types.Message, state: FSMContext):
    """Город назначения введен корректно"""
    async with state.proxy() as data:
        data['city_to'] = message.text.title()
        if data['city_from'] == data['city_to']:
            await state.finish()
            await models.delete_user(message.chat.id)
            return await message.answer('Города отправления и город назначения должны быть разными\n'
                                        'Для повторного запуска бота введите /ticket',
                                        reply_markup=types.ReplyKeyboardRemove())
        log.debug(f'{data}')

    await state.set_state(Steps.flight_date)
    await message.answer('Введите дату вылета в формате 05-11-2021', reply_markup=types.ReplyKeyboardRemove())
    await models.update_user(message.chat.id, 'Дата вылета')


async def ticket_date_invalid(message: types.Message):
    """Дата полета введена некорректно"""
    await message.answer(md.text('Введите дату вылета в формате 05-11-2021',
                                 'Информация о полетах доступна на год вперед',
                                 'На вчера купить билеты нельзя', sep='\n'))


async def ticket_date(message: types.Message, state: FSMContext):
    """Дата полета введена корректно"""
    async with state.proxy() as data:
        data['flight_date'] = message.text
        data['flights_to_choose'] = await utils.dispatcher(data['city_from'], data['city_to'], data['flight_date'])
        log.debug(f'{data}')

    await state.set_state(Steps.flight_choice)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add('1', '2', '3')
    markup.add('4', '5')
    await message.answer('Выберите рейс из предложенных ниже', reply_markup=markup)
    async with state.proxy() as data:
        for flight_info in data['flights_to_choose']:
            info_index = str(data['flights_to_choose'].index(flight_info) + 1)
            info = md.text(
                md.text(data["city_from"], flight_info[0], '-', data["city_to"], flight_info[1]),
                md.text('часов в полете -', flight_info[2]),
                sep='\n'
            )
            data[info_index] = info
            await message.answer(f"{info_index}) {info}")
    await models.update_user(message.chat.id, 'Выбор рейса')


def _ticket_date_check(message):
    try:
        if any([datetime.strptime(message.text, '%d-%m-%Y') < datetime.today(),
                datetime.strptime(message.text, '%d-%m-%Y') >= datetime.today() + timedelta(days=365)]
               ):
            return False
        else:
            return True
    except ValueError:
        return False


async def ticket_choose_flight_invalid(message: types.Message):
    """Билет выбран некорректно"""
    await message.answer('Выберите номер рейса от 1 до 5')


async def ticket_choose_flight(message: types.Message, state: FSMContext):
    """Билет выбран корректно"""
    async with state.proxy() as data:
        data['chosen_flight'] = message.text
        await message.answer(f'Выбран вариант {data["chosen_flight"]}')
        await message.answer(f'{data[data["chosen_flight"]]}')
        log.debug(f'{data}')

    await state.set_state(Steps.sits_number)
    await message.answer('Выберите количество мест от 1 до 5')
    await models.update_user(message.chat.id, 'Выбор количества мест')


async def ticket_choose_sits_invalid(message: types.Message):
    """Количество мест выбрано некорректно"""
    await message.answer('Выберите количество мест от 1 до 5')


async def ticket_choose_sits(message: types.Message, state: FSMContext):
    """Количество мест выбрано корректно"""
    async with state.proxy() as data:
        data['sits'] = message.text
        log.debug(f'{data}')

    await state.set_state(Steps.comment)
    await message.answer('Напишите дополнительные сведения о полете (комментарий)',
                         reply_markup=types.ReplyKeyboardRemove())
    await models.update_user(message.chat.id, 'Комментарий')


async def ticket_comment_invalid(message: types.Message):
    """Дополнительные сведения введены некорректно"""
    await message.answer('Напишите дополнительные сведения о полете (комментарий)')


async def ticket_comment(message: types.Message, state: FSMContext):
    """Дополнительные сведения о полете"""
    async with state.proxy() as data:
        data['comment'] = message.text
        log.debug(f'{data}')

    await state.set_state(Steps.validate_data)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add('Да', 'Нет')
    await message.answer(
        md.text(
            md.text('Выбранный рейс:'),
            md.text(data[data["chosen_flight"]]),
            md.text('Количество мест: ', data['sits']),
            md.text('Ваш комментарий:', data['comment']),
            sep='\n'
        ),
        reply_markup=types.ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN
    )
    await message.answer('Верны ли введенные данные? Да/Нет', reply_markup=markup)
    await models.update_user(message.chat.id, 'Подтверждение данных')


async def ticket_correct_data_invalid(message: types.Message, state: FSMContext):
    """Введенные данные неверны"""
    await state.finish()
    await message.answer('Для повторного заказа билетов введите /ticket', reply_markup=types.ReplyKeyboardRemove())
    await models.delete_user(message.chat.id)


async def ticket_correct_data(message: types.Message, state: FSMContext):
    """Введенные данные верны"""
    async with state.proxy() as data:
        data['correct_data'] = message.text
        log.debug(f'{data}')
    await state.set_state(Steps.phone_number)
    await message.answer('Укажите номер телефона для связи с Вами', reply_markup=types.ReplyKeyboardRemove())
    await models.update_user(message.chat.id, 'Ввод номера телефона')


async def ticket_phone_number_invalid(message: types.Message):
    """Некорректный номер телефона"""
    await message.answer('Некорректный номер телефона, введите номер телефона для связи с Вами')


async def ticket_phone_number(message: types.Message, state: FSMContext):
    """Корректный номер телефона"""
    async with state.proxy() as data:
        data['phone_number'] = message.text
        await message.answer(
            md.text('Спасибо за регистрацию. С вами свяжутся по указанному номеру телефона:',
                    data["phone_number"])
        )
        log.info(f'{message.chat.first_name} заполнил(а) форму для заказа авиабилетов. ID {message.chat.id}')
        log.info(f'Выбранный рейс: {data[data["chosen_flight"]]}')
        log.info(f'Количество мест: {data["sits"]}')
        log.info(f'Комментарий: {data["comment"]}')
        log.info(f'Номер телефона: {data["phone_number"]}\n')

        _data = [message.chat.id, message.chat.first_name, data[data["chosen_flight"]], data["sits"],
                 data["comment"], data["phone_number"]]
        await models.register_user(_data)
        await message.answer('Ваш электронный билет:')

        temp_ticket = await draw_ticket(str(message.chat.id))
        await message.answer_photo(temp_ticket)

    """Завершение сценария"""
    await state.finish()
    await models.delete_user(message.chat.id)


def register_handlers(_dp, config):
    """Регистрация обработчиков"""

    for command_info in config['command_handlers']:
        _dp.register_message_handler(command_info[0], commands=command_info[1], state=command_info[2])
        _dp.register_message_handler(command_info[0], command_info[3], state=command_info[2])

    for communicate_info in config['communicate_handlers']:
        _dp.register_message_handler(communicate_info[0], state=communicate_info[1])

    for handler_info in config['state_handlers']:
        _dp.register_message_handler(handler_info[0], handler_info[1], state=handler_info[2])


handlers_config = {

    'command_handlers': (
        (send_welcome, 'start', '*', Text(equals='/start', ignore_case=True)),
        (send_help, 'help', '*', Text(equals='/help', ignore_case=True)),
        (cancel_command, 'cancel', '*', Text(equals='/cancel', ignore_case=True)),
        (ticket_start, 'ticket', '*', Text(equals='/ticket', ignore_case=True)),
    ),

    'communicate_handlers': (
        (send_help, None),
    ),

    'state_handlers': [
        (ticket_from_invalid, lambda message: message.text.title() not in SFT.keys(), Steps.city_from),
        (ticket_from, lambda message: message.text.title() in SFT.keys(), Steps.city_from),
        (ticket_to_invalid, lambda message: message.text.title() not in SFT.keys(), Steps.city_to),
        (ticket_to, lambda message: message.text.title() in SFT.keys(), Steps.city_to),
        (ticket_date_invalid, lambda message: not _ticket_date_check(message), Steps.flight_date),
        (ticket_date, lambda message: _ticket_date_check(message), Steps.flight_date),
        (ticket_choose_flight_invalid,
         lambda message: not all([message.text.isdigit(), message.text in [str(x) for x in range(1, 6)]]),
         Steps.flight_choice),
        (ticket_choose_flight,
         lambda message: all([message.text.isdigit(), message.text in [str(x) for x in range(1, 6)]]),
         Steps.flight_choice),
        (ticket_choose_sits_invalid,
         lambda message: not all([message.text.isdigit(), message.text in [str(x) for x in range(1, 6)]]),
         Steps.sits_number),
        (ticket_choose_sits,
         lambda message: all([message.text.isdigit(), message.text in [str(x) for x in range(1, 6)]]),
         Steps.sits_number),
        (ticket_comment_invalid, lambda message: not message.text, Steps.comment),
        (ticket_comment, lambda message: message.text, Steps.comment),
        (ticket_correct_data_invalid, lambda message: message.text.title() != 'Да', Steps.validate_data),
        (ticket_correct_data, lambda message: message.text.title() == 'Да', Steps.validate_data),
        (ticket_phone_number_invalid,
         lambda message: not re.match(r'^(\d{3})\D?(\d{3})\D?(\d{4})\D?(\d*)$', message.text), Steps.phone_number),
        (ticket_phone_number,
         lambda message: re.match(r'^(\d{3})\D?(\d{3})\D?(\d{4})\D?(\d*)$', message.text), Steps.phone_number),
    ]
}
