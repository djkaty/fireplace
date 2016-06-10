import random
from hearthstone.enums import CardClass
from fireplace.ai.player import PassTurnAI
from fireplace.card import *
from fireplace.logging import get_logger


class Test1AI(PassTurnAI):
	def mulligan(self):
		if self.choice is not None:
			self.log("My hand: %r" % self.hand)
			self.log("Keeping all cards that cost 2 or less")
			self.choice.choose(*[c for c in self.choice.cards if c.cost > 2])
			self.log("My new hand: %r" % self.hand)

	def turn(self):
		# You would probably rework this for things like Tomb Pillager
		# to count the number of coins/extra mana available
		have_coin = self.hand.filter(id="GAME_005")
		if have_coin:
			self.log("I have the coin")
		for e in self.hand:
			should_play = e.is_playable() and e.id != "GAME_005"
			if not should_play:
				should_play = have_coin and e.is_playable(with_extra=1) and not e is self.hero.power and e.id != "GAME_005"

			if should_play:
				chooser = None if not e.must_choose_one else random.choice(e.choose_cards)

				if not e.is_playable():
					self.hand.filter(id="GAME_005")[0].play()
					have_coin = False
				self.log("Playing %r" % e)
				if e.has_target():
					# Let's naively assume that paladin and priest spells buff minions
					# and those of all other classes damage them. Just an example :-)
					buff_card = self.hero.card_class in [CardClass.PALADIN, CardClass.PRIEST]

					# But only for cards of our class... probably :-)
					if isinstance(e, Minion):
						buff_card = False

					target_hero = self.hero if buff_card else self.opponent.hero

					if target_hero in e.targets:
						e.play(target = target_hero, choose = chooser)
					else:
						target_minions = self.field if buff_card else self.opponent.field
						target = [m for m in target_minions if m in e.targets]
						# Don't buff opponent minions if our side of the board is empty
						# and vice versa
						if len(target):
							e.play(target = random.choice(target), choose = chooser)
				else:
					e.play(choose = chooser)

				# Make sure we do Tracking and Discover
				if self.choice:
					choice = random.choice(self.choice.cards)
					print("Choosing card %r" % (choice))
					self.choice.choose(choice)

		for e in self.characters:
			if e.can_attack():
				self.log("Attacking with %r" % e)
				if self.opponent.hero in e.targets:
					e.attack(self.opponent.hero)
				else:
					# I must attack that minion with taunt!
					e.attack(target = random.choice(e.targets))

		if self.hero.power.is_usable():
			self.log("Using hero power")
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

		self.log("Passing the turn")
