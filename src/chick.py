#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ex: set ts=8 noet:
# Copyright 2011 Ryan Flynn <parseerror+spill-chick@gmail.com>

"""
Word/grammar checking algorithm

Phon ✕ Word ✕ NGram ✕ Doc ✕ similarity

Facts
	* the corpus is not perfect. it contains errors.
	* not every valid ngram will exist in the corpus.
	* infrequent but valid ngrams are sometimes very similar to very frequent ones

Mutations
	* insertion : additional item
		* duplication : correct item incorrectly number of times
		* split	(its) -> (it,',s)
		* merge (miss,spelling) -> (misspelling)
	* deletion : item missing
	* transposition : correct items, incorrect order

TODO:
	* figure out how to handle apostrophes
	* pre-calculate token joining and merging

"""

from util import *

import logging

logger = logging.getLogger('spill-chick')
hdlr = logging.FileHandler('/var/tmp/spill-chick.log')
logger.addHandler(hdlr)
logger.setLevel(logging.DEBUG)

def handleError(self, record):
  raise
logging.Handler.handleError = handleError

from math import log
from itertools import takewhile, dropwhile, product, cycle, chain
from collections import defaultdict
import bz2, sys, re, os
import copy
from word import Words,NGram3BinWordCounter
from phon import Phon
from gram import Grams
from grambin import GramsBin
from doc import Doc

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
		# FIXME: using absolute paths is the easiest way to make us work from cmdline and invoked
		# in a web app. perhaps we could set up softlinks in /var/ to make this slightly more respectable.
		self.g = GramsBin(
			'/home/pizza/proj/spill-chick/data/corpus/google-ngrams/word.bin',
			'/home/pizza/proj/spill-chick/data/corpus/google-ngrams/ngram3.bin')
		self.w = Words(NGram3BinWordCounter(self.g.ng))
		logger.debug('  phon')
		self.p = Phon(self.w, self.g)
		logger.debug('done.')
		# sanity-check junk
		"""
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
		logger.debug('g.freq((hello,there,sir))=%s' % self.g.freq((u'hello',u'there',u'sir')))
		logger.debug('g.freq((hello,there))=%s' % self.g.freq((u'hello',u'there')))
		logger.debug('g.freq((hello,there,,))=%s' % self.g.freq((u'hello',u'there',u',')))
		logger.debug('g.freq((they,\',re))=%s' % self.g.freq((u'they',u"'",u're')))
		"""

	def phonGuess(self, toks, minfreq):
		"""
		given a list of tokens search for a list of words with similar pronunciation
		having g.freq(x) > minfreq
		"""
		# create a phonetic signature of the ngram
		phonsig = self.p.phraseSound(toks)
		logger.debug('phonsig=%s' % phonsig)
		phonwords = list(self.p.soundsToWords(phonsig))
		logger.debug('phonwords=%s' % (phonwords,))
		if phonwords == [[]]:
			phonpop = []
		else:
			# remove any words that do not meet the minimum frequency;
			# they cannot possibly be part of the answer
			phonwords2 = [[[w for w in p if self.g.freq(tuple(w)) > minfreq]
						for p in pw]
							for pw in phonwords]
			logger.debug('phonwords2 lengths=%s product=%u' % \
				(' '.join([str(len(p)) for p in phonwords2[0]]),
				 reduce(lambda x,y:x*y, [len(p) for p in phonwords2[0]])))
			if not all(phonwords2):
				return []
			#logger.debug('phonwords2=(%u)%s...' % (len(phonwords2), phonwords2[:10],))
			# remove any signatures that contain completely empty items after previous
			phonwords3 = phonwords2
			#logger.debug('phonwords3=(%u)%s...' % (len(phonwords3), phonwords3))
			# FIXME: product() function is handy in this case but is potentially hazardous.
			# we should force a limit to the length of any list passed to it to ensure
			# the avoidance of any pathological, memory-filling, swap-inducing behavior
			phonwords4 = list(flatten([list(product(*pw)) for pw in phonwords3]))
			logger.debug('phonwords4=(%u)%s...' % (len(phonwords4), phonwords4[:20]))
			# look up ngram popularity, toss anything not more popular than original and sort
			phonwordsx = [tuple(flatten(p)) for p in phonwords4]

			phonpop = rsort1([(pw, self.g.freq(pw, min)) for pw in phonwordsx])
			#logger.debug('phonpop=(%u)%s...' % (len(phonpop), phonpop[:10]))
			phonpop = list(takewhile(lambda x:x[1] > minfreq, phonpop))
			#logger.debug('phonpop=%s...' % (phonpop[:10],))
		if phonpop == []:
			return []
		best = phonpop[0][0]
		return [[x] for x in best]

	# FIXME: when we generate permutations, we must save the original and tokens must be in a list
	# this makes dealing with token split/merges handlable...
	# instead of [x,y,z] -> [x',y',z']
	# [x,y,z] -> [([x],[x']),([y],[y']),([z],[z'])]
	# 
	# instead of [x,y,z] -> [xy,z]
	# [x,y,z] -> [([x,y],[xy]),([z],[z'])]
	# 
	# this would make the doc diffing easier, but would it actually make
	# calculating the differences easier?
	# perhaps i should do this, and include an adiff total...

	@staticmethod
	def ngrampos_merge(x, y):
		return (x[0]+y[0], x[1], x[2], x[3])

	@staticmethod
	def permjoin(l, g):
		"""
		given a list of strings, produce permutations by joining two tokens together
		example [a,b,c,d] -> [[ab,c,d],[a,bc,d],[a,b,cd]
		"""
        	if len(l) > 1:
                	for i in range(len(l)-1):
                        	yield NGramDiff(l[:i],
						TokenDiff(l[i:i+2], [Chick.ngrampos_merge(l[i],l[i+1])], 1),
						l[i+2:], g)

	def do_suggest(self, target_ngram, target_freq, ctx, d, max_suggest=5):
		"""
		given an infrequent ngram from a document, attempt to calculate a more frequent one
		that is similar textually and/or phonetically but is more frequent
		"""

		target_ngram = list(target_ngram)
		part = []

		# permutations via token joining
		# expense: cheap, though rarely useful
		# TODO: smarter token joining; pre-calculate based on tokens
		part += list(Chick.permjoin(target_ngram, self.g))
		#logger.debug('permjoin(%s)=%s' % (target_ngram, part,))

		# calculate the closest, best ngram in part
		sim = sorted([NGramDiffScore(ngd, self.p) for ngd in part])
		for s in sim[:10]:
			logger.debug('sim %s' % (s,))

		#best = [(tuple(alt[:-1]),scores) for alt,scores in sim if scores[0] > 0][:max_suggest]
		best = list(takewhile(lambda s:s.score > 0, sim))[:max_suggest]
		for b in best:
			logger.debug('best %s' % (b,))
		return best

	def ngram_suggest(self, target_ngram, target_freq, d, max_suggest=1):
		"""
		we calculate ngram context and collect solutions for each context
		containing the target, then merge them into a cohesive, best suggestion.
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

		for ng,su in sugg:
			for s in su:
				logger.debug('sugg %s' % (s,))

		"""
		previously we leaned heavily on ngram frequencies and the sums of them for
		evaluating suggestios in context.
		instead, we will focus specifically on making the smallest changes which have the
		largest improvements, and in trying to normalize a document, i.e.
		"filling in the gaps" of as many 0-freq ngrams as possible.
		"""

		# merge suggestions based on what they change
		realdiff = {}
		for ng,su in sugg:
			for s in su:
				rstr = ' '.join(s.ngd.newtoks())
				if rstr in realdiff:
					realdiff[rstr] += s
				else:
					realdiff[rstr] = s
				logger.debug('real %s %s' % (rstr, realdiff[rstr]))

		# sort the merged suggestions based on their combined score
		rdbest = sorted(realdiff.items(), key=lambda x:x[1].score, reverse=True)

		for rstr,ngds in rdbest:
			logger.debug('best %s %s' % (rstr, ngds))

		return rdbest

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

		# gather all suggestions for all least_common ngrams
		suggestions = []
		while least_common:
			target_ngram,target_freq = least_common.pop(0)
			suggestions += self.ngram_suggest(target_ngram, target_freq, d, max_suggest)

		logger.debug('suggestions=%s' % (suggestions,))
		# calculate which suggestion makes the most difference
		bestsuggs = sorted(suggestions, key=lambda x:x[1].score, reverse=True)
		for bstxt,bss in bestsuggs:
			logger.debug('bestsugg %6.2f %7u %s' % \
				(bss.score, self.g.freq(bss.ngd.newtoks()), bstxt))
		if bestsuggs:
			bs = bestsuggs[0][1]
			logger.debug('%s' % (bs,))
			yield bs

		# TODO: now the trick is to a) associate these together based on target_ngram
		# to make them persist along with the document
		# and to recalculate them as necessary when a change is applied to the document that
		# affects anything they overlap

	def correct(self, txt):
		"""
		given a string, identify the least-common n-gram not present in 'skip'
		and return a list of suggested replacements
		"""
		d = Doc(txt, self.w)
		changes = list(self.suggest(d, 1))
		while changes:
			logger.debug('changes=%s' % changes)
			changes2 = rsort(changes, key=lambda x:x.score)
			logger.debug('changes2=%s' % changes2)
			change = [changes2[0].ngd]
			logger.debug('change=%s' % (change,))
			d.applyChanges(change)
			logger.debug('change=%s after applyChanges d=%s' % (change, d))
			d = Doc(d, self.w)
			break # FIXME: loops forever
			changes = list(self.suggest(d, 1))
		res = str(d).decode('utf8')
		logger.debug('correct res=%s %s' % (type(res),res))
		return res

