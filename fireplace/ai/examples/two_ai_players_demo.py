#!/usr/bin/env python
import logging
from fireplace import cards
from fireplace.game import Game
from fireplace.utils import *
from fireplace.controller import GameController
from fireplace.ai.always_hero_power import HeroPowerAI as PlayerAI

logging.basicConfig(level=logging.INFO)
logging.getLogger("fireplace").disabled = True


def create_game():
	p1_class = random_class()
	p2_class = random_class()
	deck1 = random_draft(p1_class)
	deck2 = random_draft(p2_class)
	player1 = PlayerAI("Player1", deck1, p1_class.default_hero)
	player2 = PlayerAI("Player2", deck2, p2_class.default_hero)
	game = Game(players=(player1, player2))
	return game


def main():
	cards.db.initialize()
	game = create_game()
	controller = GameController(game)
	controller.run()
	print("Game loop has ended")


if __name__ == "__main__":
	exit(main())
