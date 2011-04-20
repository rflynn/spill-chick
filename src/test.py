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
import copy
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
	if phonwords == [[]]:
		phonpop = []
	else:
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


def do_suggest(target_ngram, freq, ctx, d, w, g, p):
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
	however, if any of the tokens do not intersect part & alt...
	for more mangled stuff we try a variety of techniques,
	falling through to more desperate options should each fail
	"""
	if any(p == [] for p in part_pop):
		phong = phonGuess(toks, p, g, freq)
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
	if len(best[0]) < len(target_ngram):
		best[0] = tuple(list(best[0]) + [''])
	print('best=',best)

	def canon(ng):
		if ng[-1] == '':
			return tuple(list(ng)[:-1])
		return ng

	# if our best suggestions are no more frequent than what we started with, give up!
	if max(g.freq(canon(b)) for b in best) <= freq:
		best = []

	return best

def ngram_suggest(target_ngram, freq, d, w, g, p):
	"""
	we calculate ngram context and collect solutions for each context
	permutation containing the target. then merge these suggestions
	into a cohesive, best suggestion.
		    c d e
                a b c d e f g
	given ngram (c,d,e), calculate context and solve:
	[S(a,b,c), S(b,c,d), S(c,d,e), S(d,e,f), S(e,f,g)]
	"""

	print('target_ngram=', target_ngram)

	tlen = len(target_ngram)

	context = list(d.ngram_context(target_ngram, tlen))
	print('context=', context)
	clen = len(context)

	context_ngrams = [tuple(context[i:i+tlen]) for i in range(clen-tlen)]

	# gather suggestions for each ngram overlapping target_ngram
	sugg = [(ng, do_suggest(ng, g.freq(ng), context_ngrams, d, w, g, p))
		for ng in context_ngrams]

	print('sugg=', sugg)
	for ng,su in sugg:
		for s in su:
			print('%s%s %u' % (' ' * ng[0][3], ' '.join(s), g.freq(s)))

	def apply_suggest(ctx, ng, s):
		# replace 'ng' slice of 'ctx' with contents of text-only ngram 's'
		ctx = copy.copy(ctx)
		index = ctx.index(ng[0])
		for i in range(len(ng)):
			c = ctx[index+i]
			ctx[index+i] = (s[i], c[1], c[2], c[3])
		return (' '.join([c[0] for c in ctx]), ng, s)

	def realize_suggest(ctx, sugg):
		"""
		ctx is a list of positional ngrams; our 'target'
		sugg is a list of changesets.
		return map ctx x sugg
		"""
		return [[apply_suggest(ctx, ng, s) for s in su] for ng,su in sugg]

	# merge suggestions based on what they change
	realized = realize_suggest(context, sugg)
	print('realized=', realized)
	realcnt = defaultdict(int)
	for real in realized:
		for sctx,ng,s in real:
			realcnt[sctx] += 1 + g.freq(s)
			print(sctx)
	print('realcnt=',realcnt)

	# calculate the most-recommended change

	# sort based on frequency, then on order (best first)

	return do_suggest(target_ngram, freq, context_ngrams, d, w, g, p)


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
	print('ngsize=',ngsize)
	print('ngram(1) freq=',list(d.ngramfreq(g,1)))

	# locate the least-common ngrams
	least_common = sortn(d.ngramfreq(g, ngsize), 1)
	print('least_common=', least_common[:20])

	while least_common:
		target_ngram,target_freq = least_common.pop(0)
		best = ngram_suggest(target_ngram, target_freq, d, w, g, p)
		if best:
			# present our potential revisions
			proposedChanges = list(zip(target_ngram, best[0]))
			print('proposedChanges...', proposedChanges)
			res = d.demoChanges(proposedChanges)
			print(res)
			d.applyChanges(proposedChanges)
		# FIXME: save progress
		#least_common = sortn(d.ngramfreq(g, ngsize), 1)
		least_common = []
		print('least_common=', least_common[:20])

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

