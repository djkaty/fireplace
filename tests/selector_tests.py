import logging
import time

from utils import *
from fireplace.dsl import *
from fireplace.card import Card

logging.disable(logging.INFO)

def test_selector():
	for hand in range(3):
		game = prepare_game()

		if (hand == 0):
			print("Hand size = 1")
			game.player1.discard_hand()
			game.player1.give("EX1_561")

		elif (hand == 1):
			print("Hand size = 5")
			game.player1.give("EX1_561")

		elif (hand == 2):
			print("Hand size = 10")
			game.player1.give("EX1_561")
			game.player1.give("LOE_006")
			game.player1.give("LOE_006")
			game.player1.give("LOE_006")
			game.player1.give("LOE_006")
			game.player1.give("LOE_006")

		numIterations = 100000
		print("Running " + str(numIterations) + " iterations...")

		# Get all the dragons in all friendly players' hands, using player 1's hand as a source
		# Should return just Alexstrasza

		# 1. Standard selector
		selector = IN_HAND + DRAGON + FRIENDLY

		start = time.time()

		for i in range(numIterations):
			m = selector.eval(game, game.player1)
			assert len(m) == 1
			assert m[0].data.id == "EX1_561"

		elapsed = time.time() - start

		print("1. Standard selector: %.3f sec" % elapsed)


		# 2. With entity segregation

		# The idea is to split up entities into more manageable structures than a single huge game object
		# The game will maintain a zone[Zone.*] attribute, allowing IN_HAND to become player.zone[Zone.HAND]
		# and FRIENDLY becomes the aggregate of the zone attribute array for the player (flattened list)

		# NOTE: This change can be made in a piecemeal fashion throughout the code
		# without modifying the DSL, by defining classes like:
		# class IN_HAND(Selector): def eval(source): return source.zone[Zone.HAND] for example

		# Segregate zone items (this should be maintained as the game state changes by adding and removing items)
		game.zone_entities = {}
	
		zone_enum_list = list(map(int, Zone))
		for zone in zone_enum_list:
			game.zone_entities[zone] = []

		for item in game:
			if (hasattr(item, 'zone')):
				game.zone_entities[item.zone].append(item)

		# If we also split the zones by player, this makes things like FRIENDLY much faster
		game.player1.zone_entities = {}
		game.player2.zone_entities = {}
	
		for zone in zone_enum_list:
			game.player1.zone_entities[zone] = []

		for zone in zone_enum_list:
			game.player2.zone_entities[zone] = []

		for item in game:
			if hasattr(item, 'zone') and hasattr(item, 'controller'):
				item.controller.zone_entities[item.zone].append(item)

		# Some fake selectors
		class DragonSelector(Selector):
			def eval(self, entities, source):
				return [e for e in entities if getattr(e, 'race', Race.INVALID) == Race.DRAGON]

		class InHandSelector(Selector):
			def eval(self, entities, source):
				return source.zone_entities[Zone.HAND]  # we can also just use source.hand here

		class FriendlySelector(Selector):
			def eval(self, entities, source):
				return [item for sublist in source.zone_entities.values() for item in sublist]


		IN_HAND_2 = InHandSelector()
		DRAGON_2  = DragonSelector()
		FRIENDLY_2 = FriendlySelector()
	
		# You can mix and match these with the original IN_HAND, DRAGON and FRIENDLY for comparison
		# FRIENDLY is by far the biggest time killer
		selector = IN_HAND_2 + DRAGON_2 + FRIENDLY_2

		start = time.time()

		# Note the inner loop is the same as (1) so no major code changes needed
		for i in range(numIterations):
			m = selector.eval(game, game.player1)
			assert len(m) == 1
			assert m.pop().data.id == "EX1_561"

		elapsed = time.time() - start

		print("2. (1) + With entity segregation: %.3f sec" % elapsed)


		# 3. Using set operations instead of OpSelector

		# How slow is OpSelector? Let's find out

		start = time.time()

		for i in range(numIterations):
			s1 = IN_HAND.eval(game, game.player1)
			s2 = DRAGON.eval(game, game.player1)
			s3 = FRIENDLY.eval(game, game.player1)
			m = set(s1).intersection(set(s2)).intersection(set(s3))

			assert len(m) == 1
			assert m.pop().data.id == "EX1_561"

		elapsed = time.time() - start

		print("3. (1) + Replace OpSelector with set operations: %.3f sec" % elapsed)


		# 4. Select entity IDs instead of objects

		# Why faff around doing set ops on objects when we can do it on numbers instead?
		# This cuts out all the object-list spin up and teardown

		# We make a new selector base class and SetOp class that mimic the behaviour of
		# the fireplace selectors but are not feature-complete
		class EID_Selector:
			def __add__(self, other) -> "EID_Selector":
				return EID_SetOpSelector(operator.and_, self, other)

		class EID_SetOpSelector(EID_Selector):
			def __init__(self, op: Callable, left: EID_Selector, right: EID_Selector):
				self.op = op
				self.left = left
				self.right = right

			def eval(self, entities, source):
				left_children = self.left.eval(entities, source)
				right_children = self.right.eval(entities, source)
				return self.op(left_children, right_children)

		# Some selectors - these return entity IDs instead of entity lists
		class EID_DragonSelector(EID_Selector):
			def eval(self, entities, source):
				return {e.entity_id for e in entities if getattr(e, 'race', Race.INVALID) == Race.DRAGON}

		class EID_InHandSelector(EID_Selector):
			def eval(self, entities, source):
				return {e.entity_id for e in source.zone_entities[Zone.HAND]}

		class EID_FriendlySelector(EID_Selector):
			def eval(self, entities, source):
				return {item.entity_id for sublist in source.zone_entities.values() for item in sublist}

		DRAGON_EID = EID_DragonSelector()
		IN_HAND_EID = EID_InHandSelector()
		FRIENDLY_EID = EID_FriendlySelector()

		selector = DRAGON_EID + IN_HAND_EID + FRIENDLY_EID

		start = time.time()

		for i in range(numIterations):
			m = selector.eval(game, game.player1)
			# This is the only extra line of code. We can make it a method like Selector.entities()
			m = [e for e in game if e.entity_id in m]
			assert len(m) == 1
			assert m.pop().data.id == "EX1_561"

		elapsed = time.time() - start

		print("4. (2) + Use entity_ids instead of objects: %.3f sec" % elapsed)


		# 5. With game entities as a dict

		# Having to scan the entire game object for matching entity_ids is pretty disgusting
		# How about we just store them in a dict instead?

		# Let's add a dict to game
		# game.__iter__() implements a chain like this:
		# chain(self.entities, self.hands, self.decks, self.graveyard, self.discarded)

		game.entity_dict = {}
		for entity in game:
			game.entity_dict[entity.entity_id] = entity

		selector = DRAGON_EID + IN_HAND_EID + FRIENDLY_EID

		start = time.time()

		for i in range(numIterations):
			m = selector.eval(game, game.player1)
			# Again we could put this in a method like Selector.entities()
			m = [game.entity_dict[entity_id] for entity_id in m]
			assert len(m) == 1
			assert m.pop().data.id == "EX1_561"

		elapsed = time.time() - start

		print("5. (4) + Game entities as dict: %.3f sec" % elapsed)


		# 6. Predicates

		# We want to pre-compile all the selectors used in the DSL into predicates (fireplace #343)
		# Let's see how fast this performs on the current infrastructure

		# DISCUSS: How are we going to actually produce these predicate functions?

		class DragonInHandFriendlySelector(Selector):
			# Ultimately the evaluation function will be supplied as a lambda to the selector
			def eval(self, entities, source):
				return [e for e in entities if (
					getattr(e, 'race', Race.INVALID) == Race.DRAGON
					and e.zone == Zone.HAND
					and e.controller == source
				)]

		selector = DragonInHandFriendlySelector()

		start = time.time()

		# Note: exactly the same inner loop we started with
		for i in range(numIterations):
			m = selector.eval(game, game.player1)
			assert len(m) == 1
			assert m.pop().data.id == "EX1_561"

		elapsed = time.time() - start

		print("6. Predicate selector: %.3f sec" % elapsed)


		# 7. Guaranteed attribute availability based on (5)

		# How slow are hasattr() and getattr()?

		# They are slower than dict lookups, and Cython optimisations cannnot be performed
		# on objects with dynamic attributes. One solution is to convert all of the
		# dynamic attributes of each object to a dict (see work/cython-tests). Here we
		# try an alternative suggested approach, guaranteeing the availability of all
		# the attributes we need.

		# Normally this would be done by defining an entity class with all the possible
		# attributes set to defaults in __init__, and making every entity in CardDefs.xml
		# derive from this and populate only the XML-defined values, but here we'll just
		# add them in to existing entities where needed. We use 'race' as an example
		# since we're selecting dragons.

		for entity in game:
			if not hasattr(entity, 'race'):
				entity.race = Race.INVALID

		# We'll re-define the dragon selector to not use getattr()
		# (IN_HAND_EID and FRIENDLY_EID don't use it anyway)
		class GA_EID_DragonSelector(EID_Selector):
			def eval(self, entities, source):
				return {e.entity_id for e in entities if e.race == Race.DRAGON}

		GA_DRAGON_EID = GA_EID_DragonSelector()

		selector = GA_DRAGON_EID + IN_HAND_EID + FRIENDLY_EID

		start = time.time()

		for i in range(numIterations):
			m = selector.eval(game, game.player1)
			m = [game.entity_dict[entity_id] for entity_id in m]
			assert len(m) == 1
			assert m.pop().data.id == "EX1_561"

		elapsed = time.time() - start

		print("7. (5) + Guaranteed attributes: %.3f sec" % elapsed)


		# 8. Guaranteed attribute availability based on (6)

		# We build a predicate selector that doesn't use getattr() or hasattr()
		class GA_DragonInHandFriendlySelector(Selector):
			# Ultimately the evaluation function will be supplied as a lambda to the selector
			def eval(self, entities, source):
				return [e for e in entities if (
					e.race == Race.DRAGON		# we have just changed this line not to use getattr, otherwise same as (6)
					and e.zone == Zone.HAND
					and e.controller == source
				)]

		selector = GA_DragonInHandFriendlySelector()

		start = time.time()

		# Note: exactly the same inner loop we started with
		for i in range(numIterations):
			m = selector.eval(game, game.player1)
			assert len(m) == 1
			assert m.pop().data.id == "EX1_561"

		elapsed = time.time() - start

		print("8. (6) + Guaranteed attributes: %.3f sec" % elapsed)


		# 9. Selector as filter

		# Here each entity test is farmed out to a lambda function
		# WARNING: This will not work for things like RandomSelectors as we'd have to give
		# a bool for each entity in each individual call to the lambda

		class F_Selector:
			def __init__(self, filter):
				self.filter = filter

			def eval(self, entities, source):
				return [e for e in entities if self.filter(e, source)]

			def __add__(self, other):
				return F_AndSelector(self, other)

		class F_AndSelector(F_Selector):
			def __init__(self, left, right):
				self.filter = lambda e, s: left.filter(e, s) and right.filter(e, s)

		F_DRAGON = F_Selector(lambda e, s: getattr(e, 'race', Race.INVALID) == Race.DRAGON)
		F_IN_HAND = F_Selector(lambda e, s: e.zone == Zone.HAND)
		F_FRIENDLY = F_Selector(lambda e, s: getattr(e, 'controller', None) == s)

		selector = F_DRAGON + F_IN_HAND + F_FRIENDLY

		start = time.time()

		for i in range(numIterations):
			m = selector.eval(game, game.player1)
			assert len(m) == 1
			assert m.pop().data.id == "EX1_561"

		elapsed = time.time() - start

		print("9. Selector as filter: %.3f sec" % elapsed)


		# 10. Selector as filter with guaranteed attributes

		# AFAIK this only applies to BaseTestGame but not 100% sure
		for entity in game:
			if not hasattr(entity, 'controller'):
				entity.controller = None

		F_DRAGON = F_Selector(lambda e, s: e.race == Race.DRAGON)
		F_IN_HAND = F_Selector(lambda e, s: e.zone == Zone.HAND)
		F_FRIENDLY = F_Selector(lambda e, s: e.controller == s)

		selector = F_DRAGON + F_IN_HAND + F_FRIENDLY

		start = time.time()

		for i in range(numIterations):
			m = selector.eval(game, game.player1)
			assert len(m) == 1
			assert m.pop().data.id == "EX1_561"

		elapsed = time.time() - start

		print("10. (9) + Guaranteed attributes: %.3f sec" % elapsed)


		numIterations = 1000000
		print("Running " + str(numIterations) + " iterations...")


		# IL1. Input lensing

		# Right now we pass the entire game object to every selector, this is a waste
		# We need to determine a way of finding the smallest input set, perhaps by a
		# series of rules, for example FRIENDLY + IN_HAND will always limit the result
		# set to entities in game.current_player.hand no matter what, so there is
		# no reason to check any other entities

		# A distinction can be made between two similar but different types of
		# selectors:
		# a. Those which define a scope for the selection with a well-defined object,
		#    eg. IN_HAND maps neatly to "game.player1.hand or game.player2.hand", and
		#	 if we use the segregation in (2), FRIENDLY maps to "game.current_player.zone_entities"
		#
		# b. Those which define a scope which DOES NOT have a well-defined object,
		#    eg. DRAGON does not map nicely to a list of dragons, we must iterate to find them
		#
		# The trick is to find the selector for (a) with the smallest number of inputs,
		# and use any other chained/op'd selectors for (b)

		# In these examples we know we are using IN_HAND + FRIENDLY, so:
		# (a) = IN_HAND + FRIENDLY
		# (b) = DRAGON

		scope = game.player1.hand
		selector = DRAGON

		start = time.time()

		# Note: exactly the same inner loop we started with
		for i in range(numIterations):
			m = selector.eval(scope, game.player1)
			assert len(m) == 1
			assert m.pop().data.id == "EX1_561"

		elapsed = time.time() - start

		print("IL1. (1) + Input lensing: %.3f sec" % elapsed)


		# IL2. Input lensing with segregation, entity ID and dict optimisations

		scope = game.player1.hand
		selector = DRAGON_EID

		start = time.time()

		for i in range(numIterations):
			m = selector.eval(scope, game.player1)
			# Again we could put this in a method like Selector.entities()
			m = [game.entity_dict[entity_id] for entity_id in m]
			assert len(m) == 1
			assert m.pop().data.id == "EX1_561"

		elapsed = time.time() - start

		print("IL2. (5) + Input lensing: %.3f sec" % elapsed)



		# IL3. Input lensing with predicate selectors

		scope = game.player1.hand
		selector = DragonInHandFriendlySelector()

		start = time.time()

		for i in range(numIterations):
			m = selector.eval(scope, game.player1)
			assert len(m) == 1
			assert m.pop().data.id == "EX1_561"

		elapsed = time.time() - start

		print("IL3. (6) + Input lensing: %.3f sec" % elapsed)


		# IL4. Input lensing with selector as filters

		scope = game.player1.hand
		selector = F_DRAGON + F_IN_HAND + F_FRIENDLY

		start = time.time()

		for i in range(numIterations):
			m = selector.eval(scope, game.player1)
			assert len(m) == 1
			assert m.pop().data.id == "EX1_561"

		elapsed = time.time() - start

		print("IL4. (10) + Input lensing: %.3f sec" % elapsed)


if __name__ == "__main__":
	test_selector()


# TODO: Caching - 2 caching strategies: keep total results, or keep individual selector results before OpSelector
# TODO: Cython
# TODO: Selector as filter
