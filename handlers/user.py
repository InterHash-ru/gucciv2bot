import re
import json
import asyncio
import requests
import binascii

from web3 import Web3
from aiogram import types
from aiogram import Dispatcher
from datetime import datetime, timedelta
from aiogram.dispatcher import FSMContext
from aiogram.utils.deep_linking import get_start_link
from aiogram.dispatcher.filters import Command, CommandStart, Text
from aiogram.utils.markdown import hbold, hcode, hitalic, hunderline, hstrikethrough, hlink


# FILES <
from misc.translate import language
from misc.states import StatesAddWallet, StatesEditName
from misc.filters import IsPrivate, IsAdmin
from misc.help import keyboard_gen, format_number, chunks_generators
from misc.callback_data import pagination_callback, addWallet_callback, network_callback, cancel_callback, settings_callback, settingWallet_callback, history_trans_callback, pagination_history_callback, filter_trans_callback, transfer_network_callback
from misc.callback_data import language_callback, admin_callback, nameWallet_callback, wallet_callback, settingsPage_callback, walletInfo_callback, editWallet_callback, switch_trans_callback, notification_callback, amount_set_callback
# FILES >

#
# EXTRA FUNCTIONS
#

def get_eth_to_usd_rate():
	coingecko_api_url = "https://api.coingecko.com/api/v3/simple/price"
	params = {
		"ids": "ethereum",
		"vs_currencies": "usd",
		
		}
	response = requests.get(coingecko_api_url, params=params)

	if response.ok:
		result = response.json()
		if "ethereum" in result and "usd" in result["ethereum"]:
			return result["ethereum"]["usd"]
	else:
		response.raise_for_status()

def is_validate_USDTaddress(address):
	headers = {
		"accept": "application/json",
		"content-type": "application/json"
			}
	payload = {
		"address": address
			}
	result = requests.post("https://api.trongrid.io/wallet/validateaddress", json = payload, headers = headers)
	if result.status_code != 200:
		return False
	try:
		if result.json().get("result", False) == True:
			return address
	except:
		return False

def is_validate_ETHaddress(address, api):
	web3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/" + api['infura']))
	wallet = web3.is_checksum_address(address)
	return address if wallet else False
	
def get_balance_USDT(address, API_KEY):
	payload = {
		"address": address
	}
	headers = {
		"TRON-FREE-API-KEY" : API_KEY
	}
	result = requests.get("https://apilist.tronscan.org/api/account", headers = headers, params = payload)
	if result:
		token_balance = next((item for item in json.loads(result.text)["trc20token_balances"] if item["tokenAbbr"] == "USDT"), False)
		if token_balance == False:
			return False
		else:
			return float(token_balance["balance"]) / 1000000
	else:
		return False

def get_balance_ETH(address, infura):
	try:
		web3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/" + infura))
		balance = web3.eth.get_balance(address)
		amount_eth = int(balance) / 10 ** 18
		eth_to_usd = get_eth_to_usd_rate()
		balance_usd = amount_eth * eth_to_usd
		return balance_usd, amount_eth
	except :
		return False

def get_balance_usdt_token(address, infura, abi):
		try:
			web3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/" + infura))
			contract = web3.eth.contract(address = Web3.to_checksum_address("0xdac17f958d2ee523a2206206994597c13d831ec7"), abi = abi)
			balance_usdt_tokens = contract.functions.balanceOf(address).call()
			balance_usdt_tokens = int(balance_usdt_tokens / (10 ** 6))
			return balance_usdt_tokens
		except:
			return False

def convert_to_decimal(amount, decimal = 6):
	return int(amount * (10 ** decimal))

def convert_from_decimal(amount, decimal = 6):
	return (amount / (10 ** decimal))		

async def create_wallet_list(db, user_info, p = 0):
	array = list(chunks_generators(await db.get_users_wallet(chat_id = user_info['chat_id']), 10))
	pages = len(array)
	pages_count = str(pages - 1)
	keyboard = types.InlineKeyboardMarkup()
	for item in array[p]:
		network = "🔸" if item['network'] == "TRON" else "🔹"
		if item['network'] == "ETH":
			if item['transfer_usdt'] == 1:
				balance = str('{0:,}'.format(int(item['balance_usdt_tokens'])).replace(',', ',')) + " USDT"
			else:
				balance = str('{0:,}'.format(int(item['balance'])).replace(',', ',')) + " $"
		else:
			balance = str('{0:,}'.format(int(item['balance'])).replace(',', ',')) + " $"

		keyboard.add(types.InlineKeyboardButton(network + "    " + item['name'] + "    " + balance, callback_data = walletInfo_callback.new(action = "info", id = item['id'])))
	if len(array) > 1:
		keyboard.add(
			types.InlineKeyboardButton("◀️", callback_data = pagination_callback.new(action = 'left', page = p, all_pages = pages_count)),
			types.InlineKeyboardButton(f"{p + 1} / " + str(pages), callback_data = pagination_callback.new(action = 'count', page = 0, all_pages = pages_count)),
			types.InlineKeyboardButton("▶️", callback_data = pagination_callback.new(action = 'right', page = p, all_pages = pages_count)))
	keyboard.add(types.InlineKeyboardButton(language("➕ Добавить кошелёк", user_info['language']), callback_data = addWallet_callback.new(action = "add")))
	return keyboard

async def create_history_list(db, user_info, id_wallet, p = 0):
	wallet = await db.get_info_wallet(id = id_wallet)
	array = list(chunks_generators(await db.get_history_transaction(address = wallet['address']), 10))
	pages = len(array)
	pages_count = str(pages - 1)
	keyboard = types.InlineKeyboardMarkup()
	url = "https://tronscan.org/#/transaction/" if wallet['network'] == "TRON" else "https://etherscan.io/tx/"
	for item in array[p]:
		direction = "⬇️" if item['_to'] == wallet['address'] else "⬆️"
		_from = item['_from'][:4] + '...' + item['_from'][-5:]
		_to = item['_to'][:4] + '...' + item['_to'][-5:]
		keyboard.add(types.InlineKeyboardButton(direction + "   from: " + _from + "   to: " + _to +"   SUM: " + str('{0:,}'.format(int(item['amount'])).replace(',', '.')) + " $", url = url + item['hash_trans']))
	if len(array) > 1:
		keyboard.add(
			types.InlineKeyboardButton("◀️", callback_data = pagination_history_callback.new(action = 'left', page = p, all_pages = pages_count, id = id_wallet)),
			types.InlineKeyboardButton(f"{p + 1} / " + str(pages), callback_data = pagination_history_callback.new(action = 'count', page = 0, all_pages = pages_count, id = id_wallet)),
			types.InlineKeyboardButton("▶️", callback_data = pagination_history_callback.new(action = 'right', page = p, all_pages = pages_count, id = id_wallet)))
		keyboard.add(types.InlineKeyboardButton(language("↩️ Назад", user_info['language']), callback_data = walletInfo_callback.new(action = 'StepBack', id = id_wallet)))

	return keyboard


#
# HANDLERS USERS
#

async def command_start(message: types.Message, db, user_info, telegram, settings, new_user = False):
	try:
		await state.finish()
		await message.bot.delete_message(user_info['chat_id'], message.message_id - 1)
	except:
		pass

	wallets = await db.get_users_wallet(chat_id = user_info['chat_id'])
	if wallets:
		keyboard = types.InlineKeyboardMarkup()
		keyboard.add(types.InlineKeyboardButton(language("🗂 Кошельки", user_info['language']), callback_data = wallet_callback.new(action = "walletsPage")))
		if user_info['is_admin'] > 0:
			keyboard.add(types.InlineKeyboardButton(language("⚙️ Управление", user_info['language']), callback_data = admin_callback.new(action = 'adm_panel')))
		await message.bot.send_photo(chat_id = user_info['chat_id'], photo = settings['media'][0]['start'], reply_markup = keyboard)
	else:
		keyboard = types.InlineKeyboardMarkup()
		keyboard.add(types.InlineKeyboardButton(language("➕ Добавить кошелёк", user_info['language']), callback_data = addWallet_callback.new(action = 'addWallet')))
		if user_info['is_admin'] > 0:
			keyboard.add(types.InlineKeyboardButton(language("⚙️ Управление", user_info['language']), callback_data = admin_callback.new(action = 'adm_panel')))
		text = "\n".join([
			telegram['username'],
			"",
			language("Добавляй Tron и Ethereum кошельки, чтобы получать уведомления о всех транзакциях и следить за балансами", user_info['language']),
		])
		await message.bot.send_photo(user_info['chat_id'], photo = settings['media'][0]['start'], caption = text, reply_markup = keyboard)

async def wallets_call(call: types.CallbackQuery, callback_data: dict, db, user_info, settings, telegram):
	await call.bot.delete_message(user_info['chat_id'], call.message.message_id)
	await wallets(call, db, user_info, telegram, settings)

async def wallets(message: types.Message, db, user_info, telegram, settings):
	wallets = await db.get_users_wallet(chat_id = user_info['chat_id'])
	if wallets:
		all_balance = await db.get_total_balance(chat_id = user_info['chat_id'])
		await message.bot.send_message(user_info['chat_id'], text = language("Всего ≈ ", user_info['language']) + hcode(str('{0:,}'.format(int(all_balance['total'])).replace(',', '.')) + " $"), reply_markup = await create_wallet_list(db, user_info))
	else:
		keyboard = types.InlineKeyboardMarkup()
		keyboard.add(types.InlineKeyboardButton(language("➕ Добавить кошелёк", user_info['language']), callback_data = addWallet_callback.new(action = 'addWallet')))
		text = "\n".join([
			language("Твои кошельки будут отображаться тут", user_info['language']),
			"",
			language("Добавь свой первый кошелек чтобы получать уведомления о транзакциях и отслеживать балансы", user_info['language']),
		])
		await message.bot.send_message(chat_id = user_info['chat_id'], text = text, reply_markup = keyboard)

async def callback_pagination(call: types.CallbackQuery, callback_data: dict, db, user_info):
	if callback_data['action'] == "count":
		await call.bot.answer_callback_query(callback_query_id = call.id, text = 'Это просто счетчик страниц 😇', cache_time = 0, show_alert = True)
		return
	if callback_data['action'] == "left":
		if callback_data['page'] == "0":
			await call.bot.answer_callback_query(callback_query_id = call.id, text = 'Больше страниц нету 🙄', cache_time = 0, show_alert = True)
			return
		markup = await create_wallet_list(db, user_info, int(callback_data['page']) - 1)
	elif callback_data['action'] == "right":
		if callback_data['page'] == callback_data['all_pages']:
			await call.bot.answer_callback_query(callback_query_id = call.id, text = 'Больше страниц нету 🙄', cache_time = 0, show_alert = True)
			return
		markup = await create_wallet_list(db, user_info, int(callback_data['page']) + 1)

	all_balance = await db.get_total_balance()

	await call.bot.edit_message_text(
		chat_id			= user_info['chat_id'],
		message_id		= call.message.message_id,
		text			= language("Всего ≈ ", user_info['language']) + hcode(str('{0:,}'.format(int(all_balance['total'])).replace(',', '.')) + " $"),
		reply_markup	= markup
		)

async def show_info_from_wallet(call: types.CallbackQuery, callback_data: dict, db, user_info, api, abi, state: FSMContext):
	try:
		await state.finish()
	except:
		pass

	wallet = await db.get_info_wallet(id = callback_data['id'])
	keyboard = types.InlineKeyboardMarkup()
	keyboard.add(
				types.InlineKeyboardButton(language("🗓 Транзакции", user_info['language']), callback_data = history_trans_callback.new(action = 'trans_history', id = callback_data['id'])),
				types.InlineKeyboardButton(language("⚙️ Настройки", user_info['language']), callback_data = settingWallet_callback.new(action = 'setting_wallet', id = callback_data['id'])),
				types.InlineKeyboardButton("🖥 Etherscan", url = "https://etherscan.io/address/" + wallet['address']) if wallet['network'] == "ETH" else types.InlineKeyboardButton("🖥 Tronscan", url = "https://tronscan.org/#/address/" + wallet['address']),
				)
	keyboard.add(types.InlineKeyboardButton(language("↩️ Назад", user_info['language']), callback_data = wallet_callback.new(action = 'back')))

	if wallet['network'] == "ETH":
		text = '\n'.join([
			hbold("🔹" + wallet['name']) if wallet['network'] == "ETH" else hbold("🔸" + wallet['name']),
			"",
			language("💵 Баланс ETH: ≈ ", user_info['language']) + str('{0:,}'.format(int(wallet['balance'])).replace(',', ',')) + " $" + hitalic(f" ({round(wallet['balance_eth'], 2)} ETH)") if int(wallet['balance']) > 0 else language("💵 Баланс ETH: ") + hcode("0$"),
			language("💲 Баланс USDT: ", user_info['language']) + str('{0:,}'.format(int(wallet['balance_usdt_tokens'])).replace(',', ',')) + " USDT" if wallet['balance_usdt_tokens'] else language("💲 Баланс USDT: ", user_info['language']) + hcode("0 USDT"),
			"",
			hcode(wallet['address']),
			])
	elif wallet['network'] == "TRON":
		text = '\n'.join([
			hbold("🔹" + wallet['name']) if wallet['network'] == "ETH" else hbold("🔸" + wallet['name']),
			"",
			language("🏦 Баланс: ≈ ", user_info['language']) + hitalic(str('{0:,}'.format(int(wallet['balance'])).replace(',', '.')) + " $"),			"",
			"",
			hcode(wallet['address']),
			])
	await call.bot.edit_message_text(chat_id = user_info['chat_id'], message_id = call.message.message_id, text = text, reply_markup = keyboard, disable_web_page_preview = True)

async def page_settings_wallet(call: types.CallbackQuery, callback_data: dict, db, user_info, settings, telegram):
	wallet = await db.get_info_wallet(id = callback_data['id'])
	keyboard = types.InlineKeyboardMarkup()
	keyboard.add(types.InlineKeyboardButton(language("⬇️ Доходные транзации: ВКЛ", user_info['language']) if wallet['input_transactions'] == 1 else language("⬇️ Доходные транзации: ВЫКЛ", user_info['language']), callback_data = switch_trans_callback.new(action = 'input', id = callback_data['id'])))
	keyboard.add(types.InlineKeyboardButton(language("⬆️ Расходные транзакции: ВКЛ", user_info['language']) if wallet['outgoing_transactions'] == 1 else language("⬆️ Расходные транзакции: ВЫКЛ", user_info['language']), callback_data = switch_trans_callback.new(action = 'output', id = callback_data['id'])))
	keyboard.add(types.InlineKeyboardButton(language("🎛 Фильтр транзакций: ВЫКЛ", user_info['language']) if wallet['amount_filter'] == 0 else language("🎛 Фильтр транзакций: ", user_info['language']) + str(wallet['amount_filter']) + "$", callback_data = filter_trans_callback.new(action = 'editFilter', id = callback_data['id'])))
	if wallet['network'] == "ETH":
		keyboard.add(
					types.InlineKeyboardButton("USDT: ✅" if wallet['transfer_usdt'] == 1 else "USDT: ❌", callback_data = transfer_network_callback.new(action = 'usdt', id = callback_data['id'])),
					types.InlineKeyboardButton("ETH: ✅" if wallet['transfer_eth'] == 1 else "ETH: ❌", callback_data = transfer_network_callback.new(action = 'eth', id = callback_data['id'])),
					)
	keyboard.add(
				types.InlineKeyboardButton(language("✏️ Название", user_info['language']), callback_data = editWallet_callback.new(action = 'editName', id = callback_data['id'])),
				types.InlineKeyboardButton(language("🗑 Удалить", user_info['language']), callback_data = editWallet_callback.new(action = 'delete', id = callback_data['id'])),
				)
	keyboard.add(types.InlineKeyboardButton(language("↩️ Назад", user_info['language']), callback_data = walletInfo_callback.new(action = 'StepBack', id = callback_data['id'])))

	await call.bot.edit_message_text(chat_id = user_info['chat_id'], message_id = call.message.message_id, text = hbold("⚙️ " + wallet['name']), reply_markup = keyboard, disable_web_page_preview = True)

async def page_history_transaction(call: types.CallbackQuery, callback_data: dict, db, user_info, settings, telegram):
	wallet = await db.get_info_wallet(id = callback_data['id'])

	transactions = await db.get_history_transaction(address = wallet['address'])
	if transactions:
		text = '\n'.join([
			language("🗃 История кошелька: ", user_info['language']) + hbold(wallet['name']) + language(" | Всего: ", user_info['language']) + str(len(await db.get_history_transaction(address = wallet['address'])))
			])
		await call.bot.edit_message_text(chat_id = user_info['chat_id'], message_id = call.message.message_id, text = text, reply_markup = await create_history_list(db, user_info, callback_data['id']), disable_web_page_preview = True)
	else:
		await call.bot.answer_callback_query(callback_query_id = call.id, text = language('История транзакций пуста', user_info['language']), cache_time = 0, show_alert = True)

async def callback_transaction_pagination(call: types.CallbackQuery, callback_data: dict, db, user_info):
	if callback_data['action'] == "count":
		await call.bot.answer_callback_query(callback_query_id = call.id, text = language('Это счетчик страниц', user_info['language']), cache_time = 0, show_alert = True)
		return
	if callback_data['action'] == "left":
		if callback_data['page'] == "0":
			await call.bot.answer_callback_query(callback_query_id = call.id, text = language('Больше страниц нету', user_info['language']), cache_time = 0, show_alert = True)
			return
		markup = await create_history_list(db, user_info, callback_data['id'], int(callback_data['page']) - 1)
	elif callback_data['action'] == "right":
		if callback_data['page'] == callback_data['all_pages']:
			await call.bot.answer_callback_query(callback_query_id = call.id, text = language('Больше страниц нету', user_info['language']), cache_time = 0, show_alert = True)
			return
		markup = await create_history_list(db, user_info, callback_data['id'], int(callback_data['page']) + 1)

	wallet = await db.get_info_wallet(id = callback_data['id'])
	text = '\n'.join([
		language("🗃 История кошелька: ", user_info['language']) + hbold("'" + wallet['name'] + "'") + language(" | Всего: ", user_info['language']) + str(len(await db.get_history_transaction(address = wallet['address'])))
		])

	await call.bot.edit_message_text(
		chat_id			= user_info['chat_id'],
		message_id		= call.message.message_id,
		text			= text,
		reply_markup	= markup
		)

async def custom_transaction_display(call: types.CallbackQuery, callback_data: dict, db, user_info, settings, telegram):
	wallet = await db.get_info_wallet(id = callback_data['id'])
	if callback_data['action'] == "input":
		await db.input_transaction_display(id = callback_data['id'], value = "0" if wallet['input_transactions'] == 1 else "1")
	elif callback_data['action'] == "output":
		await db.output_transaction_display(id = callback_data['id'], value = "0" if wallet['outgoing_transactions'] == 1 else "1")
	await page_settings_wallet(call, callback_data, db, user_info, settings, telegram)

async def page_filter_transaction(call: types.CallbackQuery, callback_data: dict, db, user_info, settings, telegram):
	wallet = await db.get_info_wallet(id = callback_data['id'])
	keyboard = types.InlineKeyboardMarkup(row_width = 4)
	keyboard.add(
				types.InlineKeyboardButton("1$", callback_data = amount_set_callback.new(amount = '1', id = callback_data['id'])),
				types.InlineKeyboardButton("3$", callback_data = amount_set_callback.new(amount = '3', id = callback_data['id'])),
				types.InlineKeyboardButton("5$", callback_data = amount_set_callback.new(amount = '5', id = callback_data['id'])),
				types.InlineKeyboardButton("10$", callback_data = amount_set_callback.new(amount = '10', id = callback_data['id'])),
				types.InlineKeyboardButton("100$", callback_data = amount_set_callback.new(amount = '100', id = callback_data['id'])),
				types.InlineKeyboardButton("1000$", callback_data = amount_set_callback.new(amount = '1000', id = callback_data['id'])),
				types.InlineKeyboardButton("10000$", callback_data = amount_set_callback.new(amount = '10000', id = callback_data['id'])),
				)
	keyboard.add(types.InlineKeyboardButton(language("↩️ Назад", user_info['language']), callback_data = walletInfo_callback.new(action = 'StepBack', id = callback_data['id'])))

	network_emoji = " 🔹" if wallet['network'] == "ETH" else " 🔸"
	text = '\n'.join([
		hbold(language("🎛 Настройки кошелька ", user_info['language']) + str(wallet['name'])) + network_emoji,
		"",
		language("Выбери сумму, меньше которой не нужно уведомлять о транзакциях", user_info['language']),
		"",
		hitalic(language("Нажмите на ту же сумму, чтобы выключить фильтр", user_info['language'])),
		])

	await call.bot.edit_message_text(chat_id = user_info['chat_id'], message_id = call.message.message_id, text = text, reply_markup = keyboard)

async def custom_transaction_filter(call: types.CallbackQuery, callback_data: dict, db, user_info, settings, telegram):
	wallet = await db.get_info_wallet(id = callback_data['id'])
	await db.update_transaction_filter(id = callback_data['id'], value = callback_data['amount'] if int(wallet['amount_filter']) != int(callback_data['amount']) else "0")
	await page_settings_wallet(call, callback_data, db, user_info, settings, telegram)

async def custom_network_transaction_filter(call: types.CallbackQuery, callback_data: dict, db, user_info, settings, telegram):
	wallet = await db.get_info_wallet(id = callback_data['id'])
	if callback_data['action'] == "usdt":
		await db.usdt_trans_filter(id = callback_data['id'], value = 0 if wallet['transfer_usdt'] == 1 else 1)
	elif callback_data['action'] == "eth":
		await db.eth_trans_filter(id = callback_data['id'], value = 0 if wallet['transfer_eth'] == 1 else 1)
	await page_settings_wallet(call, callback_data, db, user_info, settings, telegram)

async def edit_name_wallet(call: types.CallbackQuery, callback_data: dict, db, user_info, settings, telegram, state: FSMContext):
	wallet = await db.get_info_wallet(id = callback_data['id'])
	if callback_data['action'] == "editName":

		keyboard = types.InlineKeyboardMarkup()
		keyboard.add(types.InlineKeyboardButton(language("↩️ Назад", user_info['language']), callback_data = walletInfo_callback.new(action = 'StepBack', id = callback_data['id'])))
		text = '\n'.join([
			hbold(language("🖌 Отправьте новое название кошелька", user_info['language']))
			])
		await call.bot.edit_message_text(chat_id = user_info['chat_id'], message_id = call.message.message_id, text = text, reply_markup = keyboard, disable_web_page_preview = True)
		async with state.proxy() as array:
			array['address'] = wallet['address']
			await StatesEditName.get_name.set()
	elif callback_data['action'] == "delete":
		keyboard = types.InlineKeyboardMarkup()
		keyboard.add(types.InlineKeyboardButton(language("🗑 Удалить", user_info['language']), callback_data = editWallet_callback.new(action = 'reject', id = callback_data['id'])),
					types.InlineKeyboardButton(language("↩️ Назад", user_info['language']), callback_data = walletInfo_callback.new(action = 'StepBack', id = callback_data['id'])))
		text = '\n'.join([
			hbold(language("⚠️ Вы действительно хотите удалить кошелек?", user_info['language']))
			])
		await call.bot.edit_message_text(chat_id = user_info['chat_id'], message_id = call.message.message_id, text = text, reply_markup = keyboard, disable_web_page_preview = True)
	elif callback_data['action'] == "reject":
		await db.delete_wallet(id = callback_data['id'])
		await call.bot.delete_message(user_info['chat_id'], call.message.message_id)
		await wallets(call, db, user_info, telegram, settings)

async def get_new_name_wallet(message: types.Message, db, user_info, settings, telegram, api, state: FSMContext):
	if message.text:
		if len(message.text) > 35:
			await message.reply(language("⚠️ Слишком большая длинна", user_info['language']), reply_markup = keyboard)
		else:
			async with state.proxy() as array:
				await db.set_name_wallet(address = array['address'], chat_id = user_info['chat_id'], name = message.text)
				await message.bot.send_message(chat_id = user_info['chat_id'], text = hbold(language("✅ Название кошелька успешно изменено", user_info['language'])))
				await state.finish()
				await wallets(message, db, user_info, telegram, settings)
	else:
		await message.reply(language("⚠️ Поддерживается исключительно текст", user_info['language']))

async def page_add_wallet(call: types.CallbackQuery, callback_data: dict, db, user_info, settings, telegram):
	keyboard = types.InlineKeyboardMarkup()
	keyboard.add(types.InlineKeyboardButton("🔹 Ethereum", callback_data = network_callback.new(network = 'ETH')),
		types.InlineKeyboardButton("🔸 Tron", callback_data = network_callback.new(network = 'TRON')))
	keyboard.add(types.InlineKeyboardButton(language("✖️ Отмена", user_info['language']), callback_data = cancel_callback.new(action = 'cancel')))

	await call.bot.delete_message(user_info['chat_id'], call.message.message_id)
	await call.bot.send_message(chat_id = user_info['chat_id'], text = language("Выберите сеть:", user_info['language']), reply_markup = keyboard)

async def choosing_walletNetwork(call: types.CallbackQuery, callback_data: dict, db, user_info, settings, telegram, state: FSMContext):
	if callback_data['network'] == "TRON":
		async with state.proxy() as array:
			array['try'] = 1
		keyboard = types.InlineKeyboardMarkup()
		keyboard.add(types.InlineKeyboardButton(language("✖️ Отмена", user_info['language']), callback_data = cancel_callback.new(action = 'cancel')))
		await call.bot.edit_message_text(chat_id = user_info['chat_id'], message_id = call.message.message_id, text = language("📍 Отправьте адресс TRON кошелька:", user_info['language']), reply_markup = keyboard)
		await StatesAddWallet.get_TronAddress.set()
	elif callback_data['network'] == "ETH":
		async with state.proxy() as array:
			array['try'] = 1
		keyboard = types.InlineKeyboardMarkup()
		keyboard.add(types.InlineKeyboardButton(language("✖️ Отмена", user_info['language']), callback_data = cancel_callback.new(action = 'cancel')))
		await call.bot.edit_message_text(chat_id = user_info['chat_id'], message_id = call.message.message_id, text = language("📍 Отправьте адресс ETH кошелька:", user_info['language']), reply_markup = keyboard)
		await StatesAddWallet.get_ETHAddress.set()

async def cancel_addWallet(call: types.CallbackQuery, callback_data: dict, db, user_info, settings, telegram, state: FSMContext):
	await state.finish()
	await call.bot.delete_message(user_info['chat_id'], call.message.message_id)
	await command_start(call, db, user_info, telegram, settings)

async def getting_TronAddress(message: types.Message, db, user_info, settings, telegram, api, state: FSMContext):
	async with state.proxy() as array:
		if message.text:
			if array['try'] >= 3:
				await message.reply(language("❌ Превышено максимальное кол-во попыток\n🔇 Вы замьюченый на 5 минут", user_info['language']))
				await state.finish()
				await asyncio.sleep(300)
				await message.reply(language("🔉 Время блокировки вышло" + str(error), user_info['language']))
				await command_start(message, db, user_info, telegram, settings)

			address = is_validate_USDTaddress(address = message.text)
			if address:
				msg = await message.bot.send_message(chat_id = user_info['chat_id'], text = language("📲 Загружаю кошелек...", user_info['language']))
				if await db.search_dublicate(address = address, chat_id = user_info['chat_id']):
					keyboard = types.InlineKeyboardMarkup()
					keyboard.add(types.InlineKeyboardButton(language("✖️ Отмена", user_info['language']), callback_data = cancel_callback.new(action = 'cancel')))
					await message.reply(language("⚠️ ЭТОТ КОШЕЛЕК УЖЕ ДОБАВЛЕН\n▪️ Оправьте другой адресс", user_info['language']), reply_markup = keyboard)
					await message.bot.delete_message(user_info['chat_id'], msg.message_id)
					array['try'] += 1
				else:
					balance = get_balance_USDT(address, api['tronscan'])
					if balance != False:
						try:
							array['address'] = address
							array['balance'] = round(balance, 2)
							amt_wallet = await db.get_count_TRON_Wallet()
							nameWallet = "TRON_WALLET_" + str(int(amt_wallet['count']) + 1) if amt_wallet else "TRON_WALLET_1"

							await db.add_NEWWallet(address = address, network = "ETH", balance = round(balance_usd, 2), balance_usdt_tokens = 0, balance_eth = 0, name = nameWallet, chat_id = user_info['chat_id'])
							keyboard = types.InlineKeyboardMarkup()
							keyboard.add(types.InlineKeyboardButton(language("Оставить это название", user_info['language']), callback_data = nameWallet_callback.new(action = "editName")))				
							text = '\n'.join([
								hbold(language("✅ Кошелек добавлен", user_info['language'])),
								"",
								language("▪ Он будет отображаться в списке ваших кошельков", user_info['language']),
								language("▪ Вы будете получать уведомления о новых транзакциях", user_info['language']),
								"",
								language("Адресс: ", user_info['language']) + hcode(address[:6] + '...' + address[-5:]),
								language("Баланс: ", user_info['language']) + hcode(str('{0:,}'.format(int(balance)).replace(',', '.')) + " $") if balance else language("Баланс: ") + hcode("0$"),
								language("Название: ", user_info['language']) + hcode(nameWallet),
								"",
								hitalic(language("⌨️ Придумайте название для кошелька", user_info['language'])),
								])

							await message.bot.edit_message_text(chat_id = user_info['chat_id'], message_id = msg.message_id, text = text, reply_markup = keyboard)
							await StatesAddWallet.get_name.set()
						except Exception as error:
							await message.reply(language("❌ Ошибка добавления кошелька !\n▪️ Содержимое: " + str(error), user_info['language']))
							await message.bot.delete_message(user_info['chat_id'], msg.message_id)
							await state.finish()
							await command_start(message, db, user_info, telegram, settings)
					elif balance == False:
						keyboard = types.InlineKeyboardMarkup()
						keyboard.add(types.InlineKeyboardButton(language("✖️ Отмена", user_info['language']), callback_data = cancel_callback.new(action = 'cancel')))
						await message.reply(language("⚠️ НЕ УДАЛОСЬ ПОЛУЧИТЬ БАЛАНС\n▪️ Попробуйте ещё раз", user_info['language']), reply_markup = keyboard)
						await message.bot.delete_message(user_info['chat_id'], msg.message_id)
						array['try'] += 1
			else:
				keyboard = types.InlineKeyboardMarkup()
				keyboard.add(types.InlineKeyboardButton(language("✖️ Отмена", user_info['language']), callback_data = cancel_callback.new(action = 'cancel')))
				await message.reply(language("⚠️ ЭТО НЕ ЯВЛЯЕТСЯ АДРЕСОМ USDT КОШЕЛЬКА\n▪️ Убедитесь в правильности адреса", user_info['language']), reply_markup = keyboard)
				array['try'] += 1
		else:
			await message.reply(language("⚠️ Поддерживается исключительно текст", user_info['language']))
			array['try'] += 1

async def getting_EthAddress(message: types.Message, db, user_info, settings, telegram, api, abi, state: FSMContext):
	async with state.proxy() as array:
		if message.text:
			if array['try'] >= 3:
				await message.reply(language("❌ Превышено максимальное кол-во попыток\n🔇 Вы замьюченый на 5 минут", user_info['language']))
				await state.finish()
				await asyncio.sleep(300)
				await message.reply(language("🔉 Время блокировки вышло" + str(error), user_info['language']))
				await command_start(message, db, user_info, telegram, settings)

			address = is_validate_ETHaddress(address = message.text, api = api)
			if address:
				msg = await message.bot.send_message(chat_id = user_info['chat_id'], text = language("📲 Загружаю кошелек...", user_info['language']))
				if await db.search_dublicate(address = address, chat_id = user_info['chat_id']):
					keyboard = types.InlineKeyboardMarkup()
					keyboard.add(types.InlineKeyboardButton(language("✖️ Отмена", user_info['language']), callback_data = cancel_callback.new(action = 'cancel')))
					await message.reply(language("⚠️ ЭТОТ КОШЕЛЕК УЖЕ ДОБАВЛЕН\n▪️ Оправьте другой адресс", user_info['language']), reply_markup = keyboard)
					await message.bot.delete_message(user_info['chat_id'], msg.message_id)
					array['try'] += 1
				else:
					balance_usd, balance_eth = get_balance_ETH(address, api['infura'])
					balance_usdt_tokens = get_balance_usdt_token(address, api['infura'], abi)
					if balance_usd != False:
						try:
							array['address'], array['balance_usd'], array['balance_eth'], array['balance_usdt_tokens'] = address, balance_usd, balance_eth, balance_usdt_tokens
							amt_wallet = await db.get_count_ETH_Wallet()
							nameWallet = "ETH_WALLET_" + str(int(amt_wallet['count']) + 1) if amt_wallet else "ETH_WALLET_1"

							await db.add_NEWWallet(address = address, network = "ETH", balance = round(balance_usd, 2), balance_usdt_tokens = balance_usdt_tokens, balance_eth = balance_eth, name = nameWallet, chat_id = user_info['chat_id'])
							keyboard = types.InlineKeyboardMarkup()
							keyboard.add(types.InlineKeyboardButton(language("Оставить это название", user_info['language']), callback_data = nameWallet_callback.new(action = "editName")))				
							text = '\n'.join([
								hbold(language("✅ Кошелек добавлен", user_info['language'])),
								"",
								language("▪ Он будет отображаться в списке ваших кошельков", user_info['language']),
								language("▪ Вы будете получать уведомления о новых транзакциях", user_info['language']),
								"",
								language("Адресс: ", user_info['language']) + hcode(address[:6] + '...' + address[-5:]),
								language("💵 Баланс ETH: ≈ ", user_info['language']) + str('{0:,}'.format(int(balance_usd)).replace(',', ',')) + " $" + hitalic(f" ({round(balance_eth, 2)} ETH)") if balance_usd else language("💵 Баланс ETH: ") + hcode("0$"),
								language("💲 Баланс USDT: ", user_info['language']) + str('{0:,}'.format(int(balance_usdt_tokens)).replace(',', ',')) + " USDT" if balance_usdt_tokens > 0 else language("💲 Баланс USDT: ", user_info['language']) + hcode("0 USDT"),
								language("Название: ", user_info['language']) + hcode(nameWallet),
								"",
								hitalic(language("⌨️ Придумайте название для кошелька"), user_info['language']),
								])

							await message.bot.edit_message_text(chat_id = user_info['chat_id'], message_id = msg.message_id, text = text, reply_markup = keyboard)
							await StatesAddWallet.get_name.set()
						except Exception as error:
							await message.reply(language("❌ Ошибка добавления кошелька !\n▪️ Содержимое: " + str(error), user_info['language']))
							await message.bot.delete_message(user_info['chat_id'], msg.message_id)
							await state.finish()
							await command_start(message, db, user_info, telegram, settings)
					elif balance_usd == False:
						keyboard = types.InlineKeyboardMarkup()
						keyboard.add(types.InlineKeyboardButton(language("✖️ Отмена", user_info['language']), callback_data = cancel_callback.new(action = 'cancel')))
						await message.reply(language("⚠️ НЕ УДАЛОСЬ ПОЛУЧИТЬ БАЛАНС\n▪️ Попробуйте ещё раз", user_info['language']), reply_markup = keyboard)
						await message.bot.delete_message(user_info['chat_id'], msg.message_id)
						array['try'] += 1
			else:
				keyboard = types.InlineKeyboardMarkup()
				keyboard.add(types.InlineKeyboardButton(language("✖️ Отмена", user_info['language']), callback_data = cancel_callback.new(action = 'cancel')))
				await message.reply(language("⚠️ ЭТО НЕ ЯВЛЯЕТСЯ АДРЕСОМ ETH КОШЕЛЬКА\n▪️ Убедитесь в правильности адреса", user_info['language']), reply_markup = keyboard)
				array['try'] += 1
		else:
			await message.reply(language("⚠️ Поддерживается исключительно текст", user_info['language']), reply_markup = keyboard)
			array['try'] += 1

async def keep_nameWallet(call: types.CallbackQuery, callback_data: dict, db, user_info, settings, telegram, state: FSMContext):
	await call.bot.delete_message(user_info['chat_id'], call.message.message_id)
	await state.finish()
	await command_start(call, db, user_info, telegram, settings)

async def name_fromWallet(message: types.Message, db, user_info, settings, telegram, state: FSMContext):
	if message.text:
		if len(message.text) > 35:
			await message.reply(language("⚠️ Слишком большая длинна", user_info['language']), reply_markup = keyboard)
		else:		
			async with state.proxy() as array:
				await db.set_name_wallet(address = array['address'], chat_id = user_info['chat_id'], name = message.text)
				text = '\n'.join([
					hbold(language("✅ Кошелек добавлен", user_info['language'])),
					"",
					language("▪ Он будет отображаться в списке ваших кошельков", user_info['language']),
					language("▪ Вы будете получать уведомления о новых транзакциях", user_info['language']),
					"",
					language("Адресс: ") + hcode(array['address'][:4] + '...' + array['address'][-5:]),
					language("💵 Баланс ETH: ≈ ", user_info['language']) + str('{0:,}'.format(int(array['balance_usd'])).replace(',', ',')) + " $" + hitalic(f" ({round(array['balance_eth'], 2)} ETH)") if array['balance_usd'] else language("💵 Баланс ETH: ") + hcode("0$"),
					language("💲 Баланс USDT: ", user_info['language']) + str('{0:,}'.format(int(array['balance_usdt_tokens'])).replace(',', ',')) + " USDT" if array['balance_usdt_tokens'] > 0 else language("💲 Баланс USDT: ", user_info['language']) + hcode("0 USDT"),
					language("Название: ") + hcode(message.text),
					"",
					])
				await message.bot.delete_message(user_info['chat_id'], message.message_id - 1)
				await message.bot.send_message(chat_id = user_info['chat_id'], text = text)
				await state.finish()
				await wallets(message, db, user_info, telegram, settings)
	else:
		await message.reply(language("⚠️ Поддерживается исключительно текст", user_info['language']))

async def settings_page_call(call: types.CallbackQuery, callback_data: dict, db, user_info, settings, telegram):
	await call.bot.delete_message(user_info['chat_id'], call.message.message_id)
	await page_settings(call, db, user_info, telegram, settings)

async def page_settings(message: types.Message, db, user_info, telegram, settings):
	keyboard = types.InlineKeyboardMarkup()
	if user_info['notification'] == 1:
		keyboard.add(types.InlineKeyboardButton(language("🔔 Звук уведомления", user_info['language']), callback_data = notification_callback.new(action = 'OFF')))
	elif user_info['notification'] == 0:
		keyboard.add(types.InlineKeyboardButton(language("🔕 Звук уведомления", user_info['language']), callback_data = notification_callback.new(action = 'ON')))
	keyboard.add(types.InlineKeyboardButton(language("🌎 Язык бота", user_info['language']), callback_data = settings_callback.new(action = 'language')))
	await message.bot.send_message(chat_id = user_info['chat_id'], text = language("⚙️ Настройки", user_info['language']), reply_markup = keyboard)

async def notification_settings(call: types.CallbackQuery, callback_data: dict, db, user_info, settings, telegram):
	if callback_data['action'] == "OFF":
		keyboard = types.InlineKeyboardMarkup()
		keyboard.add(types.InlineKeyboardButton(language("🔕 Звук уведомления", user_info['language']), callback_data = notification_callback.new(action = 'ON')))
		keyboard.add(types.InlineKeyboardButton(language("🌎 Язык бота", user_info['language']), callback_data = settings_callback.new(action = 'language')))
		await call.bot.edit_message_reply_markup(chat_id = user_info['chat_id'], message_id = call.message.message_id, reply_markup = keyboard)
		await db.change_notification(chat_id = user_info['chat_id'], value = 0)
	elif callback_data['action'] == "ON":
		keyboard = types.InlineKeyboardMarkup()
		keyboard.add(types.InlineKeyboardButton(language("🔔 Звук уведомления", user_info['language']), callback_data = notification_callback.new(action = 'OFF')))
		keyboard.add(types.InlineKeyboardButton(language("🌎 Язык бота", user_info['language']), callback_data = settings_callback.new(action = 'language')))
		await db.change_notification(chat_id = user_info['chat_id'], value = 1)
		await call.bot.edit_message_reply_markup(chat_id = user_info['chat_id'], message_id = call.message.message_id, reply_markup = keyboard)

async def setting_value(call: types.CallbackQuery, callback_data: dict, db, user_info, settings, telegram):
	if callback_data['action'] == "language":
		keyboard = types.InlineKeyboardMarkup()
		keyboard.add(types.InlineKeyboardButton(language("🇷🇺 Русский", user_info['language']), callback_data = language_callback.new(lang = 'ru')))
		keyboard.add(types.InlineKeyboardButton(language("🇺🇸 Английский", user_info['language']), callback_data = language_callback.new(lang = 'en')))
		keyboard.add(types.InlineKeyboardButton(language("↩️ Назад", user_info['language']), callback_data = settings_callback.new(action = 'back')))	
		await call.bot.edit_message_reply_markup(chat_id = user_info['chat_id'], message_id = call.message.message_id, reply_markup = keyboard)
	elif callback_data['action'] == "back":
		await page_settings(call, db, user_info, telegram, settings)

async def lang_selection(call: types.CallbackQuery, callback_data: dict, db, user_info, settings, telegram):
	await db.set_language(chat_id = user_info['chat_id'], lang = callback_data['lang'])
	user_info = await db.get_info_user(chat_id = user_info['chat_id'])
	await call.bot.delete_message(user_info['chat_id'], call.message.message_id)
	await page_settings(call, db, user_info, telegram, settings)


def register_user(dp: Dispatcher):
	dp.register_message_handler(command_start, CommandStart(), IsPrivate(), state = "*")
	dp.register_message_handler(wallets, Command('wallets'), IsPrivate())
	dp.register_callback_query_handler(wallets_call, wallet_callback.filter())
	dp.register_callback_query_handler(callback_pagination, pagination_callback.filter())
	dp.register_callback_query_handler(show_info_from_wallet, walletInfo_callback.filter(), state = "*")
	dp.register_callback_query_handler(custom_transaction_display, switch_trans_callback.filter())
	dp.register_callback_query_handler(custom_network_transaction_filter, transfer_network_callback.filter())
	dp.register_callback_query_handler(page_filter_transaction, filter_trans_callback.filter())
	dp.register_callback_query_handler(custom_transaction_filter, amount_set_callback.filter())
	dp.register_callback_query_handler(edit_name_wallet, editWallet_callback.filter())
	dp.register_message_handler(get_new_name_wallet, IsPrivate(), state = StatesEditName.get_name, content_types = types.ContentTypes.ANY)
	dp.register_callback_query_handler(page_settings_wallet, settingWallet_callback.filter())
	dp.register_callback_query_handler(page_history_transaction, history_trans_callback.filter())
	dp.register_callback_query_handler(callback_transaction_pagination, pagination_history_callback.filter())
	dp.register_callback_query_handler(page_add_wallet, addWallet_callback.filter())
	dp.register_callback_query_handler(choosing_walletNetwork, network_callback.filter())
	dp.register_message_handler(getting_TronAddress, IsPrivate(), state = StatesAddWallet.get_TronAddress, content_types = types.ContentTypes.ANY)
	dp.register_message_handler(name_fromWallet, IsPrivate(), state = StatesAddWallet.get_name, content_types = types.ContentTypes.ANY)
	dp.register_callback_query_handler(keep_nameWallet, nameWallet_callback.filter(), state = "*")
	dp.register_callback_query_handler(cancel_addWallet, cancel_callback.filter(), state = "*")
	dp.register_message_handler(getting_EthAddress, IsPrivate(), state = StatesAddWallet.get_ETHAddress, content_types = types.ContentTypes.ANY)
	dp.register_callback_query_handler(settings_page_call, settingsPage_callback.filter())
	dp.register_message_handler(page_settings, Command('settings'), IsPrivate())
	dp.register_callback_query_handler(setting_value, settings_callback.filter())
	dp.register_callback_query_handler(notification_settings, notification_callback.filter())
	dp.register_callback_query_handler(lang_selection, language_callback.filter())


