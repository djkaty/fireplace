#!/usr/bin/env python
import sys
sys.path.insert(0, "../../tests")
import time

from utils import *
from fireplace.dsl import *
from fireplace.card import Card
import logging

logging.disable(logging.INFO)

def test_selector():
	numIterations = 10000

	game = prepare_game()
	game.player1.discard_hand()
	alex = game.player1.give("EX1_561")

	start = time.time()

	# Get all the pirates and dragons in the player's hand
	# The player's hand is Alexstrasza (a dragon) so this should always return just Alexstrasza
	# NOTE: MINION selector is irrelevant, spells and weapons cannot have racial types
	selector = PIRATE | DRAGON + MINION
	for i in range(numIterations):
		assert len(selector.eval(game.player1.hand, game.player1))==1

	elapsed = time.time() - start

	print(elapsed)

	start = time.time()

	# Get all the dragons in all friendly players' hands, using player 1's hand as a source
	# Again, should return Alexstrasza, but takes ~35 times longer to execute
	selector = IN_HAND + DRAGON + FRIENDLY
	for i in range(numIterations):
		assert len(selector.eval(game, game.player1))==1

	elapsed = time.time() - start

	print(elapsed)

if __name__ == "__main__":
	test_selector()
