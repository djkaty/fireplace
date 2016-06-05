#!/usr/bin/env python
import asyncio
import logging
import threading
import time
from fireplace import cards
from fireplace.game import Game
from fireplace.utils import *
from fireplace.controller import GameController
from fireplace.ai.player import PlayerAI
from fireplace.player import Player
from fireplace.exceptions import GameOver

logging.basicConfig(level=logging.INFO)
logging.getLogger("fireplace").disabled = True
logger = logging.getLogger("demo")


"""
This demo emulates a human player vs an AI player
Note that asyncio, threading and time are unnecessary in real scenarios
The threading is just used to run the AI and allow a 'human' to do something too
The human's behaviour is simulated by code
"""

def create_game():
	p1_class = random_class()
	p2_class = random_class()
	deck1 = random_draft(p1_class)
	deck2 = random_draft(p2_class)
	player1 = Player("Player1", deck1, p1_class.default_hero)
	player2 = PlayerAI("Player2", deck2, p2_class.default_hero)
	game = Game(players=(player1, player2))
	return game

def run(controller):
	# new thread must have new event loop
	asyncio.set_event_loop(asyncio.new_event_loop())
	controller.run()

def main():
	cards.db.initialize()
	game = create_game()
	controller = GameController(game)

	# start the game loop on a new thread
	t = threading.Thread(target=run, args = (controller,))
	t.start()

	# NOTE: This while loops are NOT thread-safe and will sometimes fail

	# wait for human player to be configured
	while not hasattr(game, "player1"):
		time.sleep(0)

	human_player = game.player1

	# wait for mulligan to become available
	while game.player2.choice is None:
		time.sleep(0)

	# the following code emulates the human player

	# don't mulligan any cards
	human_player.choice.choose()

	while True:
		if game.current_player == human_player:
			# only act on our turn
			logger.info("Human player's turn starts")
			try:
				# all human player behaviour would happen here

				# starts next turn
				# AI might even pass before this returns if it's very fast
				game.end_turn()
			except GameOver:
				break
			logger.info("Human player's turn ends")

	logger.info("Game loop has ended")


if __name__ == "__main__":
	exit(main())
