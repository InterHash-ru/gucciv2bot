import os
import asyncio
import logging
from config import *
from models.database import *
from aiogram import Bot, Dispatcher
from aiogram.types import ParseMode
from handlers.check_eth import CheckTransactions
from aiogram.contrib.fsm_storage.memory import MemoryStorage

storage = MemoryStorage()

bot = Bot(token=TELEGRAM['token'], parse_mode=ParseMode.HTML, validate_token=True)
dp = Dispatcher(bot, storage = storage)
db = Database(MYSQL_INFO)
Blockchain = CheckTransactions(bot, dp, db, API_KEY['tronscan'], ABI['abi'])

asyncio.run(Blockchain.TrackingTransfers())
