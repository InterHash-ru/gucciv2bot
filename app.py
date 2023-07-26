
import os
import asyncio
import logging

import threading

from aiogram import Bot, Dispatcher
from aiogram.types import ParseMode
from aiogram.contrib.fsm_storage.memory import MemoryStorage
# from aiogram.contrib.fsm_storage.redis import RedisStorage2, RedisStorage
from aiogram.contrib.middlewares.environment import EnvironmentMiddleware

# FILES <
from config import *
from utils.broadcast import *
from misc.set_bot_commands import *
from models.database import *
from middlewares.acl import *
from middlewares.user_update import *

from handlers.user import *
from handlers.admin import *
from handlers.errors import *
from handlers.check_usdt import CheckTransactions
from misc.set_bot_commands import *
# FILES >


class BotRunner():
	def __init__(self, bot, dp, db):
		self.bot = bot
		self.dp = dp
		self.db = db

	logger = logging.getLogger(__name__)

	async def main(self):
		if SETTINGS['debug_mode']:
			if os.name == "nt":
				os.system("cls")
			else:
				os.system("clear")
		else:
			logging.basicConfig(
				level=logging.INFO,
				filename=SETTINGS['logs_path'],
				format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
			)

		await self.db.create_pool()
		await set_default_commands(self.dp)
		
		context = {
			"telegram": TELEGRAM,
			"settings": SETTINGS,
			"api": API_KEY,
			"broadcast": Broadcast()
		}
		self.dp.middleware.setup(EnvironmentMiddleware(context))
		# dp.middleware.setup(ThrottlingMiddleware())
		self.dp.middleware.setup(ACLMiddleware(self.db))
		self.dp.middleware.setup(UserUpdateMiddleware())

		# Регистрируем хендлеры
		register_user(self.dp)
		register_admin(self.dp)
		register_errors(self.dp)

		try:
			await self.dp.skip_updates()
			await self.dp.start_polling()
		finally:
			await self.dp.storage.close()
			await self.dp.storage.wait_closed()
			await self.bot.session.close()


if __name__ == '__main__':
	try:
		storage = MemoryStorage()

		bot = Bot(token=TELEGRAM['token'], parse_mode=ParseMode.HTML, validate_token=True)
		dp = Dispatcher(bot, storage = storage)
		db = Database(MYSQL_INFO)
		BotRunner = BotRunner(bot, dp, db)

		loop = asyncio.get_event_loop()
		loop.run_until_complete(BotRunner.main())
	except (KeyboardInterrupt, SystemExit):
		pass
