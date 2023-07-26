from aiogram import types
from aiogram.dispatcher.filters import BoundFilter
from aiogram.dispatcher.handler import ctx_data

class IsPrivate(BoundFilter):
	async def check(self, message: types.message) -> bool:
		data = ctx_data.get()
		return data['chat']['type'] == types.ChatType.PRIVATE

class IsAdmin(BoundFilter):
	def __init__(self, admin: bool = None):
		self.admin = admin

	async def check(self, message: types.message) -> bool:
		data = ctx_data.get()
		if data['user_info']['is_admin'] == 2 or data['user_info']['is_admin'] == self.admin:
			return True
		else:
			return False