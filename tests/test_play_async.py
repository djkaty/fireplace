#!/usr/bin/env python
import sys; sys.path.append("..")
from fireplace import cards
from fireplace.exceptions import GameOver
from utils import *


def main():
	game = prepare_game(class1=CardClass.HUNTER)
	tracking = game.player1.give("DS1_184")
	assert not game.player1.choice

	# Synchronous version
	tracking.play()
	assert game.player1.choice

	choice = random.choice(game.player1.choice.cards)
	game.player1.choice.choose(choice)
	#tracking.choose_entity(choice)

	assert not game.player1.choice

	"""
	# Asynchronous version

	tracking.play_start_choice()
	choice = random.choice(game.player1.choice.cards)

	# try to play another card
	game.player1.hand[0].play()

	game.player1.choice.choose(choice)
	assert not game.player1.choice
	tracking.play_end_choice()
	"""

	print("%r" % game.player1.hand)

if __name__ == "__main__":
	main()
