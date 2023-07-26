from datetime import datetime, timedelta
from aiogram.dispatcher.middlewares import LifetimeControllerMiddleware

class UserUpdateMiddleware(LifetimeControllerMiddleware):
	skip_patterns = ["error", "update"]

	async def post_process(self, obj, data, *args):
		db = data.get('db')
		user = data.get('user')
		user_info = data.get('user_info')

		if db and user and user_info:
			now = datetime.now()
			difference = user_info['date_last_action'] + timedelta(minutes = 30)
			if now > difference:
				await db.update_info_user(user.id, user.username, user.full_name, now.strftime('%Y-%m-%d %H:%M:%S'))