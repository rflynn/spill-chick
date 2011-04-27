#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ex: set ts=8 noet:
# Copyright 2011 Ryan Flynn <parseerror+spill-chick@gmail.com>

"""
Test our word/grammar algorithm
"""

import sys, re
from chick import Chick

def load_tests():
	# load test cases
	Tests = []
	with open('../test/test.txt','r') as f:
		for l in f:
			l = l.decode('utf8').strip()
			if l == '#--end--':
				break
			if len(l) > 1 and l[0] != '#':
				before, after = l.split(' : ')
				after = re.sub('\s*#.*', '', after.rstrip(), re.U) # replace comments
				Tests.append(([before],[after]))
	return Tests

# TODO: Word() and Grams() should be merged, they're essentially the same

def test():
	"""
	run our tests. initialze resources resources and tests, run each test and
	figure out what works and what doesn't.
	"""
	chick = Chick()
	Tests = load_tests()
	passcnt = 0
	for str,exp in Tests:
		print('Test str=',str,'exp=',exp)
		res = chick.correct(str)
		passcnt += res == exp
		print('-----------','pass' if res == exp else 'fail','------------')
	print('Tests %u/%u passed.' % (passcnt, len(Tests)))

def profile_test():
	import cProfile, pstats
	cProfile.run('test()', 'test.prof')
	st = pstats.Stats('test.prof')
	st.sort_stats('time')
	st.print_stats()

if __name__ == '__main__':

	from sys import argv
	if len(argv) > 1 and argv[1] == '--profile':
		profile_test()
	else:
		test()

