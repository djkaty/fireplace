#!/usr/bin/env python
import sys; sys.path.append("..")
from fireplace import cards
from fireplace.exceptions import GameOver
from utils import *


def main():
	game = prepare_game(class1=CardClass.HUNTER)
	game.player1.discard_hand()
	testcard = game.player1.give(cards.filter(name="Eye of Orsis"))

	assert not game.player1.choice
	testcard.play()
	assert game.player1.choice
	choice = random.choice(game.player1.choice.cards)
	game.player1.choice.choose(choice)
	assert not game.player1.choice

	print("%r" % game.player1.hand)

if __name__ == "__main__":
	main()
