import logging
import time

from utils import *
from fireplace.dsl import *
from fireplace.card import Card

# the libcpp bool is faster but Cython forgets to add #include <stdbool.h>,
# so we need to add it manually to the generated .c file if we use this
#from libcpp cimport bool

# the slower but-still-faster-than-pure-python Python bool
from cpython cimport bool

logging.disable(logging.INFO)


# Base entity class for approach 1 (see below)
# Cython classes cannot be nested
cdef class CY_Entity:
	# For CY2
	cdef public dict zone_entities

	cdef public int entity_id
	cdef public int race
	cdef public int zone
	cdef public CY_Entity controller

	# We're just providing game to help with player conversion here
	# This won't normally be necessary
	def __init__(self, entity=None, game=None):
		self.zone_entities = {}

		if not entity is None:
			# Convert a Python entity to a Cython entity
			# In the real code, none of this will be needed
			self.entity_id = entity.entity_id
			self.race = getattr(entity, 'race', Race.INVALID)
			self.zone = getattr(entity, 'zone', Zone.INVALID)
			controller = getattr(entity, 'controller', None)

			if isinstance(controller, CY_Entity):
				self.controller = controller

			elif isinstance(controller, Player):
				if controller == game.player1:
					self.controller = game.cy_player1

				elif controller == game.player2:
					self.controller = game.cy_player2


# Selectors for CY1
cdef class CY_Selector:
	def __add__(self, CY_Selector other) -> "CY_Selector":
		return CY_OpAddSelector(self, other)

	# entities will normally be CY_Entity *
	cdef set _entity_id_set(self, list entities):
		return set(e.entity_id for e in entities if e)

cdef class CY_OpAddSelector(CY_Selector):
	cdef CY_Selector left
	cdef CY_Selector right

	def __init__(self, CY_Selector left, CY_Selector right):
		self.left = left
		self.right = right

	# entities will normally be CY_Entity *
	cpdef list eval(self, list entities, CY_Entity source):
		left_children = self._entity_id_set(self.left.eval(entities, source))
		right_children = self._entity_id_set(self.right.eval(entities, source))
		result = left_children & right_children
		return [e for e in entities if e.entity_id in result]

cdef class CY1_DragonSelector(CY_Selector):
	cpdef list eval(self, list entities, CY_Entity source):
		return [e for e in entities if e.race == Race.DRAGON]

cdef class CY1_InHandSelector(CY_Selector):
	cpdef list eval(self, list entities, CY_Entity source):
		return [e for e in entities if e.zone == Zone.HAND]

cdef class CY1_FriendlySelector(CY_Selector):
	cpdef list eval(self, list entities, CY_Entity source):
		return [e for e in entities if e.controller == source]

CY1_DRAGON = CY1_DragonSelector()
CY1_IN_HAND = CY1_InHandSelector()
CY1_FRIENDLY = CY1_FriendlySelector()


# Selectors for CY2
cdef class CY2_DragonSelector(CY_Selector):
	cpdef list eval(self, list entities, CY_Entity source):
		return [e for e in entities if e.race == Race.DRAGON]

cdef class CY2_InHandSelector(CY_Selector):
	cpdef list eval(self, list entities, CY_Entity source):
		return source.zone_entities[Zone.HAND]  # we can also just use source.hand here

cdef class CY2_FriendlySelector(CY_Selector):
	cpdef list eval(self, list entities, CY_Entity source):
		return [item for sublist in source.zone_entities.values() for item in sublist]

CY2_DRAGON = CY2_DragonSelector()
CY2_IN_HAND = CY2_InHandSelector()
CY2_FRIENDLY = CY2_FriendlySelector()


# Selectors for CY3
cdef class CY_EID_Selector:
	def __add__(self, CY_EID_Selector other) -> "CY_EID_Selector":
		return CY_EID_AddSelector(self, other)

cdef class CY_EID_AddSelector(CY_EID_Selector):
	cdef CY_EID_Selector left
	cdef CY_EID_Selector right

	def __init__(self, CY_EID_Selector left, CY_EID_Selector right):
		self.left = left
		self.right = right

	cpdef set eval(self, list entities, CY_Entity source):
		left_children = self.left.eval(entities, source)
		right_children = self.right.eval(entities, source)
		return left_children & right_children

cdef class CY_EID_DragonSelector(CY_EID_Selector):
	cpdef set eval(self, list entities, CY_Entity source):
		return {e.entity_id for e in entities if e.race == Race.DRAGON}

cdef class CY_EID_InHandSelector(CY_EID_Selector):
	cpdef set eval(self, list entities, CY_Entity source):
		return {e.entity_id for e in source.zone_entities[Zone.HAND]}

cdef class CY_EID_FriendlySelector(CY_EID_Selector):
	cpdef set eval(self, list entities, CY_Entity source):
		return {item.entity_id for sublist in source.zone_entities.values() for item in sublist}

CY_DRAGON_EID = CY_EID_DragonSelector()
CY_IN_HAND_EID = CY_EID_InHandSelector()
CY_FRIENDLY_EID = CY_EID_FriendlySelector()


# Selectors for CY5
cdef class CY_DragonInHandFriendlySelector(CY_Selector):
	# Ultimately the evaluation function will be supplied as a lambda to the selector
	cpdef list eval(self, list entities, CY_Entity source):
		return [e for e in entities if (
			e.race == Race.DRAGON
			and e.zone == Zone.HAND
			and e.controller == source
		)]


# Selectors for CY6

# IMPORTANT! Unlike the pure Python implementation,
# set op selectors (And etc.) must be implemented as filters, NOT selectors
# This is because they must maintain state (left and right), and the
# special method __add__ does not allow a subclass instance to be passed
# under Cython

# This also means that filters must be implemented as classes, NOT lambdas
# because Cython does not support lambdas as function pointers

# However, this has the advantage that all filters can store state if they want to

cdef class CY_F_Filter:
	cdef bool filter(self, CY_Entity e, CY_Entity s):
		return True

cdef class CY_F_FilterDragon(CY_F_Filter):
	cdef bool filter(self, CY_Entity e, CY_Entity s):
		return e.race == Race.DRAGON

cdef class CY_F_FilterInHand(CY_F_Filter):
	cdef bool filter(self, CY_Entity e, CY_Entity s):
		return e.zone == Zone.HAND

cdef class CY_F_FilterFriendly(CY_F_Filter):
	cdef bool filter(self, CY_Entity e, CY_Entity s):
		return e.controller == s


cdef class CY_F_FilterAnd(CY_F_Filter):
	cdef CY_F_Filter left
	cdef CY_F_Filter right

	def __init__(self, CY_F_Filter left, CY_F_Filter right):
		self.left = left
		self.right = right

	cdef bool filter(self, CY_Entity e, CY_Entity s):
		return self.left.filter(e, s) and self.right.filter(e, s)


cdef class CY_F_Selector:
	# This must be public to be accessible fromself. __add__
	cdef public CY_F_Filter filter

	def __init__(self, CY_F_Filter filter):
		self.filter = filter

	cpdef list eval(self, list entities, CY_Entity source):
		return [e for e in entities if self.filter.filter(e, source)]

	def __add__(self, CY_F_Selector other):
		return CY_F_Selector(CY_F_FilterAnd(self.filter, other.filter))


CY_F_DRAGON = CY_F_Selector(CY_F_FilterDragon())
CY_F_IN_HAND = CY_F_Selector(CY_F_FilterInHand())
CY_F_FRIENDLY = CY_F_Selector(CY_F_FilterFriendly())


# Main entry point
def test_selector():
	cdef list cy_game
	cdef dict game_entity_dict
	cdef CY_Entity cy_player1
	cdef CY_Entity cy_player2
	cdef list scope
	cdef list ml
	cdef set ms
	cdef int i

	# To be able to optimize the code in Cython, we MUST use static attributes (known at compile-time)
	# so the current entity objects are no good for our purposes. There are two ways to deal with this:

	# 1. Make sure every entity derives from a class which has every attribute at compile-time
	# 2. Convert entity attributes we need to enumerate into a dict

	# Once this is done, the entity objects can be statically typed for maximum speed-up

	game = prepare_game()

	for hand in range(3):
		if (hand == 0):
			print("Hand size = 5")
			game.player1.give("EX1_561")

		elif (hand == 1):
			print("Hand size = 10")
			game.player1.give("LOE_006")
			game.player1.give("LOE_006")
			game.player1.give("LOE_006")
			game.player1.give("LOE_006")
			game.player1.give("LOE_006")

		elif (hand == 2):
			print("Hand size = 1")
			game.player1.discard_hand()
			game.player1.give("EX1_561")


		numIterations = 100000
		print("Running " + str(numIterations) + " iterations...")


		# CY1. Select using all-attributes base class (CY_Entity)
		# This is equivalent to "standard selector + guaranteed attributes" in normal Python code

		# Replace all the entities in game with CY_Entity
		# Normally Game and all its enumerable objects will derive from CY_Entity and this won't be necessary
		print("Converting...")

		# Convert players to CY_Entity first
		# Normally this won't be necessary either
		cy_player1 = CY_Entity()
		cy_player1.entity_id = game.player1.entity_id
		cy_player1.controller = cy_player1
		cy_player2 = CY_Entity()
		cy_player2.entity_id = game.player2.entity_id
		cy_player2.controller = cy_player2

		game.cy_player1 = cy_player1
		game.cy_player2 = cy_player2

		# Convert all game entities to CY_Entity
		cy_game = [CY_Entity(e, game) for e in game if isinstance(e, Entity)]

		# Check that our Cython entities do what they're supposed to do
		dragons  = DRAGON.eval(game, game.player1)
		inhand   = IN_HAND.eval(game, game.player1)
		friendly = FRIENDLY.eval(game, game.player1)

		cy_dragons  = CY1_DRAGON.eval(cy_game, cy_player1)
		cy_inhand   = CY1_IN_HAND.eval(cy_game, cy_player1)
		cy_friendly = CY1_FRIENDLY.eval(cy_game, cy_player1)

		assert len(dragons) == len(cy_dragons)
		assert len(inhand) == len(cy_inhand)
		assert len(friendly) == len(cy_friendly)

		for i, item in enumerate(dragons):
			assert item.entity_id == cy_dragons[i].entity_id

		for i, item in enumerate(inhand):
			assert item.entity_id == cy_inhand[i].entity_id

		for i, item in enumerate(friendly):
			assert item.entity_id == cy_friendly[i].entity_id

		selector = DRAGON + IN_HAND + FRIENDLY
		cy_selector = CY1_DRAGON + CY1_IN_HAND + CY1_FRIENDLY

		total = selector.eval(game, game.player1)
		cy_total = cy_selector.eval(cy_game, cy_player1)

		assert len(total) == 1
		assert len(cy_total) == 1
		assert total[0].entity_id == cy_total[0].entity_id

		# CY_Entity has no data attribute so we'll test for the right entity_id instead
		our_alexstrasza_id = total[0].entity_id

		# Now do the performance test
		print("Running...")

		start = time.time()

		for i in range(numIterations):
			ml = cy_selector.eval(cy_game, cy_player1)
			assert ml.pop().entity_id == our_alexstrasza_id

		elapsed = time.time() - start

		print("CY1. Static-typed entities: %.3f sec" % elapsed)


		# CY2. With entity segregation

		zone_enum_list = list(map(int, Zone))

		# Split entities by zone and controlling player
		cy_player1.zone_entities = {}
		cy_player2.zone_entities = {}
	
		for zone in zone_enum_list:
			cy_player1.zone_entities[zone] = []

		for zone in zone_enum_list:
			cy_player2.zone_entities[zone] = []

		for item in cy_game:
			if not item.controller is None:
				item.controller.zone_entities[item.zone].append(item)

		# Do the test
		cy_selector = CY2_DRAGON + CY2_IN_HAND + CY2_FRIENDLY

		start = time.time()

		for i in range(numIterations):
			ml = cy_selector.eval(cy_game, cy_player1)
			assert ml.pop().entity_id == our_alexstrasza_id

		elapsed = time.time() - start

		print("CY2. (CY1) + With entity segregation: %.3f sec" % elapsed)


		# CY3. Select entity IDs instead of objects

		cy_selector = CY_DRAGON_EID + CY_IN_HAND_EID + CY_FRIENDLY_EID

		start = time.time()

		for i in range(numIterations):
			ms = cy_selector.eval(cy_game, cy_player1)
			# This is the only extra line of code. We can make it a method like Selector.entities()
			ml = [e for e in cy_game if e.entity_id in ms]
			assert ml.pop().entity_id == our_alexstrasza_id

		elapsed = time.time() - start

		print("CY3. (CY2) + Use entity_ids instead of objects: %.3f sec" % elapsed)


		# CY4. With game entities as a dict

		game_entity_dict = {}
		for entity in cy_game:
			game_entity_dict[entity.entity_id] = entity

		cy_selector = CY_DRAGON_EID + CY_IN_HAND_EID + CY_FRIENDLY_EID

		start = time.time()

		for i in range(numIterations):
			ms = cy_selector.eval(cy_game, cy_player1)
			# Again we could put this in a method like Selector.entities()
			ml = [game_entity_dict[entity_id] for entity_id in ms]
			assert ml.pop().entity_id == our_alexstrasza_id

		elapsed = time.time() - start

		print("CY4. (CY3) + Game entities as dict: %.3f sec" % elapsed)


		# CY5. Predicates

		cy_selector = CY_DragonInHandFriendlySelector()

		start = time.time()

		# Note: exactly the same inner loop we started with
		for i in range(numIterations):
			ml = cy_selector.eval(cy_game, cy_player1)
			assert ml.pop().entity_id == our_alexstrasza_id

		elapsed = time.time() - start

		print("CY5. (CY1) + Predicate selector: %.3f sec" % elapsed)


		# CY6. Selector as filter

		# Check that our Cython selectors do what they're supposed to do
		dragons  = DRAGON.eval(game, game.player1)
		inhand   = IN_HAND.eval(game, game.player1)
		friendly = FRIENDLY.eval(game, game.player1)

		cy_dragons  = CY_F_DRAGON.eval(cy_game, cy_player1)
		cy_inhand   = CY_F_IN_HAND.eval(cy_game, cy_player1)
		cy_friendly = CY_F_FRIENDLY.eval(cy_game, cy_player1)

		assert len(dragons) == len(cy_dragons)
		assert len(inhand) == len(cy_inhand)
		assert len(friendly) == len(cy_friendly)

		for i, item in enumerate(dragons):
			assert item.entity_id == cy_dragons[i].entity_id

		for i, item in enumerate(inhand):
			assert item.entity_id == cy_inhand[i].entity_id

		for i, item in enumerate(friendly):
			assert item.entity_id == cy_friendly[i].entity_id

		selector = DRAGON + IN_HAND + FRIENDLY
		cy_selector = CY_F_DRAGON + CY_F_IN_HAND + CY_F_FRIENDLY

		total = selector.eval(game, game.player1)
		cy_total = cy_selector.eval(cy_game, cy_player1)

		assert len(total) == 1
		assert len(cy_total) == 1
		assert total[0].entity_id == cy_total[0].entity_id

		# Now do the test
		cy_selector = CY_F_DRAGON + CY_F_IN_HAND + CY_F_FRIENDLY

		start = time.time()

		for i in range(numIterations):
			ml = cy_selector.eval(cy_game, cy_player1)
			assert ml.pop().entity_id == our_alexstrasza_id

		elapsed = time.time() - start

		print("CY6. Selector as filter: %.3f sec" % elapsed)




		numIterations = 1000000
		print("Running " + str(numIterations) + " iterations...")


		# ILCY1. Input lensing

		# Well normally we'd set scope to cy_game.player1.hand but it doesn't exist so we cheat here
		# (assume this has a run-time of zero, or the same as accessing game.player1.hand)
		scope = (CY1_FRIENDLY + CY1_IN_HAND).eval(cy_game, cy_player1)

		cy_selector = CY1_DRAGON

		start = time.time()

		# Note: exactly the same inner loop we started with
		for i in range(numIterations):
			ml = cy_selector.eval(scope, cy_player1)
			assert ml.pop().entity_id == our_alexstrasza_id

		elapsed = time.time() - start

		print("ILCY1. (CY1) + Input lensing: %.3f sec" % elapsed)


		# ILCY2. Input lensing with segregation, entity ID and dict optimisations

		scope = (CY1_FRIENDLY + CY1_IN_HAND).eval(cy_game, cy_player1)
		cy_selector = CY_DRAGON_EID

		start = time.time()

		for i in range(numIterations):
			ms = cy_selector.eval(scope, cy_player1)
			ml = [game_entity_dict[entity_id] for entity_id in ms]
			assert ml.pop().entity_id == our_alexstrasza_id

		elapsed = time.time() - start

		print("ILCY2. (CY4) + Input lensing: %.3f sec" % elapsed)


		# ILCY3. Input lensing with predicate selectors

		scope = (CY1_FRIENDLY + CY1_IN_HAND).eval(cy_game, cy_player1)
		cy_selector = CY_DragonInHandFriendlySelector()

		start = time.time()

		for i in range(numIterations):
			ml = cy_selector.eval(scope, cy_player1)
			assert ml.pop().entity_id == our_alexstrasza_id

		elapsed = time.time() - start

		print("ILCY3. (CY5) + Input lensing: %.3f sec" % elapsed)


		# ILCY4. Input lensing with selector as filters

		scope = (CY1_FRIENDLY + CY1_IN_HAND).eval(cy_game, cy_player1)
		cy_selector = CY_F_DRAGON + CY_F_IN_HAND + CY_F_FRIENDLY

		start = time.time()

		for i in range(numIterations):
			ml = cy_selector.eval(scope, cy_player1)
			assert ml.pop().entity_id == our_alexstrasza_id

		elapsed = time.time() - start

		print("ILCY4. (CY6) + Input lensing: %.3f sec" % elapsed)


if __name__ == "__main__":
	test_selector()


# TODO: Caching - 2 caching strategies: keep total results, or keep individual selector results before OpSelector
