import logging
from fireplace.ai.player import PlayerAI
from hearthstone.enums import CardClass

"""
An example AI which uses its hero power whenever possible
"""

class HeroPowerAI(PlayerAI):
	def mulligan(self):
		if self.choice is not None:
			self.log("Keeping all cards")
			self.choice.choose()

	def turn(self):
		while self.hero.power.is_usable():
			self.log("Playing hero power")
			if self.hero.power.has_target():
				if self.hero.power.card_class == CardClass.MAGE:
					# mage pings opponent's face
					self.hero.power.use(self.opponent.hero)
				elif self.hero.power.card_class == CardClass.PRIEST:
					# priest heals own face
					self.hero.power.use(self.hero)
			else:
				# other other 7 heroes have no hero power target
				self.hero.power.use()

		self.log("Can't play hero power anymore this turn")
		self.log("Passing the turn")
