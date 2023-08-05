from aiogram.dispatcher.filters.state import StatesGroup, State

class StatesAddWallet(StatesGroup):
	get_TronAddress = State()
	get_ETHAddress = State()
	get_name_eth = State()
	get_name_tron = State()

class StatesBroadcast(StatesGroup):
	action = State()
	message = State()
	editor = State()
	keyboard = State()
	timeout = State()

class StatesEditName(StatesGroup):
	get_name = State()