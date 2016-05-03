#!/usr/bin/env python
import sys;
sys.path.insert(0, "../..")
sys.path.insert(0, "../../tests")
from utils import *
from fireplace.dsl import *
from fireplace.card import Card

numIterations = 1000

game = prepare_game()
game.player1.discard_hand()
alex = game.player1.give("EX1_561")
selector = PIRATE | DRAGON + MINION

for i in range(numIterations):
	assert len(selector.eval(game.player1.hand, game.player1)) >= 1

selector = IN_HAND + DRAGON + FRIENDLY

for i in range(numIterations):
	targets = selector.eval(game, game.player1)
	assert len(targets) == 1
	assert targets[0] == alex
