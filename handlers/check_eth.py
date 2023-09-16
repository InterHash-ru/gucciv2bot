import time

import datetime
from datetime import datetime

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
# init()
# os.system("cls")

class CheckTransactions():
	def __init__(self, bot, dp, db, API_KEY, abi):
		self.client = Web3(Web3.HTTPProvider("https://eth.public-rpc.com"))
		self.contract = self.client.eth.contract(address = Web3.to_checksum_address("0xdac17f958d2ee523a2206206994597c13d831ec7"), abi = abi)
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
				return float(result["ethereum"]["usd"])

	def get_balance_ETH(self, address):
		try:
			balance = self.client.eth.get_balance(address)
			amount_eth = int(balance) / 10 ** 18
			eth_to_usd = self.get_eth_to_usd_rate()
			balance_usd = amount_eth * eth_to_usd
			return balance_usd, amount_eth
		except:
			return False

	def convert_eth_to_usd(self, eth_amount):
		eth_to_usd = self.get_eth_to_usd_rate()
		usd_amount = float(eth_amount) * float(eth_to_usd)
		return round(usd_amount, 2)

	def checking_transaction_status(self, tx_hash): # ETH transaction
		transaction = self.client.eth.get_transaction_receipt(tx_hash)
		if transaction['status'] == 1:
			return True
		else:
			return False

	async def TrackingTransfers(self):
		await self.db.create_pool()
		while True:
			all_wallets = await self.db.get_all_ETH_wallets()
			last_block = self.client.eth.get_block_number()
			if self.block_number < last_block:
				try:
					txs = self.client.eth.get_block(int(last_block), True)
					# print("[ETH] BLOCK" + Fore.GREEN + " №" + str(last_block) + Style.RESET_ALL + " (" + str(len(txs['transactions'])) + " transactions)")
				except:
					pass
				if txs:
					for transaction in txs['transactions']:
						if transaction['to'] == '0xdAC17F958D2ee523a2206206994597C13D831ec7':	# TRANSACTION USDT TOKEN IN ERC-20 NETWORK
							result = self.contract.decode_function_input(transaction['input'])
							address_from = transaction['from']
							if result[0].fn_name == "transfer":
								address_to = result[1]['_to']
								for wallet in all_wallets:
									if wallet['address'] == address_from and wallet['outgoing_transactions'] == 1 and wallet['transfer_usdt'] == 1:
										trans_amount = int(result[1]['_value']) / (10 ** 6)
										if wallet['amount_filter'] == 0 or float(wallet['amount_filter']) <= float(trans_amount):
											if self.checking_transaction_status(transaction['hash']) == True:	
												user_info = await self.db.get_info_user(chat_id = wallet['chat_id'])
												balance_usdt_tokens = self.contract.functions.balanceOf(wallet['address']).call()
												balance_usdt_tokens = int(balance_usdt_tokens / (10 ** 6))			# Total USDT token holders
												balance_eth = self.client.eth.get_balance(wallet['address'])			
												balance_eth = self.client.from_wei(balance_eth, 'ether')			# ETH Coin balance and its dollar equivalent
												balance_usd = float(balance_eth) * self.get_eth_to_usd_rate()

												await self.db.update_balance_usdt_token(id = wallet['id'], balance_usdtTokens = balance_usdt_tokens, balance = balance_usd)
												record_history = await self.db.search_history_by_param(_hash = transaction['hash'].hex())
												if record_history:
													pass
												else:
													await self.db.add_history_transaction(_from = address_from, _to = address_to, amount = trans_amount, _hash = transaction['hash'].hex())

												if user_info and user_info['kicked'] == 0:
													text = '\n'.join([
														hbold(f"➖ {str(trans_amount)}" + " USDT ") + hitalic("(ERC-20)") + hitalic("🔹 "),
														"",
														language("◦ от 	", user_info['language']) + hcode(address_from[:6] + '...' + address_from[-5:]) + "  " + hitalic("(" + wallet['name'] + ")"),
														language("• на 	", user_info['language']) + hcode(str(address_to[:6]) + '...' + str(address_to[-5:])),
														"",
														language("💵 Баланс ETH: ≈ ", user_info['language']) + str('{0:,}'.format(int(balance_usd)).replace(',', ',')) + " $" + hitalic(f" ({round(balance_eth, 2)} ETH)") if balance_usd else language("💵 Баланс ETH: ") + hcode("0$"),
														language("💲 Баланс USDT: ", user_info['language']) + str('{0:,}'.format(int(balance_usdt_tokens)).replace(',', ',')) + " USDT" if balance_usdt_tokens else language("💲 Баланс USDT: ", user_info['language']) + hcode("0 USDT"),
														"",
														hlink("ℹ️ Transaction Details", "https://etherscan.io/tx/" + str(transaction['hash'].hex())),
														])
													img = open('data/img/out_usdt_token.png', 'rb')
													if user_info['notification'] == 1:
														await self.bot.send_photo(chat_id = user_info['chat_id'], photo = img, caption = text, disable_notification = False)
														img.close()
													elif user_info['notification'] == 0:
														await self.bot.send_photo(chat_id = user_info['chat_id'], photo = img, caption = text, disable_notification = True)
														img.close()
													# print(Fore.GREEN + "ADDRESS FROM - " + Style.RESET_ALL + Fore.CYAN + str(wallet['address'] + Style.RESET_ALL + " ("+wallet['name']+")") + Fore.GREEN + " | ADDRESS TO - " + Style.RESET_ALL + Fore.MAGENTA + str(address_to) + Style.RESET_ALL + Fore.GREEN +" | SUM: " + str(trans_amount) + " USDT | Balance USDT token: ≈ " + str('{0:,}'.format(int(balance_usdt_tokens)).replace(',', '.')) + " USDT" + Style.RESET_ALL)
												self.block_number = last_block
									elif wallet['address'] == address_to and wallet['input_transactions'] == 1 and wallet['transfer_usdt'] == 1:
										trans_amount = int(result[1]['_value']) / (10 ** 6)
										if wallet['amount_filter'] == 0 or float(wallet['amount_filter']) <= float(trans_amount):
											if self.checking_transaction_status(transaction['hash']) == True:
												user_info = await self.db.get_info_user(chat_id = wallet['chat_id'])
												balance_usdt_tokens = self.contract.functions.balanceOf(wallet['address']).call()
												balance_usdt_tokens = int(balance_usdt_tokens / (10 ** 6))			# Total USDT token holders
												balance_eth = self.client.eth.get_balance(wallet['address'])			
												balance_eth = self.client.from_wei(balance_eth, 'ether')			# ETH Coin balance and its dollar equivalent
												balance_usd = float(balance_eth) * self.get_eth_to_usd_rate()

												await self.db.update_balance_usdt_token(id = wallet['id'], balance_usdtTokens = balance_usdt_tokens, balance = balance_usd)
												record_history = await self.db.search_history_by_param(_hash = transaction['hash'].hex())
												if record_history:
													pass
												else:
													await self.db.add_history_transaction(_from = address_from, _to = address_to, amount = trans_amount, _hash = transaction['hash'].hex())
												
												if user_info and user_info['kicked'] == 0:
													text = '\n'.join([
														hbold(f"➕ {str(trans_amount)}" + " USDT ") + hitalic("(ERC-20)") + hitalic("🔹 "),
														"",
														language("◦ от 	", user_info['language']) + hcode(address_from[:6] + '...' + address_from[-5:]),
														language("• на 	", user_info['language']) + hcode(address_to[:6] + '...' + address_to[-5:]) + "  " + hitalic("(" + wallet['name'] + ")"),
														"",
														language("💵 Баланс ETH: ≈ ", user_info['language']) + str('{0:,}'.format(int(balance_usd)).replace(',', ',')) + " $" + hitalic(f" ({round(balance_eth, 2)} ETH)") if balance_usd else language("💵 Баланс ETH: ") + hcode("0$"),
														language("💲 Баланс USDT: ", user_info['language']) + str('{0:,}'.format(int(balance_usdt_tokens)).replace(',', ',')) + " USDT" if balance_usdt_tokens else language("💲 Баланс USDT: ", user_info['language']) + hcode("0 USDT"),
														"",
														hlink("ℹ️ Transaction Details", "https://etherscan.io/tx/" + str(transaction['hash'].hex())),
														])
													img = open('data/img/in_usdt_token.png', 'rb')
													if user_info['notification'] == 1:
														await self.bot.send_photo(chat_id = user_info['chat_id'], photo = img, caption = text, disable_notification = False)
														img.close()
													elif user_info['notification'] == 0:
														await self.bot.send_photo(chat_id = user_info['chat_id'], photo = img, caption = text, disable_notification = True)
														img.close()
													# print(Fore.RED + "ADDRESS TO - " + Style.RESET_ALL + Fore.CYAN + str(address_to + Style.RESET_ALL + Fore.RED + " | ADDRESS FROM - " + Style.RESET_ALL + Fore.MAGENTA + str(wallet['address']) + Style.RESET_ALL + " ("+wallet['name']+")") + Fore.RED +" | SUM: " + str(trans_amount) + " USDT | Balance USDT token: ≈ " + str('{0:,}'.format(int(balance_usdt_tokens)).replace(',', '.')) + " USDT" + Style.RESET_ALL)
												self.block_number = last_block

						try:																	# TRANSACTION ETH TOKEN IN ERC-20 NETWORK
							address_from = transaction['from']
							address_to = transaction['to']
							tx_hash = transaction['hash'].hex()
							if transaction['input'][:10] == transaction['input'] and transaction['value'] > 0:
								for wallet in all_wallets:
									if wallet['transfer_eth'] == 1:
										if wallet['address'] == address_from and wallet['outgoing_transactions'] == 1:
											eth_amount = self.client.from_wei(transaction['value'], 'ether')
											usd_amount = self.convert_eth_to_usd(eth_amount)
											if wallet['amount_filter'] == 0 or float(wallet['amount_filter']) <= float(usd_amount):
												if balance_usd:
													user_info = await self.db.get_info_user(chat_id = wallet['chat_id'])
													balance_usdt_tokens = self.contract.functions.balanceOf(wallet['address']).call()
													balance_usdt_tokens = int(balance_usdt_tokens / (10 ** 6))			# Total USDT token holders
													balance_eth = self.client.eth.get_balance(wallet['address'])			
													balance_eth = self.client.from_wei(balance_eth, 'ether')			# ETH Coin balance and its dollar equivalent
													balance_usd = float(balance_eth) * self.get_eth_to_usd_rate()	
													
													await self.db.update_balance_eth(id = wallet['id'], balance = balance_usd, balance_eth = balance_eth)
													record_history = await self.db.search_history_by_param(_hash = tx_hash)
													if record_history:
														pass
													else:
														await self.db.add_history_transaction(_from = address_from, _to = address_to, amount = round(eth_amount, 2), _hash = tx_hash)

													if user_info and user_info['kicked'] == 0:
														text = '\n'.join([
															hbold(f"➖ {str(round(eth_amount, 2))}" + " ETH 🔹 ") + hitalic(f"≈ {usd_amount}$"),
															"",
															language("◦ от 	", user_info['language']) + hcode(address_from[:6] + '...' + address_from[-5:]) + "  " + hitalic("(" + wallet['name'] + ")"),
															language("• на 	", user_info['language']) + hcode(address_to[:6] + '...' + address_to[-5:]),
															"",
															language("💵 Баланс ETH: ≈ ", user_info['language']) + str('{0:,}'.format(int(balance_usd)).replace(',', ',')) + " $" + hitalic(f" ({round(balance_eth, 2)} ETH)") if balance_usd else language("💵 Баланс ETH: ") + hcode("0$"),
															language("💲 Баланс USDT: ", user_info['language']) + str('{0:,}'.format(int(balance_usdt_tokens)).replace(',', ',')) + " USDT" if balance_usdt_tokens else language("💲 Баланс USDT: ", user_info['language']) + hcode("0 USDT"),
															"",
															hlink(language("ℹ️ Transaction Details", user_info['language']), "https://etherscan.io/tx/" + tx_hash),
															])
														img = open('data/img/out_eth.png', 'rb')
														if user_info['notification'] == 1:
															await self.bot.send_photo(chat_id = user_info['chat_id'], photo = img, caption = text, disable_notification = False)
															img.close()
														elif user_info['notification'] == 0:
															await self.bot.send_photo(chat_id = user_info['chat_id'], photo = img, caption = text, disable_notification = True)
															img.close()
														# print(Fore.GREEN + "ADDRESS FROM - " + Style.RESET_ALL + Fore.CYAN + str(transaction['from'] + " ("+wallet['name']+")") + Style.RESET_ALL + Fore.GREEN + " | ADDRESS TO - " + Style.RESET_ALL + Fore.MAGENTA + transaction['to'] + Style.RESET_ALL + Fore.GREEN +" | SUM: " + str(eth_amount) + " ETH | Balance: ≈ " + str('{0:,}'.format(int(balance_usd)).replace(',', '.')) + "$" + Style.RESET_ALL)
													self.block_number = last_block
										elif wallet['address'] == address_to and wallet['input_transactions'] == 1:
											eth_amount = self.client.from_wei(transaction['value'], 'ether')
											usd_amount = self.convert_eth_to_usd(eth_amount)
											if wallet['amount_filter'] == 0 or float(wallet['amount_filter']) <= float(usd_amount):
												user_info = await self.db.get_info_user(chat_id = wallet['chat_id'])
												balance_usdt_tokens = self.contract.functions.balanceOf(wallet['address']).call()
												balance_usdt_tokens = int(balance_usdt_tokens / (10 ** 6))			# Total USDT token holders
												balance_eth = self.client.eth.get_balance(wallet['address'])			
												balance_eth = self.client.from_wei(balance_eth, 'ether')			# ETH Coin balance and its dollar equivalent
												balance_usd = float(balance_eth) * self.get_eth_to_usd_rate()	
												if user_info:
													await self.db.update_balance_eth(id = wallet['id'], balance = balance_usd, balance_eth = balance_eth)
													record_history = await self.db.search_history_by_param(_hash = tx_hash)
													if record_history:
														pass
													else:
														await self.db.add_history_transaction(_from = address_from, _to = address_to, amount = round(eth_amount, 2), _hash = tx_hash)

													if user_info and user_info['kicked'] == 0:
														text = '\n'.join([
															hbold(f"➕ {str(round(eth_amount, 2))}" + " ETH 🔹 ") + hitalic(f"≈ {usd_amount}$"),
															"",
															language("◦ от 	", user_info['language']) + hcode(address_from[:6] + '...' + address_from[-5:]),
															language("• на 	", user_info['language']) + hcode(address_to[:6] + '...' + address_to[-5:]) + "  " + hitalic("(" + wallet['name'] + ")"),
															"",
															language("💵 Баланс ETH: ≈ ", user_info['language']) + str('{0:,}'.format(int(balance_usd)).replace(',', ',')) + " $" + hitalic(f" ({round(balance_eth, 2)} ETH)") if balance_usd else language("💵 Баланс ETH: ") + hcode("0$"),
															language("💲 Баланс USDT: ", user_info['language']) + str('{0:,}'.format(int(balance_usdt_tokens)).replace(',', ',')) + " USDT" if balance_usdt_tokens else language("💲 Баланс USDT: ", user_info['language']) + hcode("0 USDT"),
															"",
															hlink(language("ℹ️ Transaction Details", user_info['language']), "https://etherscan.io/tx/" + tx_hash),
															])
														img = open('data/img/in_eth.png', 'rb')
														if user_info['notification'] == 1:
															await self.bot.send_photo(chat_id = user_info['chat_id'], photo = img, caption = text, disable_notification = False)
															img.close()				
														elif user_info['notification'] == 0:
															await self.bot.send_photo(chat_id = user_info['chat_id'], photo = img, caption = text, disable_notification = True)
															img.close()		
														# print(Fore.RED + "ADDRESS TO - " + Style.RESET_ALL + Fore.CYAN + str(transaction['to'] + " ("+wallet['name']+")") + Style.RESET_ALL + Fore.RED + " | ADDRESS FROM - " + Style.RESET_ALL + Fore.MAGENTA + transaction['from'] + Style.RESET_ALL + Fore.RED +" | SUM: " + str(eth_amount) + " ETH | Balance: ≈ " + str('{0:,}'.format(int(balance_usd)).replace(',', '.')) + "$" + Style.RESET_ALL)
													self.block_number = last_block
										else:
											pass
						except web3.exceptions.BlockNotFound as e:
							pass
						except RuntimeError as e:
							pass
						except asyncio.CancelledError:
							pass
					self.block_number = last_block
					await asyncio.sleep(5)
				else:
					pass
