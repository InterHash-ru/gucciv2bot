import asyncio
import aiomysql

# FILES <
from models.user import User
# FILES >

class Database(User):
	def __init__(self, config):
		self.pool = None
		self.config = config

	async def create_pool(self):
		self.pool = await aiomysql.create_pool(
			host = self.config['host'],
			user = self.config['user'],
			password = self.config['password'],
			db = self.config['db'],
			port = self.config['port'],
			autocommit = True,
		)

	async def execute(self, command, *args, fetch: bool = False, fetchone: bool = False, fetchrow: bool = False, execute: bool = False):
		async with self.pool.acquire() as connection:
			async with connection.cursor(aiomysql.DictCursor) as cursor:
				await cursor.execute(command, *args)
				if fetch:
					result = await cursor.fetchall()
				elif fetchone or fetchrow:
					result = await cursor.fetchone()
				elif execute:
					result = cursor.lastrowid
				return (result)

	@staticmethod
	def format_args(sql, parameters: dict):
		sql += " AND ".join([f"{item} = %s" for num, item in enumerate(parameters.keys(), start = 1)])
		return(sql, tuple(parameters.values()))