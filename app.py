from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor

import handlers

try:
    from settings import TOKEN, ADMIN_ID
except ImportError:
    exit('DO cp setting.py.default settings.py and set token.')

bot = Bot(token=TOKEN, parse_mode='HTML')

storage = MemoryStorage()

dp = Dispatcher(bot, storage=storage)

handlers.register_handlers(dp, handlers.handlers_config)


async def send_to_admin(*args):
    """Оповещение админа о запуске бота"""
    handlers.log.info('Бот запущен')
    await bot.send_message(chat_id=ADMIN_ID, text='Бот запущен')


if __name__ == '__main__':
    try:
        executor.start_polling(dp, skip_updates=True, on_startup=send_to_admin)
    except BaseException as exc:
        handlers.log.exception(exc)
