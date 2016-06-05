import asyncio
import logging
from hearthstone.enums import Step
from fireplace.exceptions import GameOver
from fireplace.ai.player import PlayerAI

class GameController:
	def __init__(self, game):
		self.log = logging.getLogger("GameController")
		self.log.setLevel(logging.DEBUG)
		self.game = game
		self.game.manager.register(self)

	# manager interface
	def action_start(self, type, source, index, target):
		pass

	def action_end(self, type, source):
		pass

	def new_entity(self, entity):
		pass

	def start_game(self):
		self.log.info("Game has started")
		# note: choice will be None here but won't be when mulligan() starts
		if isinstance(self.game.player1, PlayerAI):
			self.event_loop.call_soon(self.game.player1.mulligan)
		if isinstance(self.game.player2, PlayerAI):
			self.event_loop.call_soon(self.game.player2.mulligan)

	def game_step(self, step, next_step):
		self.log.debug("Game.STEP changes to %s" % step)
		if step == Step.MAIN_ACTION:
			self.log.info("Turn %s starting for player %s" % (self.game.turn, self.game.current_player.entity_id - 1))
			self.event_loop.call_soon(self.do_turn)

	# internal processing
	def do_turn(self):
		self.log.debug("Starting turn callback")
		if isinstance(self.game.current_player, PlayerAI):
			try:
				self.game.current_player.turn()
				# note: does not return until the next turn has started
				self.game.end_turn()
			except GameOver:
				self.event_loop.stop()
				self.log.info("Game ended normally")
		self.log.debug("Ending turn callback")

	# public methods
	def run(self):
		# note: an event loop for the thread must exist before calling run()
		# this is guaranteed for single-threaded programs
		self.event_loop = asyncio.get_event_loop()
		self.game.start()
		self.event_loop.run_forever()