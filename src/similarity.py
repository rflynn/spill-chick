#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
token and ngram comparison
incorporate:
	edit-distance
		consonants/vowels(?)
	sound
	popularity/frequency
"""

from math import sqrt,log
from util import  damerau_levenshtein

def sim_score(x, y, p, g):
	"""
	given strings x and y, produce tuple of similarity scores using different means
	"""
	return (similarity(x, y, p),
	        int(x[0] == y[0]), # starts with same letter
	        g.freqs(y)) # frequency; never a good first option but separates the wheat from the chaff

def sim_order(tok, alts, p, g):
	"""
	given a token and a list of alternative tokens, score and sort alts
	in descending order of similarity to tok
	"""
	sim1 = [(alt, sim_score(tok, alt, p, g)) for alt in alts]
	sim2 = sorted(sim1, key=lambda x:x[1][1], reverse=True)
	sim3 = sorted(sim2, key=lambda x:x[1][2], reverse=True)
	sim4 = sorted(sim3, key=lambda x:x[1][0]) # FIXME
	return sim4


def sim_order_ngrampop(ng, alts, p, g):
	#print 'ng=',ng,'alts=',alts[:10],'...'
	ngfreq = g.freq(ng)
	sim1 = [(alt, sim_score_ngram(ng, ngfreq, alt, p, g)) for alt in alts]
	sim2 = sorted(sim1, key=lambda x:x[1][3], reverse=True)
	sim3 = sorted(sim2, key=lambda x:x[1][2], reverse=True)
	sim4 = sorted(sim3, key=lambda x:x[1][0], reverse=True)
	#print 'sim_order_ngrampop=',sim4[:50],'...'
	return sim4

if __name__ == '__main__':
	import sys
	sys.path.append('..')
	from grambin import GramsBin
	from word import Words,NGram3BinWordCounter
	from phon import Phon
	import logging

	logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
	logging.debug('loading...')
	g = GramsBin(
		'/home/pizza/proj/spill-chick/data/corpus/google-ngrams/word.bin',
		'/home/pizza/proj/spill-chick/data/corpus/google-ngrams/ngram3.bin')
	w = Words(NGram3BinWordCounter(g.ng))
	p = Phon(w,g)
	logging.debug('loaded.')

	# test single tokens
	for tok,alts in [	
		('bomb', ['bob','comb','tom','tomb','womb','ohm','boo','bbbb','unrelated','i']),
		('apart', ['part','par','party','partly','aaaaa','unrelated','i']),
		('eatin', ['eden','gethsemane']), ]:
		# for some reason max(len(s),...) blows up when s is str but not unicode, wtf
		tok,alts = unicode(tok),map(unicode,alts)
		sim = sim_order(tok, alts, p, g)
		print('%s %s' % (tok, [(str(alt),score) for alt,score in sim]))

	# test full ngrams
	for ng,alts in [	
		(('bridge','the','gas'),
		 [('in','the','gap', 5077L), ('through','the','gap', 4397L), ('bridging','the','gap', 3547L), ('fill','the','gap', 3072L), ('close','the','gap', 2388L), ('to','the','gap', 2044L), ('and','the','gap', 1969L), ('that','the','gap', 1859L), ('closing','the','gap', 1672L), ('into','the','gap', 1649L), ('at','the','gap', 1316L), ('across','the','gap', 1156L), ('up','the','gap', 1122L), ('bridges','the','gap', 842L), ('is','the','gap', 832L), ('closed','the','gap', 820L),('bridge','the','gap', 6241L)])
		]:
		# for some reason max(len(s),...) blows up when s is str but not unicode, wtf
		def ed(ng,f): return tuple(map(f,ng[:-1]) + [ng[-1]])
		def enc(ng): return ed(ng,unicode)
		def dec(ng): return ed(ng,str)
		ng,alts = map(unicode,ng), map(enc, alts)
		sim = sim_order_ngrampop(ng, alts, p, g)
		print('%s %s' % (ng, [(dec(s),sc) for (s,sc) in sim]))

