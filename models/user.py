import asyncio
import aiomysql

class User:
	# TABLE 'users' INSERT, SELECT
	async def add_new_user(self, chat_id, username, fullname, date_start):
		sql = "INSERT INTO users (chat_id, username, fullname, date_start) VALUES (%s, %s, %s, %s)"
		return await self.execute(sql, (chat_id, username, fullname, date_start), execute = True)

	async def get_info_user(self, **kwargs):
		sql, parameters = self.format_args("SELECT * FROM users WHERE ", kwargs)
		return await self.execute(sql, parameters, fetchone = True)

	async def update_info_user(self, chat_id, username, fullname, date_last_action):
		sql = "UPDATE users SET username = %s, fullname = %s, date_last_action = %s WHERE chat_id = %s"
		return await self.execute(sql, (username, fullname, date_last_action, chat_id), execute = True)

	async def update_kicked_user(self, chat_id, status):
		sql = "UPDATE users SET kicked = %s WHERE chat_id = %s"
		return await self.execute(sql, (status, chat_id), execute = True)

	async def get_chat_id_users(self, active = False):
		sql = "SELECT chat_id FROM users" + (" WHERE kicked = 0" if active else "")# + " ORDER BY id"
		return await self.execute(sql, fetch = True)

	async def get_is_admin_users(self):
		sql = "SELECT * FROM users WHERE is_admin > 0"
		return await self.execute(sql, fetch = True)

	async def set_language(self, chat_id, lang):
		sql = "UPDATE users SET language = %s WHERE chat_id = %s"
		return await self.execute(sql, (lang, chat_id), execute = True)

	async def change_notification(self, chat_id, value):
		sql = "UPDATE users SET notification = %s WHERE chat_id = %s"
		return await self.execute(sql, (value, chat_id), execute = True)


	# TABLE 'wallets' INSERT, SELECT, DELETE

	async def get_all_TRON_wallets(self):
		sql = "SELECT * FROM wallets WHERE network = 'TRON'"
		return await self.execute(sql, fetch = True)

	async def get_all_ETH_wallets(self):
		sql = "SELECT * FROM wallets WHERE network = 'ETH'"
		return await self.execute(sql, fetch = True)

	async def get_users_wallet(self, chat_id):
		sql = "SELECT * FROM wallets WHERE chat_id = %s"
		return await self.execute(sql, (chat_id), fetch = True)

	async def get_info_wallet(self, id):
		sql = "SELECT * FROM wallets WHERE id = %s"
		return await self.execute(sql, (id), fetchone = True)

	async def add_NEWWallet(self, address, network, balance, name, chat_id):
		sql = "INSERT INTO wallets (address, network, balance, name, chat_id) VALUES (%s, %s, %s, %s, %s)"
		return await self.execute(sql, (address, network, balance, name, chat_id), execute = True)

	async def add_ethWallet(self, address, network, chat_id):
		sql = "INSERT INTO wallets (address, network, chat_id) VALUES (%s, %s, %s)"
		return await self.execute(sql, (address, network, chat_id), execute = True)

	async def search_dublicate(self, address, chat_id):
		sql = "SELECT * FROM wallets WHERE address = %s AND chat_id = %s"
		return await self.execute(sql, (address, chat_id), fetchone = True)

	async def set_name_wallet(self, address, chat_id, name):
		sql = "UPDATE wallets SET name = %s WHERE address = %s AND chat_id = %s"
		return await self.execute(sql, (name, address, chat_id), execute = True)

	async def get_total_balance(self, chat_id):
		sql = "SELECT SUM(balance) as total FROM wallets WHERE chat_id = %s"
		return await self.execute(sql, (chat_id), fetchrow = True)

	async def update_balance(self, id, balance):
		sql = "UPDATE wallets SET balance = %s WHERE id = %s"
		return await self.execute(sql, (balance, id), execute = True)

	async def update_balance_eth(self, id, balance, balance_eth):
		sql = "UPDATE wallets SET balance = %s, balance_eth = %s WHERE id = %s"
		return await self.execute(sql, (balance, balance_eth, id), execute = True)

	async def input_transaction_display(self, id, value):
		sql = "UPDATE wallets SET input_transactions = %s WHERE id = %s"
		return await self.execute(sql, (value, id), execute = True)

	async def update_transaction_filter(self, id, value):
		sql = "UPDATE wallets SET amount_filter = %s WHERE id = %s"
		return await self.execute(sql, (value, id), execute = True)

	async def output_transaction_display(self, id, value):
		sql = "UPDATE wallets SET outgoing_transactions = %s WHERE id = %s"
		return await self.execute(sql, (value, id), execute = True)

	async def delete_wallet(self, id):
		sql = "DELETE FROM wallets WHERE id = %s"
		return await self.execute(sql, (id), execute = True)

	async def add_history_transaction(self, _from, _to, amount, _hash):
		sql = "INSERT INTO history_transaction (_from, _to, amount, hash_trans) VALUES (%s, %s, %s, %s)"
		return await self.execute(sql, (_from, _to, amount, _hash), execute = True)

	async def get_history_transaction(self, address):
		sql = "SELECT * FROM history_transaction WHERE _from = %s OR _to = %s"
		return await self.execute(sql, (address, address), fetch = True)

	async def search_history_by_param(self, _hash):
		sql = "SELECT * FROM history_transaction WHERE hash_trans = %s"
		return await self.execute(sql, (_hash), fetch = True)


	# ADMIN 'statistics'
	async def get_stats_users(self):
		sql = "SELECT COUNT(*) as all_users FROM users"
		return await self.execute(sql, fetchrow = True)

	async def get_count_ETH_Wallet(self):
		sql = "SELECT COUNT(*) as count FROM wallets WHERE network = 'ETH'"
		return await self.execute(sql, fetchrow = True)

	async def get_count_TRON_Wallet(self):
		sql = "SELECT COUNT(*) as count FROM wallets WHERE network = 'TRON'"
		return await self.execute(sql, fetchrow = True)

	async def get_stats_count(self, table, separator = "=", **kwargs):
		sql = "SELECT COUNT(*) as count FROM {}{}".format(table, (" WHERE " if len(kwargs) else ""))
		sql += " AND ".join([f"{key} {separator} {value}" for key, value in kwargs.items()])
		return await self.execute(sql, fetchrow = True)