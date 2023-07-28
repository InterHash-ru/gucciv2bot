import asyncio
import os, sys, json, requests

import colorama
from colorama import init, Fore, Back, Style

from web3 import Web3
import web3.exceptions
from web3.contract import Contract

from decimal import Decimal

from tronpy import Tron
from tronpy.abi import trx_abi
from eth_utils import decode_hex
from misc.translate import language
from tronpy.providers import HTTPProvider
from aiogram.utils.markdown import hbold, hcode, hitalic, hunderline, hstrikethrough, hlink
init()
#os.system("cls")

class CheckTransactions():
	def __init__(self, bot, dp, db, API_KEY, abi):
		self.client = Web3(Web3.HTTPProvider("https://eth.public-rpc.com"))
		# self.contract = self.getContract()
		self.bot = bot
		self.dp = dp
		self.db = db
		self.API_KEY = API_KEY
		self.abi = abi
		self.block_number = 0

	def convert_to_decimal(self, amount, decimal = 6):
		return int(amount * (10 ** decimal))

	def convert_from_decimal(self, amount, decimal = 6):
		return (amount / (10 ** decimal))	

	def get_eth_to_usd_rate(self):
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


	def get_balance_ETH(self, address):
		try:
			balance = self.client.eth.get_balance(address)
			amount_eth = int(balance) / 10 ** 18
			eth_to_usd = self.get_eth_to_usd_rate()
			balance_usd = amount_eth * eth_to_usd
			return balance_usd, amount_eth
		except:
			return False

	async def TrackingTransfers(self):
		await self.db.create_pool()

		while True:
			all_wallets = await self.db.get_all_ETH_wallets()
			last_block = self.client.eth.get_block_number()
			if self.block_number < last_block:
				try:
					txs = self.client.eth.get_block(last_block, True)
#					print("[ETH] BLOCK №" + str(last_block))
				except Exception:
					pass

				for transaction in txs['transactions']:
					if transaction['input']:
						try:
							function_signature = transaction['input'][:10]
							transfer_signature = '0xa9059cbb'
							address_from = transaction['from']
							address_to = transaction['to']
							tx_hash = transaction['hash'].hex()
							if function_signature == transaction['input'] and transaction['value'] > 0:
								for wallet in all_wallets:
									if wallet['address'] == address_from and wallet['outgoing_transactions'] == 1:
										eth_amount = self.client.from_wei(transaction['value'], 'ether')
										balance_usd, balance_eth = self.get_balance_ETH(wallet['address'])
										if balance_usd:
											user_info = await self.db.get_info_user(chat_id = wallet['chat_id'])
											await self.db.update_balance_eth(id = wallet['id'], balance = balance_usd, balance_eth = balance_eth)
											record_history = await self.db.search_history_by_param(_hash = tx_hash)
											if record_history:
												pass
											else:
												await self.db.add_history_transaction(_from = address_from, _to = address_to, amount = round(eth_amount, 2), _hash = tx_hash)

											if user_info and user_info['kicked'] == 0:
												text = '\n'.join([
													hbold(f"➖ {str(round(eth_amount, 2))}") + " ETH",
													"",
													language("◦ от 	", user_info['language']) + hcode(address_from[:6] + '...' + address_from[-5:]) + "  " + hitalic("(" + wallet['name'] + ")"),
													language("• на 	", user_info['language']) + hcode(address_to[:6] + '...' + address_to[-5:]),
													"",
													language("💵 Баланс: ≈ ", user_info['language']) + str('{0:,}'.format(int(balance_usd)).replace(',', '.')) + " $" + hitalic(f" ({round(balance_eth, 2)} ETH)") if balance_usd else language("Баланс: ") + hcode("0$"),
													"",
													hlink(language("ℹ️ Подробнее", user_info['language']), "https://etherscan.io/tx/" + tx_hash),
													])
												if user_info['notification'] == 1:
													await self.bot.send_message(user_info['chat_id'], text = text, disable_web_page_preview = True, disable_notification = True)
												elif user_info['notification'] == 0:
													await self.bot.send_message(user_info['chat_id'], text = text, disable_web_page_preview = True, disable_notification = False)
												# print(Fore.GREEN + "ADDRESS FROM - " + Style.RESET_ALL + Fore.CYAN + str(transaction['from'] + " ("+wallet['name']+")") + Style.RESET_ALL + Fore.GREEN + " | ADDRESS TO - " + Style.RESET_ALL + Fore.MAGENTA + transaction['to'] + Style.RESET_ALL + Fore.GREEN +" | SUM: " + str(eth_amount) + " ETH | Balance: ≈ " + str('{0:,}'.format(int(balance_usd)).replace(',', '.')) + "$" + Style.RESET_ALL)
											self.block_number = last_block

									elif wallet['address'] == address_to and wallet['input_transactions'] == 1:
										eth_amount = self.client.from_wei(transaction['value'], 'ether')
										balance_usd, balance_eth = self.get_balance_ETH(wallet['address'])

										user_info = await self.db.get_info_user(chat_id = wallet['chat_id'])
										if user_info:
											await self.db.update_balance_eth(id = wallet['id'], balance = balance_usd, balance_eth = balance_eth)
											record_history = await self.db.search_history_by_param(_hash = tx_hash)
											if record_history:
												pass
											else:
												await self.db.add_history_transaction(_from = address_from, _to = address_to, amount = round(eth_amount, 2), _hash = tx_hash)

											if user_info and user_info['kicked'] == 0:
												text = '\n'.join([
													hbold(f"➕ {str(round(eth_amount, 2))}") + " ETH",
													"",
													language("◦ от 	", user_info['language']) + hcode(address_from[:6] + '...' + address_from[-5:]),
													language("• на 	", user_info['language']) + hcode(address_to[:6] + '...' + address_to[-5:]) + "  " + hitalic("(" + wallet['name'] + ")"),
													"",
													language("💵 Баланс: ≈ ", user_info['language']) + str('{0:,}'.format(int(balance_usd)).replace(',', '.')) + " $" + hitalic(f" ({round(balance_eth, 2)} ETH)") if balance_usd else language("Баланс: ") + hcode("0$"),
													"",
													hlink(language("ℹ️ Подробнее", user_info['language']), "https://etherscan.io/tx/" + tx_hash),
													])
												if user_info['notification'] == 1:
													await self.bot.send_message(user_info['chat_id'], text = text, disable_web_page_preview = True, disable_notification = True)				
												elif user_info['notification'] == 0:
													await self.bot.send_message(user_info['chat_id'], text = text, disable_web_page_preview = True, disable_notification = False)				
												# print(Fore.GREEN + "ADDRESS TO - " + Style.RESET_ALL + Fore.CYAN + str(transaction['to'] + " ("+wallet['name']+")") + Style.RESET_ALL + Fore.GREEN + " | ADDRESS FROM - " + Style.RESET_ALL + Fore.MAGENTA + transaction['from'] + Style.RESET_ALL + Fore.GREEN +" | SUM: " + str(eth_amount) + " ETH | Balance: ≈ " + str('{0:,}'.format(int(balance_usd)).replace(',', '.')) + "$" + Style.RESET_ALL)
											self.block_number = last_block

						except web3.exceptions.BlockNotFound as e:
							print(Fore.RED + str(e) + Style.RESET_ALL)
							pass
						except RuntimeError as e:
							print(Fore.RED + str(e) + Style.RESET_ALL)
							pass
						except asyncio.CancelledError:
							pass
				self.block_number = last_block
				await asyncio.sleep(7)
