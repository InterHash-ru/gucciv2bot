from aiogram import types

async def set_default_commands(dp):
	await dp.bot.set_my_commands([
		types.BotCommand("wallets", ("🗂 Кошельки")),
		types.BotCommand("settings", "🛠 Настройки бота"),
		types.BotCommand("start", "🔄 Перезапустить бота"),
	])