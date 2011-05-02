#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ex: set ts=8 noet:
# Copyright 2011 Ryan Flynn <parseerror+spill-chick@gmail.com>

"""
word/grammar checking algorithm

Facts
	* the corpus is not perfect. it contains errors.
	* not every valid ngram will exist in the corpus.
	* infrequent but valid ngrams are sometimes very similar to very frequent ones

Mutations
	* insertion : additional item
		* duplication : correct item incorrectly number of times
	* deletion : item missing
	* transposition : correct items, incorrect order


"""

import logging

logger = logging.getLogger('spill-chick')
hdlr = logging.FileHandler('/var/tmp/spill-chick.log')
logger.addHandler(hdlr)
logger.setLevel(logging.DEBUG)

def handleError(self, record):
  raise
logging.Handler.handleError = handleError

from math import log
from operator import itemgetter
from itertools import takewhile, dropwhile, product, cycle, chain
from collections import defaultdict
import bz2, sys, re, os
import copy
from word import Words,NGram3BinWordCounter
from phon import Phon
from gram import Grams
from grambin import GramsBin
from doc import Doc
import similarity

logger.debug('sys.version=' + sys.version)

"""

sentence: "if it did the future would undoubtedly be changed"

"the future would" and "would undoubtedly be" have high scores,
but the connector, "future would undoubtedly", has zero.
we need to be aware that every valid 3-gram will not be in our database,
but that if the surrounding, overlapping ones are then it's probably ok

sugg       did the future 156
sugg            the future would 3162
sugg                future would undoubtedly 0
sugg                       would undoubtedly be 3111
sugg                             undoubtedly be changed 0

sugg    i did the 12284
sugg    it did the 4279
sugg    i did then 1654
sugg    it did then 690
sugg    i hid the 646
sugg       did the future 156
sugg       hid the future 38
sugg       aid the future 30
sugg            the future would 3162
sugg            the future world 2640
sugg            the future could 934
sugg                future wood and 0
sugg                future wood undoubtedly 0
sugg                future would and 0
sugg                future would undoubtedly 0
sugg                       would undoubtedly be 3111
sugg                       could undoubtedly be 152
sugg                             undoubtedly be changed 0

"""

import inspect
def lineno():
    """Returns the current line number in our program."""
    return inspect.currentframe().f_back.f_lineno

# TODO: modify levenshtein to weight score based on what has changed;
# - transpositions should count less than insertions/deletions
# - changes near the front of the word should count more than the end
# - for latin alphabets changes to vowels should count less than consonants
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
def rsort(l, **kw): return sorted(l, reverse=True, **kw)
def rsort1(l): return rsort(l, key=itemgetter(1))
def rsort2(l): return rsort(l, key=itemgetter(2))
def sort1(l): return sorted(l, key=itemgetter(1))
def sort2(l): return sorted(l, key=itemgetter(2))
def flatten(ll): return chain.from_iterable(ll)
def zip_longest(x, y, pad=None):
	x, y = list(x), list(y)
	lx, ly = len(x), len(y)
	if lx < ly:
		x += [pad] * (ly-lx)
	elif ly < lx:
		y += [pad] * (lx-ly)
	return zip(x, y)

def list2ngrams(l, size):
	"""
	split l into overlapping ngrams of size
	[x,y,z] -> [(x,y),(y,z)]
	"""
	if size >= len(l):
		return [tuple(l)]
	return [tuple(l[i:i+size]) for i in range(len(l)-size+1)]


class Chick:
	def __init__(self):
		# initialize all "global" data
		logger.debug('loading...')
		logger.debug('  corpus...')
		self.g = GramsBin(
			'/home/pizza/proj/spill-chick/data/corpus/google-ngrams/word.bin',
			'/home/pizza/proj/spill-chick/data/corpus/google-ngrams/ngram3.bin')
		self.w = Words(NGram3BinWordCounter(self.g.ng))
		logger.debug('  phon')
		self.p = Phon(self.w, self.g)
		logger.debug('done.')
		# sanity-check junk
		logger.debug('w.correct(naieve)=%s' % self.w.correct(u'naieve'))
		logger.debug('w.correct(refridgerator)=%s' % self.w.correct(u'refridgerator'))
		logger.debug('g.freqs(refridgerator)=%s' % self.g.freqs(u'refridgerator'))
		logger.debug('g.freqs(refrigerator)=%s' % self.g.freqs(u'refrigerator'))
		logger.debug('g.freq((didn))=%s' % self.g.freq((u'didn',)))
		logger.debug('g.freq((a,mistake))=%s' % self.g.freq((u'a',u'mistake')))
		logger.debug('g.freq((undoubtedly,be,changed))=%s' % self.g.freq((u'undoubtedly',u'be',u'changed')))
		logger.debug('g.freq((undoubtedly,be))=%s' % self.g.freq((u'undoubtedly',u'be')))
		logger.debug('g.freq((be,changed))=%s' % self.g.freq((u'be',u'changed')))
		logger.debug('g.freq((it,it,did))=%s' % self.g.freq((u'it',u'it',u'did')))
		logger.debug('g.freq((it,it))=%s' % self.g.freq((u'it',u'it')))
		logger.debug('g.freq((it,did))=%s' % self.g.freq((u'it',u'did')))

	def alternatives(self, d, t, freq):
		"""
		given tok ('token', line, index) return a list of possible alternative tokens.
		only return alternatives within the realm of popularity of the original token.
		"""
		edit = self.w.similar(t)
		phon = self.p.soundsLike(t, self.g)
		uniq = edit | set(phon)
		minpop = lambda x: round(log(self.g.freqs(x)+1))
		freqpop = round(log(freq+1))
		alt = [(x,levenshtein(t,x),minpop(x)) for x in uniq if minpop(x) >= freqpop]
		#alt = rsort2(alt)
		#alt = sort1(alt)
		alt2 = [x[0] for x in alt]
		return set(alt2)

	# FIXME: 'marques' -> marks!
	# FIXME: revue -> review?!
	def phonGuess(self, toks, minfreq):
		"""
		given a list of tokens search for a list of words with similar pronunciation having g.freq(x) > minfreq
		"""
		# create a phentic signature of the ngram
		phonsig = self.p.phraseSound(toks)
		logger.debug('phonsig=%s' % phonsig)
		#logger.debug('phonsig=',p.phraseSound(['all','intents','and','purposes']))

		phonwords = list(self.p.soundsToWords(phonsig))
		logger.debug('phonwords=%s' % phonwords)
		if phonwords == [[]]:
			phonpop = []
		else:
			# remove any words we've never seen
			phonwords2 = [[[w for w in p if self.g.freqs(w) > minfreq] for p in pw] for pw in phonwords]
			logger.debug('phonwords2=%s' % (phonwords2,))
			# remove any signatures that contain completely empty items after previous
			phonwords3 = [pw for pw in phonwords2 if all(pw)]
			logger.debug('phonwords3=%s' % phonwords3)
			phonwords4 = list(flatten([list(product(*pw)) for pw in phonwords3]))
			logger.debug('phonwords4=%s' % phonwords4)
			# look up ngram popularity, toss anything not more popular than original and sort
			phonpop = rsort1([(pw, self.g.freq(pw)) for pw in phonwords4])
			logger.debug('phonpop=%s' % phonpop)
			phonpop = list(takewhile(lambda x:x[1] > minfreq, phonpop))
			logger.debug('phonpop=%s' % phonpop)
		if phonpop == []:
			return []
		best = phonpop[0][0]
		return [[x] for x in best]

	@staticmethod
	def permjoin(l):
		"""
		given a list of strings, produce all permutations by joining two tokens together
		example [a,b,c] [[a,bc],[ab,c]]
		"""
		if len(l) < 2:
			yield l
		else:
			for suf in Chick.permjoin(l[1:]):
				yield [l[0]]+ suf
			for suf in Chick.permjoin(l[2:]):
				yield [l[0]+l[1]] + suf

	def do_suggest(self, target_ngram, target_freq, ctx, d, max_suggest=5):
		"""
		given an infrequent ngram from a document, attempt to calculate a more frequent one
		that is similar textually and/or phonetically but is more frequent
		"""

		toks = [t[0] for t in target_ngram]
		logger.debug('toks=%s' % (toks,))

		perms = []

		# permutations by phonic similarity
		phon = self.phonGuess(toks, target_freq)
		logger.debug('phonGuess(%s)=%s' % (toks, phon))
		if phon:
			perms += [[p[0] for p in phon]]

		# permutations via token joining
		perms += list(Chick.permjoin(toks))[1:]
		logger.debug('permjoin(%s)=%s' % (toks, perms))

		part = [tuple(j + [self.g.freq(tuple(j))]) for j in perms]

		# permutations via ngram3 partial matches
		part += self.g.ngram_like(toks)
		logger.debug('part=%s...' % part[:10])

		# calculate the closest, best ngram in part
		sim = similarity.sim_order_ngrampop(toks, part, self.p, self.g)
		logger.debug('sim=%s' % sim[:10])
		best = [(tuple(alt[:-1]),scores) for alt,scores in sim
			if scores[0] > 0][:max_suggest]
		logger.debug('*** BEST=%s' % best)
		return best

	# currently if we're replacing a series of tokens with a shorter one we pad with an empty string
	# this remove that string for lookup
	@staticmethod
	def canon(ng):
		if ng[-1] == '':
			return tuple(list(ng)[:-1])
		return ng

	def ngram_suggest(self, target_ngram, target_freq, d, max_suggest=1):
		"""
		we calculate ngram context and collect solutions for each context
		permutation containing the target. then merge these suggestions
		into a cohesive, best suggestion.
			c d e
		    a b c d e f g
		given ngram (c,d,e), calculate context and solve:
		[S(a,b,c), S(b,c,d), S(c,d,e), S(d,e,f), S(e,f,g)]
		"""

		logger.debug('target_ngram=%s' % (target_ngram,))
		tlen = len(target_ngram)

		context = list(d.ngram_context(target_ngram, tlen))
		logger.debug('context=%s' % (context,))
		ctoks = [c[0] for c in context]
		clen = len(context)

		logger.debug('tlen=%d clen=%d' % (tlen, clen))
		context_ngrams = list2ngrams(context, tlen)
		logger.debug('context_ngrams=%s' % (context_ngrams,))

		# gather suggestions for each ngram overlapping target_ngram
		sugg = [(ng, self.do_suggest(ng, self.g.freq([x[0] for x in ng]), context_ngrams, d))
			for ng in [target_ngram]] #context_ngrams]

		logger.debug('sugg=%s' % (sugg,))
		for ng,su in sugg:
			for s,sc in su:
				logger.debug('sugg %s%s %u' % \
					(' ' * ng[0][3], ' '.join(s), self.g.freq(Chick.canon(s))))

		"""
		previously we leaned heavily on ngram frequencies and the sums of them for
		evaluating suggestios in context.
		instead, we will focus specifically on making the smallest changes which have the
		largest improvements, and in trying to normalize a document, i.e.
		"filling in the gaps" of as many 0-freq ngrams as possible.
		"""

		def apply_suggest(ctx, ng, s):
			# replace 'ng' slice of 'ctx' with contents of text-only ngram 's'
			#logger.debug('apply_suggest(ctx=%s ng=%s s=%s)' % (ctx, ng, s))
			ctx = copy.copy(ctx)
			index = ctx.index(ng[0])
			repl = [(t, c[1], c[2], c[3]) for c,t in zip(ctx[index:], s)]
			ctx2 = ctx[:index] + repl + ctx[index+len(ng):]
			# store the side-by-side token difference for later
			def zip_ngpos_str(ng, s):
				# return must be (('orig', line, index, startpos), 'new')
				if len(ng) > len(s):
					return zip_longest(ng, s, '')
				elif len(ng) < len(s):
					pad = ('', ng[-1][1], ng[-1][2], ng[-1][3])
					return zip(list(ng)+[pad], s)
				return zip(ng, s)
			diff = list(zip_ngpos_str(ng, s))
			return (tuple(c[0] for c in ctx2 if c[0]), ng, s, diff)

		def realize_suggest(ctx, sugg):
			"""
			ctx is a list of positional ngrams; our 'target'
			sugg is a list of changesets.
			return map ctx x sugg
			"""
			#logger.debug('realize_suggest(ctx=%s sugg=%s)' % (ctx, sugg))
			return [[(apply_suggest(ctx, ng, s), diff)
				for s,diff in su]
					for ng,su in sugg]

		# merge suggestions based on what they change
		realized = realize_suggest(context, sugg)
		logger.debug('realized=%s' % (realized,))
		realdiff = {}
		for real in realized:
			for (rngtxt,rngpos,rsugg,rdiff),diff in real:
				rstr = ' '.join(rngtxt)
				# FIXME: trying to evaluate the change in its surrounding context;
				# there must be a better way to do it than this
				# FIXME: also, i need a way to handle token merges/deletes/insertions
				# that allows meaningful comparison of ngrams from before and after
				rsc = [similarity.sim_order_ngrampop(x, [tuple(list(y)+[self.g.freq(y)])], self.p, self.g)
					for x,y in zip(list2ngrams(ctoks, tlen),
						       list2ngrams(rngtxt, tlen))]


				# FIXME: overwriting diff
				diff = tuple(reduce(lambda x,y:map(sum,zip(x,y)),
					[r[0][1] for r in rsc]))
				
				logger.debug('real %s diff=%s rsc=%s' % (rstr, diff, rsc))
				# merge suggestions by their effects
				rddiff, rdngpos = realdiff.get(rstr, ((0,0,0),[]))
				rddiff = tuple(map(sum, zip(rddiff, diff)))
				rdngpos.append(rdiff)
				realdiff[rstr] = (rddiff, rdngpos)

		# sort the merged suggestions based on their combined score
		rdbest = sorted(realdiff.items(), key=lambda x:x[1][0], reverse=True)
		logger.debug('realdiff=%s' % (rdbest,))
		for rstr,(score,_) in rdbest:
			logger.debug('best %s %s' % (rstr, score))
		# extract the suggested changes and return them
		bestsuggs = [rd[1][1][0] for rd in rdbest[:max_suggest]]
		logger.debug('bestsuggs=%s' % (bestsuggs,))
		return bestsuggs

	def suggest(self, txt, max_suggest=1, skip=[]):
		"""
		given a string, run suggest() and apply the first suggestion
		"""
		logger.debug('Chick.suggest(txt=%s max_suggest=%s, skip=%s)' % (txt, max_suggest, skip))

		d = Doc(txt, self.w)
		logger.debug('doc=%s' % d)

		# start out like a regular spellchecker
		# address unknown tokens (ngram size 1) first
		ut = list(d.unknownToks())
		logger.debug('unknownToks=%s' % ut)
		# FIXME: this does not always work
		# example: 'passified' becomes 'assified' instead of 'pacified'
		# TODO: lots of mis-spellings are phonetic; we should attempt to "sound out"
		# unknown words, possibly by breaking them into pieces and trying to assemble the sound
		# from existing words
		utChanges = [(u, self.w.correct(u[0])) for u in ut]
		logger.debug('utChanges=%s' % utChanges)
		utChanges2 = list(filter(lambda x: x not in skip, utChanges))
		for ut in utChanges2:
			yield (ut[0], [[ut]])

		"""
		now the hard part.
		locate uncommon n-gram sequences which may indicate grammatical errors
		see if we can determine better replacements for them given their context
		"""

		# order n-grams by unpopularity
		ngsize = min(3, d.totalTokens())
		logger.debug('ngsize=%s d.totalTokens()=%s' % (ngsize, d.totalTokens()))
		logger.debug('ngram(1) freq=%s' % list(d.ngramfreq(self.g,1)))

		# locate the least-common ngrams
		# TODO: in some cases an ngram is unpopular, but overlapping ngrams on either side
		# are relatively popular.
		# is this useful in differentiating between uncommon but valid phrases from invalid ones?
		"""
sugg       did the future 156
sugg            the future would 3162
sugg                future would undoubtedly 0
sugg                       would undoubtedly be 3111
sugg                             undoubtedly be changed 0
		"""
		least_common = sort1(d.ngramfreq(self.g, ngsize))
		logger.debug('least_common=%s' % least_common[:20])
		least_common = list(dropwhile(lambda x: x[0] in skip, least_common))

		while least_common:
			target_ngram,target_freq = least_common.pop(0)
			best = self.ngram_suggest(target_ngram, target_freq, d, max_suggest)
			logger.debug('ngram_suggest=%s' % best)
			if not best or all(b[0][0] == b[1] for b in best[0]):
				continue
			yield (target_ngram, best)
			logger.debug('least_common=%s...' % least_common[:20])
			# FIXME: currently we're re-doing 99% of the same work each time
			# instead, do more work up-front and save it!
			break

	def correct(self, txt):
		"""
		given a string, identify the least-common n-gram not present in 'skip'
		and return a list of suggested replacements
		"""
		d = Doc(txt, self.w)
		changes = list(self.suggest(d, 1))
		while changes:
			logger.debug('changes=%s' % changes)
			changes2 = rsort1(changes)
			logger.debug('changes2=%s' % changes2)
			original,change = changes2[0]
			change = change[0]
			logger.debug('original=%s change=%s' % (original, change))
			d.applyChanges(change)
			logger.debug('change=%s after applyChanges d=%s' % (change, d))
			d = Doc(d, self.w)
			break # FIXME: loops forever
			changes = list(self.suggest(d, 1))
		res = str(d).decode('utf8')
		logger.debug('correct res=%s %s' % (type(res),res))
		return res

