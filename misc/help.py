from aiogram import types

def keyboard_gen(array, is_admin = False):
	keyboard = types.ReplyKeyboardMarkup(resize_keyboard = True)
	for el in array:
		keyboard.add(*[types.KeyboardButton(name) for name in el])
	if is_admin:
		keyboard.add(*[types.KeyboardButton(name) for name in ['⚙️ Управление']])
	return(keyboard)

def chunks_generators(lst, n):
	for i in range(0, len(lst), n):
		yield lst[i : i + n]

def format_number(string):
	return '{:,}'.format(string).replace(',', ' ')