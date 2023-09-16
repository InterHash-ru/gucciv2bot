import asyncio
import os, sys, json, requests

import colorama
from colorama import init, Fore, Back, Style

from tronpy import Tron
from tronpy.abi import trx_abi
from eth_utils import decode_hex
from misc.translate import language
from tronpy.providers import HTTPProvider
from aiogram.utils.markdown import hbold, hcode, hitalic, hunderline, hstrikethrough, hlink
# init()
# os.system("cls")


class CheckTransactions():
	def __init__(self, bot, dp, db, API_KEY):
		# self.client = Tron(HTTPProvider("http://34.220.77.106:8090"))
		self.client = Tron(HTTPProvider("http://3.225.171.164:8090"))
		self.contract = self.getContract()
		self.bot = bot
		self.dp = dp
		self.db = db
		self.API_KEY = API_KEY
		self.block_number = 0

	def getContract(self):
		while True:
			try:
				contract = self.client.get_contract("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
				return (contract)
			except Exception as e:
				pass

	def convert_to_decimal(self, amount, decimal = 6):
		return int(amount * (10 ** decimal))

	def convert_from_decimal(self, amount, decimal = 6):
		return (amount / (10 ** decimal))		

	def get_usdt_balance(self, address):
		try:
			balance = self.contract.functions.balanceOf(address)
			return {'status': 'ok', 'balance': balance}
		except AddressNotFound as e:
			return {'status': 'ok', 'balance': 0}
		except Exception as e:
			return {'status': 'ko', 'errros': str(e)}

	async def TrackingTransfers(self):
		await self.db.create_pool()
		while True:
			all_wallets = await self.db.get_all_TRON_wallets()
			last_block = self.client.get_latest_block_number()
			# text = "DOUBLE !" if int(self.block_number) == int(last_block) else " "
			if int(self.block_number) < int(last_block):
				txs = self.client.get_block(last_block)
				# print("[USDT] BLOCK" + Fore.GREEN + " №" + str(last_block) + Style.RESET_ALL + " (" + str(len(txs['transactions'])) + " transactions) |	" + str(self.block_number) + '/' + str(last_block))
				if txs['transactions']:
					for transaction in txs['transactions']:
						value = transaction['raw_data']['contract'][0]['parameter']['value']
						_hash = transaction['txID']
						contract_address = value.get('contract_address')

						if contract_address and contract_address == "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t":
							data = trx_abi.decode_abi(['address', 'uint256'], bytes.fromhex(value['data'])[4:])
							address_from = value['owner_address']
							address_to = data[0]
							usdt_decimal = data[1]
							for wallet in all_wallets:
								if wallet['address'] == address_from and wallet['outgoing_transactions'] == 1 and transaction['ret'][0]['contractRet'] == "SUCCESS":
									transfer_amount = self.convert_from_decimal(usdt_decimal)
									if transfer_amount > 0:
										if wallet['amount_filter'] == 0 or float(wallet['amount_filter']) <= transfer_amount:
											balance_wallet = self.get_usdt_balance(wallet['address'])
											if balance_wallet['status'] == "ok":
												balance_wallet = self.convert_from_decimal(balance_wallet['balance'])
												
												user_info = await self.db.get_info_user(chat_id = wallet['chat_id'])
												await self.db.update_balance(id = wallet['id'], balance = balance_wallet)
											
												record_history = await self.db.search_history_by_param(_hash = _hash)
												if record_history:
													pass
												else:
													await self.db.add_history_transaction(_from = address_from, _to = address_to, amount = float(transfer_amount), _hash = _hash)
												if user_info and user_info['kicked'] == 0:
													text = '\n'.join([
														hbold(f"➖ {str(round(transfer_amount, 2))}" + " USDT 🔸"),
														"",
														language("◦ от 	", user_info['language']) + hcode(address_from[:6] + '...' + address_from[-5:]) + "  " + hitalic("(" + wallet['name'] + ")"),
														language("• на 	", user_info['language']) + hcode(address_to[:6] + '...' + address_to[-5:]),
														"",
														language("💵 Баланс: ≈ ", user_info['language']) + str('{0:,}'.format(int(balance_wallet)).replace(',', '.')) + " $",
														"",
														hlink("ℹ️ Transaction Details", "https://tronscan.org/#/transaction/" + _hash),
														])
													img = open('data/img/out_usdt.png', 'rb')
													if user_info['notification'] == 1:
														await self.bot.send_photo(chat_id = user_info['chat_id'], photo = img, caption = text, disable_notification = False)
														img.close()
													elif user_info['notification'] == 0:
														await self.bot.send_photo(chat_id = user_info['chat_id'], photo = img, caption = text, disable_notification = True)
														img.close()
											# print(Fore.GREEN + "      ADDRESS FROM - " + Style.RESET_ALL + Fore.CYAN + str(address_from) + Style.RESET_ALL + " '" + wallet['name'] + "'" + Fore.GREEN + " | ADDRESS TO - " + Style.RESET_ALL + Fore.CYAN + address_to + Style.RESET_ALL + Fore.GREEN +" | SUM: " + str(round(transfer_amount, 2)) + "$ | Balance: ≈ " + str('{0:,}'.format(int(balance_wallet)).replace(',', '.')) + "$" + Style.RESET_ALL)

								elif wallet['address'] == address_to and wallet['input_transactions'] == 1 and transaction['ret'][0]['contractRet'] == "SUCCESS":
									transfer_amount = self.convert_from_decimal(usdt_decimal)
									if transfer_amount > 0:
										if wallet['amount_filter'] == 0 or float(wallet['amount_filter']) <= transfer_amount:
											balance_wallet = self.get_usdt_balance(wallet['address'])
											if balance_wallet['status'] == "ok":
												balance_wallet = self.convert_from_decimal(balance_wallet['balance'])

												user_info = await self.db.get_info_user(chat_id = wallet['chat_id'])
												await self.db.update_balance(id = wallet['id'], balance = balance_wallet)
												
												record_history = await self.db.search_history_by_param(_hash = _hash)
												if record_history:
													pass
												else:
													await self.db.add_history_transaction(_from = address_from, _to = address_to, amount = float(transfer_amount), _hash = _hash)

												if user_info and user_info['kicked'] == 0:
													text = '\n'.join([
														hbold(f"➕ {str(round(transfer_amount, 2))}" + " USDT 🔸"),
														"",
														language("◦ от 	", user_info['language']) + hcode(address_from[:6] + '...' + address_from[-5:]),
														language("• на 	", user_info['language']) + hcode(address_to[:6] + '...' + address_to[-5:]) + "  " + hitalic("(" + wallet['name'] + ")"),
														"",
														language("💵 Баланс: ≈ ", user_info['language']) + str('{0:,}'.format(int(balance_wallet)).replace(',', '.')) + " $",
														"",
														hlink("ℹ️ Transaction Details", "https://tronscan.org/#/transaction/" + _hash),
														])
													img = open('data/img/in_usdt.png', 'rb')
													if user_info['notification'] == 1:
														await self.bot.send_photo(chat_id = user_info['chat_id'], photo = img, caption = text, disable_notification = False)
														img.close()
													elif user_info['notification'] == 0:
														await self.bot.send_photo(chat_id = user_info['chat_id'], photo = img, caption = text, disable_notification = True)
														img.close()
											# print(Fore.RED + "      ADDRESS TO - " + Style.RESET_ALL +  Fore.CYAN + str(address_to) + Style.RESET_ALL + " '" + wallet['name'] + "'" + Fore.RED + " | ADDRESS  FROM - " + Style.RESET_ALL + Fore.CYAN + address_from + Style.RESET_ALL + Fore.RED + " | SUM: " + str(round(transfer_amount, 2)) + "$ | Balance: ≈ " + str('{0:,}'.format(int(balance_wallet)).replace(',', '.')) + "$" + Style.RESET_ALL)
								else:
									pass
								self.block_number = last_block
					self.block_number = last_block
					await asyncio.sleep(2)
				else:
					pass
			else:
				self.block_number = last_block
				await asyncio.sleep(2)


