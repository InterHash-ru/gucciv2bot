from dataclasses import dataclass

class Broadcast:
	def __init__(self):
		self.declare_variables()

	def declare_variables(self):
		# available, launched, stopped, waiting
		self.status: str = "available"
		self.timer: object = None
		self.message: object = None
		self.keyboard: object = None
		self.preview: bool = None
		self.stats_left: int = 0
		self.stats_success: int = 0
		self.stats_fail: int = 0
		self.channel_message: object = None