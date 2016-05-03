from typing import List
import string
import random
import time
import csv

class RandomAttrsClass:
	""" Create an instance with 1-5 random attributes named a-z with values 1-100 """
	def __init__(self):
		numattrs = random.randint(1, 5)

		for i in range(numattrs):
			attrname = random.choice(string.ascii_lowercase)
			attrvalue = random.randint(1, 100)

			setattr(self, attrname, attrvalue)


""" Function that takes an object with arbitrary attributes
	and converts them to a dictionary """
def EntityConverter(obj):
	attrlist = [a for a in dir(obj) if not a.startswith('__')]
	dict = {}
	for a in attrlist:
		dict[a] = getattr(obj, a)
	return dict


cdef class LessThanSelector:
	cdef str _attrname
	cdef int _attrvalue

	""" Choose all elements where o.x < y """
	def __init__(self, attrname, attrvalue):
		self._attrname = attrname
		self._attrvalue = attrvalue

	def evaluate(self, entities: List[RandomAttrsClass]) -> List[RandomAttrsClass]:
		return [e for e in entities if self._attrname in e and e[self._attrname] < self._attrvalue]


def test_selector():
	# The number of 'game entities' (rows on spreadsheet)
	numObjects = [50, 100, 500, 1000]

	# The number of selections to do (columns on spreadsheet)
	numIterations = [100, 500, 1000, 2000, 5000]

	# Time taken (seconds)
	timeTaken = []

	# Create game entities
	for objCount in numObjects:
		entities = []
		for i in range(objCount):
			entities.append(EntityConverter(RandomAttrsClass()))

		times = []
		# Selection criteria
		for iterCount in numIterations:
			print(str(objCount) + " entities, " + str(iterCount) + " selections")

			start = time.time()

			for i in range(iterCount):
				LessThanSelector('c', 50).evaluate(entities)

			times.append(time.time() - start)

		timeTaken.append(times)
	
	# Results
	with open('profile.cy.dict.opt.csv', 'w') as csvfile:
		w = csv.writer(csvfile, dialect='excel')
		w.writerows(timeTaken)

if __name__ == "__main__":
	test_selector()
