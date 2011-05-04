#!/usr/bin/env python

"""
benchmark fastest implementation of key generating algorithm for tokens.
gets called ~600 million times in CPU-bound task.

>>> def doit1():
... import string
... string.lower('Python')
...
>>> import string
>>> def doit2():
... string.lower('Python')
...
>>> import timeit
>>> t = timeit.Timer(setup='from __main__ import doit1', stmt='doit1()')
>>> t.timeit()
11.479144930839539
>>> t = timeit.Timer(setup='from __main__ import doit2', stmt='doit2()')
>>> t.timeit()
4.6661689281463623
"""

def id1(d, key):
	try:
		return d[key]
	except KeyError:
		cnt = len(d)
		d[key] = cnt
		return cnt

def id2(d, key):
	ld = len(d)
	val = d.get(key, ld)
	if val == ld:
		d[key] = val
	return val

def id3(d, key):
	if key in d:
		return d[key]
	else:
		cnt = len(d)
		d[key] = cnt
		return cnt

Id = {}
def id4(_, key):
	global Id
	if key in Id:
		return Id[key]
	else:
		cnt = len(Id)
		Id[key] = cnt
		return cnt

from random import randint

def foo(f):
	d = {}
	for _ in range(1,1000):
		f(d, randint(0, 20))

import timeit
for n in range(1,5):
	print '%d:%s' % (n, timeit.Timer(setup='from __main__ import foo,id%d' % n, stmt='foo(id%d)' % n).timeit(number=1000))

