#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ex: set ts=8 noet:
# Copyright 2011 Ryan Flynn <parseerror+spill-chick@gmail.com>

"""
Test our word/grammar algorithm
"""

import sys, re
from grambin import GramsBin
from word import Words,NGram3BinWordCounter
from phon import Phon
import chick

def load_tests():
	# load test cases
	Tests = []
	with open('../test/test.txt','r') as f:
		for l in f:
			l = l.strip()
			if l == '#--end--':
				break
			if len(l) > 1 and l[0] != '#':
				before, after = l.strip().split(' : ')
				after = re.sub('\s*#.*', '', after.rstrip()) # replace comments
				Tests.append(([before],[after]))
	return Tests

# TODO: Word() and Grams() should be merged, they're essentially the same

def init():
	# initialize all "global" data
	print('loading...')
	sys.stdout.flush()
	print('  corpus...')
	sys.stdout.flush()
	g = GramsBin(
		'../data/corpus/google-ngrams/word.bin',
		'../data/corpus/google-ngrams/ngram3.bin')
	w = Words(NGram3BinWordCounter(g.ng))
	print('  phon')
	sys.stdout.flush()
	p = Phon(w)
	"""
	g = Grams(w)
	for filename in ['big.txt','idioms.txt','dict-debian-american-english.bz2']:#,'wiki-titles-scrubbed.txt']:
		print('   ',filename)
		sys.stdout.flush()
		try:
			o = bz2.BZ2File if filename.endswith('.bz2') else open
			with o('../data/corpus/'+filename, 'r') as f:
				g.add(f)
		except:
			pass
	"""
	print('done.')
	# sanity-check junk
	# note: string/unicode fucks python2
	"""
	print('w.correct(naieve)=',w.correct(u'naieve'))
	print('g.freq((didn))=',g.freq(('didn',)))
	print('g.freq((a,mistake))=',g.freq(('a','mistake')))
	print('g.freq((undoubtedly,be,changed))=',g.freq(('undoubtedly','be','changed')))
	print('g.freq((undoubtedly,be))=',g.freq(('undoubtedly','be')))
	print('g.freq((be,changed))=',g.freq(('be','changed')))
	print('g.freq((it,it,did))=',g.freq(('it','it','did')))
	print('g.freq((it,it))=',g.freq(('it','it')))
	print('g.freq((it,did))=',g.freq(('it','did')))
	"""
	#alt_know = alternatives(w,p,g,None,'know')
	#print('alt(know)=',alt_know)
	#alt_now = alternatives(w,p,g,None,'now')
	#print('alt(now)=',alt_now)
	#assert 'know' in alt_now
	return (w, p, g)

def test():
	"""
	run our tests. initialze resources resources and tests, run each test and
	figure out what works and what doesn't.
	"""
	w,p,g = init()
	Tests = load_tests()
	passcnt = 0
	for str,exp in Tests:
		res = chick.correct(str, w, p, g)
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

