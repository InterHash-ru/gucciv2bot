import logging

from aiogram import Dispatcher
from aiogram.utils.exceptions import (TelegramAPIError, BotBlocked, InvalidQueryID, MessageCantBeDeleted, RetryAfter, MessageToDeleteNotFound)

async def errors_handler(update, exception):
	if isinstance(exception, TelegramAPIError):
		return True

	if isinstance(exception, BotBlocked):
		return True

	if isinstance(exception, InvalidQueryID):
		return True

	if isinstance(exception, MessageCantBeDeleted):
		return True

	if isinstance(exception, MessageToDeleteNotFound):
		return True

	logging.exception(f'Update: {update} \n{exception}')

def register_errors(dp: Dispatcher):
	dp.register_errors_handler(errors_handler)