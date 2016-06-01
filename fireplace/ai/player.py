import logging
from fireplace.player import Player

class PlayerAI(Player):
	def __init__(self, name, deck, hero_class):
		super().__init__(name, deck, hero_class)

		self.logger = logging.getLogger("P-%s" % name)

	# interface that AI players must implement
	def mulligan(self):
		if self.choice is not None:
			self.log("Keeping all cards")
			self.choice.choose()

	def turn(self):
		self.log("Passing the turn")
