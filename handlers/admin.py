import os
import re
import json
import asyncio
import logging
from io import BytesIO
import prettytable as pt
from datetime import datetime, timedelta

from aiogram import types
from aiogram import Dispatcher
from aiogram.utils import exceptions
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.handler import ctx_data
from aiogram.dispatcher.filters import Command, CommandStart, Text
from aiogram.utils.markdown import hbold, hcode, hitalic, hunderline, hstrikethrough, hlink

# FILES <
from misc.states import StatesBroadcast
from misc.filters import IsPrivate, IsAdmin
from misc.help import keyboard_gen, chunks_generators, format_number
from misc.callback_data import show_callback, target_callback, admin_callback, adminButton_callback, pagination_callback
# FILES >

#
# OTHER
#

async def page_home(call: types.CallbackQuery, callback_data: dict, db, user_info, settings):	
	keyboard = types.InlineKeyboardMarkup()
	keyboard.add(types.InlineKeyboardButton("✉️ Рассылка", callback_data = adminButton_callback.new(action = 'malling')),
		types.InlineKeyboardButton("📈 Статистика", callback_data = adminButton_callback.new(action = 'statistics')))
	keyboard.add(types.InlineKeyboardButton("📋 Логи ошибок", callback_data = adminButton_callback.new(action = 'error_log')),
		types.InlineKeyboardButton("🗃 Выгрузить базу", callback_data = adminButton_callback.new(action = 'dump_db')))
	await call.bot.send_message(chat_id = user_info['chat_id'], text = hbold("💎 Администратор, выберите команду для управления."), reply_markup = keyboard)


#
# LOGS
#

async def page_logs(call: types.CallbackQuery, callback_data: dict, db, user_info, settings):
	logs_size = os.path.getsize(settings['logs_path'])
	size_kb = round(logs_size / 1024)
	text = "\n".join([
		hbold("📋 Логи ошибок"),
		"",
		hitalic(settings['logs_path']) + " - " + hbold(str(size_kb) + " КБ") ,
	])

	keyboard = types.InlineKeyboardMarkup()
	keyboard.add(types.InlineKeyboardButton("📋 Выгрузить лог", callback_data = target_callback.new(action = "logs_download")))
	keyboard.add(types.InlineKeyboardButton("🗑 Очистить лог", callback_data = target_callback.new(action = "logs_clean")))
	await call.bot.send_message(chat_id = user_info['chat_id'], text = text, reply_markup = keyboard)


async def callback_logs(call: types.CallbackQuery, callback_data: dict, db, user_info, settings):
	if callback_data['action'] == "logs_download":
		msg = await call.bot.edit_message_text(chat_id = user_info['chat_id'], message_id = call.message.message_id, text = hbold("⏱ Ожидайте, загружаю информацию"))
		if os.path.getsize(settings['logs_path']):
			file = open(settings['logs_path'], 'rb')
			await call.bot.send_document(chat_id = user_info['chat_id'], document = file, caption = "Дата: " + hbold(str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))))
			await call.bot.delete_message(chat_id = user_info['chat_id'], message_id = msg.message_id)
		else:
			await call.bot.edit_message_text(chat_id = user_info['chat_id'], message_id = msg.message_id, text = hbold("📋 Логи ошибок пусты!"))
	elif callback_data['action'] == "logs_clean":
		with open(settings['logs_path'], 'w'):
			pass
		await call.bot.edit_message_text(chat_id = user_info['chat_id'], message_id = call.message.message_id, text = hbold("✅ Логи ошибок были очищены!"))

#
# USERS
#

async def page_users(call: types.CallbackQuery, callback_data: dict, db, user_info, settings):
	keyboard = types.InlineKeyboardMarkup()
	keyboard.add(types.InlineKeyboardButton("👥 Всех пользователей", callback_data = target_callback.new(action = "users_download_all")))
	keyboard.add(types.InlineKeyboardButton("👤 Активных пользователей", callback_data = target_callback.new(action = "users_download_active")))
	await call.bot.send_message(chat_id = user_info['chat_id'], text = hbold("🗃 Выгрузить базу"), reply_markup = keyboard)

async def callback_users(call: types.CallbackQuery, callback_data: dict, db, user_info):
	msg = await call.bot.edit_message_text(chat_id = user_info['chat_id'], message_id = call.message.message_id, text = hbold("⏱ Ожидайте, загружаю информацию"))
	users = await db.get_chat_id_users(True if callback_data['action'] == "users_download_active" else False)
	count = str(len(users))
	chat_ids = "\n".join([str(user['chat_id']) for user in users])
	file = BytesIO()
	file.write(chat_ids.encode())
	file.seek(0)
	file.name = count + '_users.txt'
	text = "\n".join([
		"Пользователей: " + hbold(count),
		"",
		"Дата: " + hbold(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
	])
	await call.bot.send_document(chat_id = user_info['chat_id'], document = file, caption = text)
	await call.bot.delete_message(chat_id = user_info['chat_id'], message_id = msg.message_id)
	file.close()

#
# STATISTICS
#

async def page_statistics(call: types.CallbackQuery, callback_data: dict, db, user_info, settings):
	msg = await call.bot.send_message(chat_id = user_info['chat_id'], text = hbold("⏱ Ожидайте, собираю информацию"))

	stats_users = await db.get_stats_users()
	hour_users = await db.get_stats_count(table = "users", separator = ">=", date_start = "NOW() - INTERVAL 1 HOUR")
	day_users = await db.get_stats_count(table = "users", separator = ">=", date_start = "NOW() - INTERVAL 1 DAY")
	action_day_users = await db.get_stats_count(table = "users", separator = ">=", date_last_action = "NOW() - INTERVAL 1 DAY")
	action = await db.get_stats_count(table = "users", kicked = "0")
	kicked = await db.get_stats_count(table = "users", kicked = "1")
	admins = await db.get_stats_count(table = "users", separator = ">=", is_admin = "1")

	all_wallets = await db.get_stats_count(table = "wallets")
	all_tron_wallet = await db.get_count_TRON_Wallet()
	all_eth_wallet = await db.get_count_ETH_Wallet()

	all_transaction = await db.get_stats_count(table = "history_transaction")

	text = "\n".join([
		hbold("📈 Статистика"),
		"",
		"Общее кол-во пользователей: " + hbold(format_number(stats_users['all_users'])) + hitalic(" чел."),
		"",
		hbold("Кол-во пользователей"),
		hitalic("▪️ новых за последний час: ") + hbold(format_number(hour_users['count'])) + hitalic(" чел."),
		hitalic("▪️ новых за последние 24 часа: ") + hbold(format_number(day_users['count'])) + hitalic(" чел."),
		hitalic("▪️ пользовались ботом за 24 часа: ") + hbold(format_number(action_day_users['count'])) + hitalic(" чел."),
		#
		hitalic("▪️ которые пользуются ботом: ") + hbold(format_number(action['count'])) + hitalic(" чел."),
		hitalic("▪️ которые остановили бота: ") + hbold(format_number(kicked['count'])) + hitalic(" чел."),
		"",
		"Общее кол-во",
		hitalic("▪️ кошельков: ") + hbold(format_number(all_wallets['count'])) + hitalic(" шт."),
		hitalic("▪️ USDT: ") + hbold(format_number(all_tron_wallet['count'])) + hitalic(" шт."),
		hitalic("▪️ ETH: ") + hbold(format_number(all_eth_wallet['count'])) + hitalic(" шт."),
		hitalic("▪️ всего транзакций: ") + hbold(format_number(all_transaction['count'])) + hitalic(" шт."),
		"",
		hbold("Общее кол-во"),
		hitalic("▫️ администраторов: ") + hbold(format_number(admins['count'])) + hitalic(" чел."),
	])

	keyboard = types.InlineKeyboardMarkup()
	keyboard.add(types.InlineKeyboardButton("Администраторы", callback_data = show_callback.new(action = "admins")))
	await call.bot.edit_message_text(chat_id = user_info['chat_id'], message_id = msg.message_id, text = text, reply_markup = keyboard)

async def callback_show_admins(call: types.CallbackQuery, callback_data: dict, db, settings):
	admins = await db.get_is_admin_users()
	text = "📄 Администраторы (" + str(len(admins)) + ")\n\n"
	text += "\n".join([admin['fullname'] + " - 👨‍💻 Администратор"  for admin in admins])
	await call.bot.answer_callback_query(callback_query_id = call.id, text = text, cache_time = 0, show_alert = True)


#
# BROADCAST
#

async def page_broadcast(call: types.CallbackQuery, callback_data: dict, db, user_info, settings, broadcast):
	if broadcast.status == "available" or broadcast.status == "stopped":
		text = hbold("✉️ Рассылка не запущена")
		keyboard = keyboard_gen([['✉️ Запустить рассылку'], ['◀️ Назад']])
	elif broadcast.status == "launched":
		text = "\n".join([
			hbold("⏳ Сейчас рассылка запущена"),
			"",
			hitalic("🔄 Осталось: ") + hbold(broadcast.stats_left),
			hitalic("✅ Успешно: ") + hbold(broadcast.stats_success),
			hitalic("❌ Неуспешно: ") + hbold(broadcast.stats_fail),
			"",
			hitalic("⏱ Время рассылки: ") + hbold(str(datetime.now() - broadcast.timer['date_start']).split(".")[0]),
			"",
			hbold("Используйте:"),
			hitalic("/edit - чтобы изменить сообщение"),
			hitalic("/stop - чтобы остановить рассылку"),
		])
		keyboard = keyboard_gen([['◀️ Назад']])
	elif broadcast.status == "waiting":
		text = "\n".join([
			hbold("⏱ Рассылка отложенна на: ") + hitalic(broadcast.timer['date']),
			"",
			hbold("Используйте:"),
			hitalic("/cancel - чтобы отменить рассылку"),
		])

		keyboard = keyboard_gen([['◀️ Назад']])
	# await message.answer(text = text, reply_markup = keyboard)
	await call.bot.send_message(chat_id = user_info['chat_id'], text = text, reply_markup = keyboard)
	await StatesBroadcast.action.set()

async def page_broadcast_action(message: types.Message, db, user_info, settings, broadcast, state: FSMContext):
	if message.content_type in ["text"]:
		if message.text == "◀️ Назад":
			await state.finish()
			await page_home(message, message, db, user_info, settings)
			return
		elif message.text == "✉️ Запустить рассылку":
			if broadcast.status == "available":
				await message.answer(text = hbold("✍️ Введите сообщение для рассылки:"), reply_markup = keyboard_gen([['⛔️ Отмена']]))
				await StatesBroadcast.message.set()
			else:
				await state.finish()
				await message.answer(text = hbold("❗️ Запущен другой рекламный пост"), reply_markup = keyboard_gen([['◀️ Назад']]))
		elif message.text == "/edit":
			if broadcast.status == "launched":
				await state.update_data(edit = True)
				await message.answer(text = hbold("✍️ Введите новое сообщение для рассылки:"), reply_markup = keyboard_gen([['⛔️ Отмена']]))
				await StatesBroadcast.message.set()
			else:
				await state.finish()
				await message.answer(text = hbold("❗️ Вы не можете изменить сообщение, рассылка не запущена"), reply_markup = keyboard_gen([['◀️ Назад']]))
		elif message.text == "/stop" or message.text == "/cancel":
			await state.finish()
			broadcast.status = "stopped"
		else:
			await message.answer(text = hbold("❗️ Используйте кнопки ниже"))
	else:
		await message.answer(text = hbold("❗️ Используйте кнопки ниже"))

async def page_broadcast_message(message: types.Message, db, user_info, settings, broadcast, state: FSMContext):
	if message.content_type in ["text"]:
		if message.text == "⛔️ Отмена":
			await state.finish()
			await page_broadcast(message, message, db, user_info, settings, broadcast)
			return
	
	await state.update_data(message = message, preview = True) if not (await state.get_data()).get("message") else None

	state_data = await state.get_data()
	msgObject = state_data.get("message")
	msgKeyboard = state_data.get("keyboard")
	msgTimer = state_data.get("timer")
	msgEdit = state_data.get("edit")
	msgPreview = state_data.get("preview")
	preview_url = [entities for entities in msgObject.entities if "url" in str(entities)]

	text = "\n".join([
		hbold("⚙️ Настройки рассылки:"),
		"",
		hitalic(" ▫️ Кнопки: ") + hbold("есть" if msgKeyboard else "прикреплены к посту" if msgObject and "reply_markup" in msgObject else "нету"),
		hitalic(" ▫️ Таймер: ") + hbold(msgTimer['date'] if msgTimer else "нету"),
		(hitalic(" ▫️ Предпросмотр ссылок: ") + hbold("выкл" if msgPreview else "вкл") + hitalic(" (/preview - изменить)") + "\n") if len(preview_url) else "",
		hitalic(" ❕ Чтобы сбросить \"Кнопки/Таймер\" нажмите ◀️ Назад"),
		hitalic(" ❕ В пересланном сообщение, кнопками нельзя сбросить") if msgObject and "reply_markup" in msgObject else ""
	])

	if msgEdit:
		keyboard = keyboard_gen([['➕ Добавить кнопки', '👀 Предпросмотр'], ['✉️ Отправить'], ['❌ Отменить']])
	else:
		keyboard = keyboard_gen([['➕ Добавить кнопки', '👀 Предпросмотр'], ['⏱ Таймер', '✉️ Отправить'], ['❌ Отменить']])
	await message.answer(text = text, reply_markup = keyboard)
	await StatesBroadcast.editor.set()

async def page_broadcast_editor(message: types.Message, db, user_info, settings, broadcast, telegram, state: FSMContext):
	if message.content_type in ["text"]:
		state_data = await state.get_data()
		msgObject = state_data.get("message")
		msgKeyboard = state_data.get("keyboard")
		msgEdit = state_data.get("edit")
		msgPreview = state_data.get("preview")

		if message.text in "➕ Добавить кнопки":
			text = "\n".join([
				hbold("➕ Добавить кнопки"),
				"",
				hitalic("❕ Формат: ") + hbold("Текст - ссылка | Текст - ссылка"),
			])
			await message.answer(text = text, reply_markup = keyboard_gen([['◀️ Назад']]))
			await StatesBroadcast.keyboard.set()
		elif message.text in "⏱ Таймер" and not msgEdit:
			text = "\n".join([
				hbold("⏱ Таймер"),
				"",
				hitalic("❕ Формат: ") + hbold("2025-12-01 10:00"),
			])
			await message.answer(text = text, reply_markup = keyboard_gen([['◀️ Назад']]))
			await StatesBroadcast.timeout.set()
		elif message.text in "👀 Предпросмотр":
			try:
				await msgObject.send_copy(chat_id = user_info['chat_id'], reply_markup = msgKeyboard, disable_web_page_preview = msgPreview)
			except:
				await message.answer(text = hbold("❗️ В кнопках указаны некорректные ссылки"))
		elif message.text in "✉️ Отправить":
			if msgEdit:
				await state.finish()
				broadcast.message = msgObject
				broadcast.keyboard = msgKeyboard
				await message.answer(text = hbold("✅ Сообщение успешно изменено!"), reply_markup = keyboard_gen([['◀️ Назад']]))
			else:
				await broadcast_run(message, db, user_info, settings, broadcast, telegram, state)
		elif message.text in "/preview":
			if msgPreview:
				await state.update_data(preview = False)
			else:
				await state.update_data(preview = True)
			await page_broadcast_message(message, db, user_info, settings, broadcast,  state)
		elif message.text in "❌ Отменить":
			await state.finish()
			await page_broadcast(message, message, db, user_info, settings, broadcast)
			return
		else:
			await message.answer(text = hbold("❗️ Используйте кнопки ниже"))
	else:
		await message.answer(text = hbold("❗️ Используйте кнопки ниже"))

async def page_broadcast_keyboard(message: types.Message, db, user_info, settings, broadcast, state: FSMContext):
	if message.content_type in ["text"]:
		if message.text == "◀️ Назад":
			await state.update_data(keyboard = None) if (await state.get_data()).get("keyboard") else None
			await page_broadcast_message(message, db, user_info, settings, broadcast,  state)
			return
	try:
		keyboard = types.InlineKeyboardMarkup()
		text_buttons = list(filter(None, message.text.split("\n")))
		for text_button in text_buttons:
			more = []
			buttons = text_button.split("|")
			for button in buttons:
				params = button.strip().split("-")
				more.append(types.InlineKeyboardButton(params[0].strip(), url = params[1].strip()))
			keyboard.add(*more)
		await state.update_data(keyboard = keyboard)
		await page_broadcast_message(message, db, user_info, settings, broadcast,  state)
	except Exception as e:
		await message.answer(text = hbold("❗️ Вы отправляете кнопки в неправильном формате"))

async def page_broadcast_timeout(message: types.Message, db, user_info, settings, broadcast, telegram, state: FSMContext):
	if message.content_type in ["text"]:
		if message.text == "◀️ Назад":
			await state.update_data(timer = None) if (await state.get_data()).get("timer") else None
			await page_broadcast_message(message, db, user_info, settings, broadcast,  state)
			return
	try:
		date = datetime.strptime(message.text, '%Y-%m-%d %H:%M')
		seconds_left = int(date.timestamp()) - int(datetime.now().timestamp())
		if seconds_left <= 0:
			await message.answer(text = hbold("❗️ Вы указали некорректную дату."))
			return
		await state.update_data(timer = {"date": date, "seconds_left": seconds_left})
		await page_broadcast_message(message, db, user_info, settings, broadcast,  state)
	except Exception as e:
		await message.answer(text = hbold("❗️ Вы указали некорректную дату."))

async def broadcast_notify(message, action):
	try:
		data = ctx_data.get()
		user_info = data.get('user_info')
		settings = data.get('settings')
		broadcast = data.get('broadcast')
		telegram = data.get('telegram')

		if action == "channel_message":
			broadcast.channel_message = await broadcast.message.send_copy(chat_id = settings['broadcast_channel'], reply_markup = broadcast.keyboard, disable_web_page_preview = broadcast.preview)
			return
		elif action == "launched":
			text = hbold("✅ Рассылка запущена!")
		elif action == "waiting":
			text = hbold("⏱ Рассылка отложенна на: ") + hitalic(broadcast.timer['date'])
		elif action == "waiting_stop":
			text = hbold("⛔️ Отложенная рассылка отменена!")
		elif action == "stopped":
			text = "\n".join([
				hbold("⛔️ Рассылка остановлена!"),
				"",
				hitalic("🔄 Осталось: ") + hbold(broadcast.stats_left),
				hitalic("✅ Успешно: ") + hbold(broadcast.stats_success),
				hitalic("❌ Неуспешно: ") + hbold(broadcast.stats_fail),
			])
		elif action == "finish":
			text = "\n".join([
				hbold("✉️ Рассылка выполнена!"),
				"",
				hitalic("✅ Успешно: ") + hbold(broadcast.stats_success),
				hitalic("❌ Неуспешно: ") + hbold(broadcast.stats_fail),
				"",
				hitalic("⏱ Время рассылки заняло: ") + hbold(str(datetime.now() - broadcast.timer['date_start']).split(".")[0]),
			])

		remove_markup = types.ReplyKeyboardRemove()
		await message.bot.send_message(chat_id = user_info['chat_id'], text = text, reply_markup = remove_markup)

		text += hitalic("\n\n🤖 Бот: @" + telegram['username'])
		text += hitalic("\n👤 Запустил: ") + hbold(user_info['fullname'])
		await message.bot.send_message(chat_id = settings['broadcast_channel'], reply_to_message_id = broadcast.channel_message.message_id, text = text)
	except Exception as e:
		pass

async def broadcast_sm(chat_id, broadcast):
	try:
		await broadcast.message.send_copy(chat_id = chat_id, reply_markup = broadcast.keyboard, disable_web_page_preview = broadcast.preview)
	except exceptions.RetryAfter as e:
		await asyncio.sleep(e.timeout)
		logging.exception(f'"| Broadcast RetryAfter | - (chat_id: {str(chat_id)}, ERROR: {str(e)}, Broadcast: {str(broadcast.__dict__)})\n\n')
		return await broadcast_sm(chat_id, broadcast)
	except Exception as e:
		broadcast.stats_fail += 1
	else:
		broadcast.stats_success += 1
	broadcast.stats_left -= 1

async def broadcast_run(message: types.Message, db, user_info, settings, broadcast, telegram, state: FSMContext):
	if broadcast.status == "available":
		state_data = await state.get_data()
		if state_data.get("timer"):
			if int(state_data.get("timer")['date'].timestamp()) - int(datetime.now().timestamp()) <= 0:
				await message.answer(text = hbold("❗️ Вы указали некорректную дату."))
				return
		await state.finish()

		broadcast.message = state_data.get("message")
		broadcast.keyboard = state_data.get("keyboard")
		broadcast.timer = state_data.get("timer")
		broadcast.preview = state_data.get("preview")

		await broadcast_notify(message, action = "channel_message")

		if broadcast.timer and broadcast.timer['seconds_left']:
			await broadcast_notify(message, action = "waiting")
			broadcast.status = "waiting"
			for i in range(broadcast.timer['seconds_left']):
				if broadcast.status == "stopped":
					await broadcast_notify(message, action = "waiting_stop")
					broadcast.declare_variables()
					return
				await asyncio.sleep(1)
		
		users = await db.get_chat_id_users(True)
		broadcast.stats_left = len(users)
		if broadcast.timer:
			broadcast.timer.update({"date_start": datetime.now()})
		else:
			broadcast.timer = {"date_start": datetime.now()}

		await broadcast_notify(message, action = "launched")
		broadcast.status = "launched"

		packs = list(chunks_generators(users, settings['broadcast_threads']))

		for users in packs:
			tasks = []
			if broadcast.status == "stopped":
				await broadcast_notify(message, action = "stopped")
				broadcast.declare_variables()
				return
			for user in users:
				tasks.append(asyncio.create_task(broadcast_sm(user['chat_id'], broadcast)))
			await asyncio.gather(*tasks)
			await asyncio.sleep(settings['broadcast_timeout'])

		await broadcast_notify(message, action = "finish")
		broadcast.declare_variables()
	else:
		await state.finish()
		await message.answer(text = hbold("❗️ Запущен другой рекламный пост"), reply_markup = keyboard_gen([['◀️ Назад']]))

def register_admin(dp: Dispatcher):
	# OTHER
	dp.register_callback_query_handler(page_home, IsPrivate(), IsAdmin(), admin_callback.filter())

	# LOGS
	dp.register_callback_query_handler(page_logs, IsPrivate(), IsAdmin(), adminButton_callback.filter(action = 'error_log'))
	# dp.register_message_handler(page_logs, IsPrivate(), IsAdmin(), text = "📋 Логи ошибок")
	dp.register_callback_query_handler(callback_logs, target_callback.filter(action = ["logs_download", "logs_clean"]))

	# USERS
	dp.register_callback_query_handler(page_users, IsPrivate(), IsAdmin(), adminButton_callback.filter(action = 'dump_db'))
	dp.register_callback_query_handler(callback_users, target_callback.filter(action = ["users_download_all", "users_download_active"]))


	# STATISTICS
	dp.register_callback_query_handler(page_statistics, IsPrivate(), IsAdmin(), adminButton_callback.filter(action = 'statistics'))
	dp.register_callback_query_handler(callback_show_admins, show_callback.filter(action = "admins"))

	# BROADCAST
	dp.register_callback_query_handler(page_broadcast, IsPrivate(), IsAdmin(), adminButton_callback.filter(action = 'malling'))
	dp.register_message_handler(page_broadcast_action, IsPrivate(), IsAdmin(1), state = StatesBroadcast.action, content_types = types.ContentTypes.ANY)
	dp.register_message_handler(page_broadcast_message, IsPrivate(), IsAdmin(1), state = StatesBroadcast.message, content_types = types.ContentTypes.ANY)
	dp.register_message_handler(page_broadcast_editor, IsPrivate(), IsAdmin(1), state = StatesBroadcast.editor, content_types = types.ContentTypes.ANY)
	dp.register_message_handler(page_broadcast_keyboard, IsPrivate(), IsAdmin(1), state = StatesBroadcast.keyboard, content_types = types.ContentTypes.ANY)
	dp.register_message_handler(page_broadcast_timeout, IsPrivate(), IsAdmin(1), state = StatesBroadcast.timeout, content_types = types.ContentTypes.ANY)
	