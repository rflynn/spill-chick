#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ex: set ts=8 noet:
# Copyright 2011 Ryan Flynn <parseerror+spill-chick@gmail.com>

"""
Test our word/grammar algorithm
"""

from math import log
from operator import itemgetter
from itertools import takewhile, product, cycle, chain
from collections import defaultdict
import bz2, sys, re
from word import Words
from phon import Phon
from gram import Grams
from doc import Doc
import algo

def levenshtein(a,b):
	"Calculates the Levenshtein distance between a and b."
	n, m = len(a), len(b)
	if n > m:
		# Make sure n <= m, to use O(min(n,m)) space
		a,b = b,a
		n,m = m,n
		
	current = range(n+1)
	for i in range(1,m+1):
		previous, current = current, [i]+[0]*n
		for j in range(1,n+1):
			add, delete = previous[j]+1, current[j-1]+1
			change = previous[j-1]
			if a[j-1] != b[i-1]:
				change = change + 1
			current[j] = min(add, delete, change)
			
	return current[n]

# convenience functions
def rsort(l, **kw):
	return sorted(l, reverse=True, **kw)
def rsortn(l, n):
	return rsort(l, key=itemgetter(n))
def rsort1(l):
	return rsort(l, key=itemgetter(1))
def sortn(l, n):
	return sorted(l, key=itemgetter(n))
def flatten(ll):
	return chain.from_iterable(ll)


def alternatives(w, p, g, d, t):
	"""
	given tok ('token', line, index) return a list of possible alternative tokens.
	only return alternatives that within the realm of popularity of the original token.
	"""
	edit = w.similar(t)
	phon = p.soundsLike(t,g)
	uniq = edit | set(phon)
	minpop = lambda x: round(log(g.freqs(x)))
	alt = [(x,levenshtein(t,x),minpop(x)) for x in uniq if minpop(x) > 0]
	#alt = rsortn(alt, 2)
	#alt = sortn(alt, 1)
	alt2 = [x[0] for x in alt]
	return set(alt2)

def inter_token(toks, freq, g):
	"""
	given a list of tokens, disregard token borders and attempt to find alternate valid
	token lists
	"""
	if sum(map(len, toks)) > 12:
		print('too long for exhaustive')
		return []
	s = list(algo.splits(toks, freq, g))
	return s

def phonGuess(toks, p, g, minfreq):
	"""
	given a list of tokens search for a list of words with similar pronunciation having g.freq(x) > minfreq
	"""
	# create a phentic signature of the ngram
	phonsig = p.phraseSound(toks)
	phonwords = list(p.soundsToWords(phonsig))
	print('phonwords=',phonwords)
	# remove any words we've never seen
	phonwords2 = [[[w for w in p if g.freqs(w) > 1] for p in pw] for pw in phonwords]
	print('phonwords2=',phonwords2)
	# remove any signatures that contain completely empty items after previous
	phonwords3 = [pw for pw in phonwords2 if all(pw)]
	print('phonwords3=',phonwords3)
	phonwords4 = list(flatten([list(product(*pw)) for pw in phonwords3]))
	print('phonwords4=',phonwords4)
	# look up ngram popularity, toss anything not more popular than original and sort
	phonpop = rsort1([(pw, g.freq(pw)) for pw in phonwords4])
	phonpop = list(takewhile(lambda x:x[1] > minfreq, phonpop))
	print('phonpop=',phonpop)
	if phonpop == []:
		return []
	best = phonpop[0][0]
	return [[x] for x in best]

def ngram_suggest(target_ngram, target_freq, d, w, g, p):
	"""
	given an infrequent ngram from a document, attempt to calculate a more frequent one
	that is similar textually and/or phonetically but is more frequent
	"""
	toks = [x[0] for x in target_ngram]
	print('toks=',toks)

	# find potential alternative tokens for the tokens in the unpopular ngrams
	alt = dict([(t, alternatives(w,p,g,d,t)) for t in toks])
	#print('alt=',alt)

	# list all ngrams containing partial matches for our ngram
	part = g.ngram_like(toks)
	print('part=', part)

	"""
	part & alt
	part is based on our corpus and alt based on token similarity.
	an intersection between the two means we've found as good a candidate as we'll get.
	"""
	part_pop = [[p for p in pa if p in alt[t]] for t,pa in zip(toks, part)]
	print('part_pop=', part_pop)

	"""
	the code above is our best shot for repairing simple transpositions, etc.
	for more mangled stuff we try a variety of techniques, falling through to more
	desperate options should each fail
	"""
	if any(p == [] for p in part_pop):
		phong = phonGuess(toks, p, g, target_freq)
		print('phong=',phong)
		if phong != []:
			part_pop = phong
		else:
			intertok = inter_token(toks, w.frq, g)
			print('intertok=', intertok)
			if intertok != []:
				part_pop = [(x,) for x in intertok[0]]
			else:
				for i in range(len(part_pop)):
					if part_pop[i] == []:
						dec = [(t, g.freqs(t), levenshtein(t, toks[i]))
								for t in alt[toks[i]] if t != toks[i]]
						part_pop[i] = [x[0] for x in sortn(dec, 2)][:3]
		print("part_pop'=", part_pop)

	partial = list(product(*part_pop))
	print('partial=', partial)

	best = partial
	# NOTE: i really want izip_longest() but it's not available!
	if len(best[0]) < len(target_ngram[0]):
		best[0] = tuple(list(best[0]) + [''])
	print('best=',best)

	return best

def check(str, w, p, g):
	"""
	given a string, try to fix it
	"""

	d = Doc(str, w)
	print('doc=', d.tok)

	# start out like a regular spellchecker
	# address unknown tokens (ngram size 1) first
	ut = list(d.unknownToks())
	print('unknownToks=',ut)
	utChanges = [(u, w.correct(u[0])) for u in ut]
	print('utChanges=',utChanges)
	d.applyChanges(utChanges)

	"""
	now the hard part.
	locate uncommon n-gram sequences which may indicate grammatical errors
	see if we can determine better replacements for them given their context
	"""

	# order n-grams by unpopularity
	ngsize = min(3, d.totalTokens())
	while ngsize >= min(3, d.totalTokens()):
		ngsize = min(3, d.totalTokens())
		print('ngsize=',ngsize)
		print('ngram(1) freq=',list(d.ngramfreq(g,1)))

		# locate the least-common ngrams
		least_common = sortn(d.ngramfreq(g, ngsize), 1)
		print('least_common=', least_common[:20])
		if least_common == []:
			break
		target_ngram,target_freq = least_common[0]
		print('target_ngram=',target_ngram)

		best = ngram_suggest(target_ngram, target_freq, d, w, g, p)

		if best:
			# present our potential revisions
			proposedChanges = list(zip(target_ngram, best[0]))
			print('proposedChanges...', proposedChanges)
			res = d.demoChanges(proposedChanges)
			print(res)
			d.applyChanges(proposedChanges)
		ngsize -= 1
	return d.lines

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

def init():
	# initialize all "global" data
	print('loading...')
	sys.stdout.flush()
	w = Words()
	print('  phon')
	sys.stdout.flush()
	p = Phon(w)
	print('  corpus...')
	sys.stdout.flush()
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
	print('done.')
	# sanity-check junk
	print('w.correct(naieve)=',w.correct('naieve'))
	print('g.freq((i,know))=',g.freq(('i','know')))
	print('g.freq((it,use))=',g.freq(('it','use')))
	alt_know = alternatives(w,p,g,None,'know')
	print('alt(know)=',alt_know)
	alt_now = alternatives(w,p,g,None,'now')
	print('alt(now)=',alt_now)
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
		res = check(str, w, p, g)
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

