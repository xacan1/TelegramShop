import asyncio
from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import config

storage = MemoryStorage()
loop = asyncio.new_event_loop()
bot = Bot(config.BOT_TOKEN, parse_mode='html')
dp = Dispatcher(bot, loop=loop, storage=storage)


if __name__ == '__main__':
    from handlers import dp
    executor.start_polling(dp)
