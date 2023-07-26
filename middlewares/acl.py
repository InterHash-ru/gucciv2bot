import logging
import contextlib
from aiogram import types
from aiogram import Bot, Dispatcher
from aiogram.utils import exceptions
from datetime import datetime, timedelta
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware

class ACLMiddleware(BaseMiddleware):
	def __init__(self, db):
		super().__init__()
		self.db = db
		self.dp = Dispatcher

	async def check_private_chat(self, chat: types.Chat = None):
		chat_type = chat.type if chat else types.ChatType.PRIVATE
		if chat_type != types.ChatType.PRIVATE:
			raise CancelHandler

	async def setup_chat(self, data: dict, user: types.User, chat: types.Chat = None):
		# None if from_channel else await self.check_private_chat(chat)
		user_info = await self.db.get_info_user(chat_id = user.id)
		if not user_info:
			try:
				await self.db.add_new_user(user.id, user.username, user.full_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
			except:
				pass
			user_info = await self.db.get_info_user(chat_id = user.id)
			data['new_user'] = True
		else:
			data['new_user'] = False

		if user_info['kicked']:
			await self.db.update_kicked_user(user_info['chat_id'], 0)
		
		data['db'] = self.db
		data['dp'] = self.dp
		data['chat'] = chat
		data['user_info'] = user_info

	async def on_pre_process_message(self, message: types.Message, data: dict):
		await self.setup_chat(data, message.from_user, message.chat)

	async def on_pre_process_callback_query(self, call: types.CallbackQuery, data: dict):
		await self.setup_chat(data, call.from_user, call.message.chat if call.message else None)

	async def on_pre_process_inline_query(self, inline_query: types.InlineQuery, data: dict):
		user_info = await self.db.get_info_user(chat_id = inline_query.from_user.id)
		if user_info:
			data['db'] = self.db
			data['chat'] = inline_query.from_user
			data['user_info'] = user_info

	async def on_pre_process_my_chat_member(self, my_chat_member: types.ChatMemberUpdated, data: dict):
		await self.check_private_chat(my_chat_member.chat)
		chat_id = my_chat_member.from_user.id
		status = my_chat_member.new_chat_member.status
		status = 1 if status == "kicked" else 0
		await self.db.update_kicked_user(chat_id, status)
		raise CancelHandler

	async def on_pre_process_chat_join_request(self, update: types.ChatJoinRequest, data: dict):
		with contextlib.suppress(exceptions.TelegramAPIError):
			await update.approve()
		if update.values['from']['username'] == None or not await self.db.get_black_list_status(username = update.values['from']['username'].lower()):
			await self.setup_chat(data, update.values['from'], update.values['chat'], from_channel = True)
		else:
			raise CancelHandler

	async def on_pre_process_chosen_inline_result(self, chosen_inline_result: types.ChosenInlineResult, data: dict):
		await self.setup_chat(data, chosen_inline_result.from_user)