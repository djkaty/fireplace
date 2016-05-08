# Fireplace selector optimizations report

This branch shows test code and results for various selector implementations in both Python and Cython.

Test platform: Intel Core i7-2600K @ 3.4GHz, 16GB RAM, Python 3.5 64-bit (Win7), Cython 0.24 (Win7, MSVC 14 compiler)

#### Running the tests

Run `selector_tests.py` for pure Python tests

Run `selector_tests_cython_bootstrap.py` to compile and run the Cython tests (`selector_tests_opt_cy.pyx`). These tests are optimized for Cython performance.

For Cython non-optimized tests, change the bootstrap file to reference `selector_tests_noopt_cy` instead. The non-optimized tests use identical source code to the pure Python tests, they are just compiled with Cython instead.

The tests use the selector `DRAGON + IN_HAND + FRIENDLY`. The player is given a copy of Alexstrasza. If there happens to be more dragons in the player's hand, the tests will fail with an AssertError. Just re-run the script.

#### View test code

[View test code on GitHub](https://github.com/djkaty/fireplace/compare/work/master...djkaty:work/selector-tests)

The code is commented in detail with explanations of each test.

#### View results

**Please read the test details below before attempting to draw conclusions from the results.**

Excel spreadsheet with all data and graphs is in `fireplace/selector-all.xlsx`

If you can't open Excel spreadsheets, see these PNG images:

[Spreadsheet data](https://raw.githubusercontent.com/djkaty/fireplace/work/selector-tests/selector-data.png)

[Spreadsheet graphs](https://raw.githubusercontent.com/djkaty/fireplace/work/selector-tests/selector-graphs.png)

Blue bar: Hand size = 1

Orange bar: Hand size = 5

Grey bar: Hand size = 10

The data labels shown are for the median hand size of 5.

Y-axis: Run-time (seconds), or speed-up (multiple of original code)

Note the spreadsheet contains some graphs not included above, but they are largely irrelevant.

#### Test terminology

- _Standard selector_ - this is how fireplace currently works and measures current performance
- _Entity segregation_ - fireplace currently uses a bucket of entities (`game.__iter__` returns a chain with player hands, decks, graveyard, board etc.) which are scanned through in their entirety for each selector. The idea of entity segregation is to reduce the work of some selectors by making several buckets. In these tests, the bucket is sliced by zone and player. This means that each player has a `zone_entities` dict, where each key is a member of the Zone enum and each value is a list of entities in that zone. This allows us to avoid scanning the entire bucket of entities in many cases
- _Select entity IDs instead of objects_ - in these tests, selectors return entity IDs instead of entities. This improves the performance of SetOpSelector dramatically as it does not have to build up and tear down lists of entities. The entity IDs are resolved into entity objects at the end of the selection
- _With game entities as dict_ - entities are currently found by iterating the game object. By moving entities into a dictionary keyed by their entity ID, this scanning can be avoided. These tests add the `game.entity_dict` attribute and copy all the entity references into it, then use it for lookups
- _Guaranteed attributes_ - each entity's data currently consists of attributes dynamically generated at run-time via parsing `CardDefs.xml`. This means that `hastattr()` and `getattr()` must often be used. By making the `Entity` base class have every possible attribute with default values, and only modifying attributes found in each entity XML definition for a specific entity, we eliminate the need to use `hasattr()` and `getattr()` which are slow
- _Predicate selectors_ - this was edk/qi's idea; each fully-composed selector (eg. `DRAGON + IN_HAND + FRIENDLY`) is merged or pre-compiled into a single `Selector` object with a single lambda function as the test. This eliminates sub-selectors, dynamic interpretation of set operators and scanning the same entities multiple times
- _Selector-as-filter_ - this was JimboHS's idea; selectors are re-written as lambda functions similar to how filters work. This allows `SetOpSelector` to be eliminated and implemented as a lambda
- _Input lensing_ - this is the process of narrowing the entity list input to selectors - which at the moment is the entire `game` iteration chain - to only those entities which are required. For example, if `IN_HAND + FRIENDLY` is part of the selector, the passed entities can be limited to `game.current_player.hand` to reduce the number of entities scanned

Some optimizations require other optimizations as a pre-requisite. Some optimizations are incompatible with each other.

Note that in the Cython tests, all tests use the guaranteed attributes optimization as all the attributes of a C object must be known at compile-time.

#### Test notes and limitations

These tests are expected to work for `Selector`, `EnumSelector`, `SelectorEntityValue`, `AttrValue`, `ComparisonSelector`, `FilterSelector` and `SetOpSelector`.

`FuncSelector`, `SliceSelector` and `BoardPositionSelector` are ignored.

`RandomSelector` will work in most cases (see exceptions below).

`LazyValue`s are not tested but should be able to be added without too much difficulty.

Only `DRAGON + IN_HAND + FRIENDLY` was used for the test. This selector was chosen because it is extremely slow, has set operations and does duplicate work.

The guaranteed attributes test only use the attributes required in our tests: `zone`, `race` and `controller`. Adding extra attributes is expected to have zero performance impact.

The re-written selectors in the test only re-implement the required selectors; `SetOpSelector` is replaced by `AndSelector` which only implements the `+` operator, for simplicity. Adding the other ops should not cause a performance impact.

#### Test structure

100,000 iterations of each of a series of tests was run, and 1 million iterations of input lensing over the most relevant of those tests.

The tests were re-run for the following hands:

- Just Alexstrasza (1 card)
- Alexstrasza plus 4 random cards (chosen once at startup and re-used) (5 cards)
- Alexstrasza plus 4 random cards plus 5 copies of Museum Curator (arbitrarily chosen non-Dragon card) (10 cards)

The tests were run on an otherwise idle machine.

In all cases, the factor of speed-up reported is compared to the run-time of Python test 1 (just the current standard selectors).

## General test conclusions

Please refer to the spreadsheet data and graphs for results of individual tests.

The direct non-optimized Cython compilation of the Python tests gave an average 8-20% speed increase in all cases and is not discussed further.

- In all cases, _guaranteed attributes_ alone gave the largest speed-up (1.6-1.8x in Python and 8.4x in optimized Cython) for the least amount of programming work. This requires only the base class of `Entity` and the XML parser to be modified

- _Entity segregation_ gave the largest speed-up for the next least amount of work (2.8x in Python and 14x in Cython). This requires the management of the location of entities being added and removed to the game to be modified throughout the entire codebase, but is not a fundamental change

- _Entity IDs instead of objects_ gave a large speed-up where set operations were required, as expected, for minimal work

- _Game entities as dict_ gave a marginal but still worthwhile speed-up for moderate work

- _Predicate selector_ as a stand-alone optimization gave the biggest single speed-up of 5.8x in Python and 24x in Cython (see notes below)

- _Selector as filter_ performed relatively poorly in Python (3.6x) compared to predicate selectors (5.8x) or all of the previous optimizations combined besides predicate selectors (5x) but was the fastest optimization in Cython (25x); we assume this is because this technique builds a tree of function calls which are very expensive in Python but very cheap in Cython

Note that in general, guaranteed attributes will speed up all aspects of fireplace's execution due to heavy use of `getattr()` and `setattr()`, not just selectors.

## Pros and cons

The best total optimizations were as follows:

1. Entity segregation + Entity IDs instead of game objects + Game entities as dict + Guaranteed attributes (8.1x in Python, 20x in Cython)

2. Predicate selector + guaranteed attributes (10x in Python, 24x in Cython)

3. Selector as filter in Cython (25x)

Each of these has advantages and disadvantages:

#### Option 1

**Pros**

- Easiest to implement
- Requires no changes to DSL
- Entity segregation and guaranteed attributes improve the run-time of fireplace in general
- All selector types should continue to function as normal because the actual selector composition logic is not changed

**Cons**

- Worst performance in both Python and Cython (but only slightly, ~20%)
- Game code must be changed to keep entities in the right buckets
- With the exception of guaranteed attributes, none of these optimizations apply to options 2 or 3, so if these were applied at a later date, the work would be wasted

#### Option 2

**Pros**

- Fastest option in Python, very close to fastest (~4-5%) in Cython
- Would be the only optimization required
- All selector types should continue to function as normal because selectors such as `BoardPositionSelector` would be left untouched

**Cons**

- The predicates must be generated somehow. There are 2 main ways:

1. Write them by hand. This works but precludes set operators from being used to combine selectors
2. Pre-compile them. This can be done by Python bytecode (as per edk/qi's suggestion) or writing a Python script which parses the selectors and outputs Python code to implement them as lambdas (my suggestion) as part of `setup_py`. This requires substantial changes to how the DSL is written to make it parseable and represents the most amount of work of any of the optimizations

#### Option 3

**Pros**

- Highest performing in Cython
- Requires no changes to the DSL

**Cons**

- Poor performance in Python (but still 3.5x faster than the current implementation)
- Special cases will have to be made for things such as `RandomSelector` due to the fact that each single entity test is dispatched to a filter function returning bool for inclusion or exclusion

Note that if predicates are implemented using lambdas in Python, they must be substantially re-written for Cython, as due to complex reasons discussed in the source code comments, the filter functions (lambdas) must be implemented as classes in Cython. If taking this option, I recommend starting out by making each predicate a class in pure Python. Note this also helps with the `RandomSelector`-type problem because a filter can then maintain state.

## Input lensing

Input lensing provides massive speed-ups in all cases (50x - 130x in Python, 150x - 550x in Cython, approximate figures). However it raises some complex problems, namely, how does one decide how to narrow the input?

There are two main solutions:

1. Simply only use input lensing in special cases where we know for sure for example that we are only looking at one player's hand or a similarly limited selection of entities, and hardcode this into our calls to `Selector.eval`

2. Re-write the DSL to distinguish between two kinds of selectors: those that give scope to the selection, and those which actually perform the selection. These are essentially the same thing as far as the user is concerned as both are narrowing functions; the difference between them is that in combination with entity segregation, selectors such as `IN_HAND` can simply be reduced to something like `game.zone_entities[Zone.HAND]` without iterating any entities at all, whereas selectors such as `PIRATE` do require scanning every entity and filtering

A simple pseudo-code for such selectors would look like:

`DRAGON.from(IN_HAND_FRIENDLY)`

where in `selector.py` we define `IN_HAND_FRIENDLY` hence:

```
class IN_HAND_FRIENDLY(Selector):
  def eval(self, entities, source):
    return source.game.current_player.hand
```

Of course there are many different ways to implement this.

## Suggested future directions

**Short-term**: Implement guaranteed attributes first, then entity segregation. These will both speed up fireplace's run-time in general as well as selectors

**Medium-term**: Choose one of the three options above and implement it in Python. My preference is option 1 if future work in Cython is not guaranteed, and option 3 if it is guaranteed

**Long-term**: Implement the optimizations in Cython

Ultimate goal: implementing predicate selectors or selectors as filters shows that we can get a speed increase of 24-25x in Cython, and implementing the other less fundamental changes shows we can get a speed-up of 8x in Python. Predicates and guaranteed attributes give the maximum Python-only speed up of 10x.

Katy.
