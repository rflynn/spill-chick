#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ex: set ts=8 noet:
# Copyright 2011 Ryan Flynn <parseerror+spill-chick@gmail.com>

"""
Word/grammar checking algorithm

Phon ✕ Word ✕ NGramDiff ✕ Doc

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
from ngramdiff import TokenDiff,NGramDiff,NGramDiffScore

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

	# FIXME: soundsToWords is expensive and should only be run as a last resort
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

	"""
	return a list of ngrampos permutations where each token has been replaced by a word with
	similar pronunciation, and g.freqs(word) > minfreq
	"""
	def permphon(self, ngrampos, minfreq):
		perms = []
		for i in range(len(ngrampos)):
			prefix = ngrampos[:i]
			suffix = ngrampos[i+1:]
			tokpos = ngrampos[i]
			tok = tokpos[0]
			sounds = self.p.word[tok]
			if not sounds:
				continue
			#logger.debug('tok=%s sounds=%s' % (tok, sounds))
			for sound in sounds:
				soundslikes = self.p.phon[sound]
				#logger.debug('tok=%s soundslikes=%s' % (tok, soundslikes))
				for soundslike in soundslikes:
					if len(soundslike) > 1:
						continue
					soundslike = soundslike[0]
					if soundslike == tok:
						continue
					#logger.debug('soundslike %s -> %s' % (tok, soundslike))
					if self.g.freqs(soundslike) <= minfreq:
						continue
					newtok = (soundslike,) + tokpos[1:]
					damlev = damerau_levenshtein(tok, soundslike)
					td = TokenDiff([tokpos], [newtok], damlev)
					perms.append(NGramDiff(prefix, td, suffix, self.g, soundalike=True))
		return perms

	@staticmethod
	def ngrampos_merge(x, y):
		return (x[0]+y[0], x[1], x[2], x[3])

	def permjoin(self, l, minfreq):
		"""
		given a list of strings, produce permutations by joining two tokens together
		example [a,b,c,d] -> [[ab,c,d],[a,bc,d],[a,b,cd]
		"""
		perms = []
		if len(l) > 1:
			for i in range(len(l)-1):
				joined = Chick.ngrampos_merge(l[i],l[i+1])
				if self.g.freqs(joined[0]) > minfreq:
					td = TokenDiff(l[i:i+2], [joined], 1)
					ngd = NGramDiff(l[:i], td, l[i+2:], self.g)
					perms.append(ngd)
		return perms

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
		part += self.permjoin(target_ngram, target_freq)
		#logger.debug('permjoin(%s)=%s' % (target_ngram, part,))

		part += self.permphon(target_ngram, target_freq)

		part += self.g.ngram_like(target_ngram, target_freq)

		logger.debug('part after ngram_like=%s...' % (part[:30],))

		# calculate the closest, best ngram in part
		sim = sorted([NGramDiffScore(ngd, self.p) for ngd in part])
		for s in sim[:10]:
			logger.debug('sim %4.1f %2u %u %6u %6u %s' % \
				(s.score, s.ediff, s.sl, s.ngd.oldfreq, s.ngd.newfreq, ' '.join(s.ngd.newtoks())))

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
		rdbest = sorted(realdiff.values(), key=lambda x:x.score, reverse=True)

		for ngds in rdbest:
			logger.debug('best %s' % (ngds,))

		return rdbest

	def suggest(self, txt, max_suggest=1, skip=[]):
		"""
		given a string, run suggest() and apply the first suggestion
		"""
		logger.debug('Chick.suggest(txt=%s max_suggest=%s, skip=%s)' % (txt, max_suggest, skip))

		d = Doc(txt, self.w)
		logger.debug('doc=%s' % d)

		"""

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
		# filter ngrams containing numeric tokens, they generate too many poor suggestions
		least_common = list(filter(
					lambda ng: not any(re.match('^\d+$', n[0][0], re.U) for n in ng[0]),
					least_common))

		# FIXME: limit to reduce work
		least_common = least_common[:max(20, len(least_common)/2)]

		# gather all suggestions for all least_common ngrams
		suggestions = []
		for target_ngram,target_freq in least_common:
			suggs = self.ngram_suggest(target_ngram, target_freq, d, max_suggest)
			if suggs:
				suggestions.append(suggs)

		if not suggestions:
			"""
			"""
			ut = list(d.unknownToks())
			logger.debug('unknownToks=%s' % ut)
			utChanges = [(u, (self.w.correct(u[0]), u[1], u[2], u[3])) for u in ut]
			logger.debug('utChanges=%s' % utChanges)
			utChanges2 = list(filter(lambda x: x not in skip, utChanges))
			for old,new in utChanges2:
				td = TokenDiff([old], [new], damerau_levenshtein(old[0], new[0]))
				ngd = NGramDiff([], td, [], self.g)
				ngds = NGramDiffScore(ngd, None, 1)
				suggestions.append([ngds])

		logger.debug('------------')
		logger.debug('suggestions=%s' % (suggestions,))
		suggs = filter(lambda x:x and x[0].ngd.newfreq != x[0].ngd.oldfreq, suggestions)
		logger.debug('suggs=%s' % (suggs,))
		# sort suggestions by their score, highest first
		bestsuggs = rsort(suggs, key=lambda x: x[0].score)
		# sort suggestions by how much
		bestsuggs = rsort(bestsuggs, key=lambda x: x[0].improve_pct())
		for bs in bestsuggs:
			for bss in bs:
				logger.debug('bestsugg %6.2f %2u %2u %7u %6.0f%% %s' % \
					(bss.score, bss.ediff, bss.ngd.diff.damlev,
					 bss.ngd.newfreq, bss.improve_pct(), ' '.join(bss.ngd.newtoks())))

		for bs in bestsuggs:
			logger.debug('> bs=%s' % (bs,))
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
		for ch in changes:
			logger.debug('ch=%s' % (ch,))
			change = [ch[0].ngd]
			logger.debug('change=%s' % (change,))
			d.applyChanges(change)
			logger.debug('change=%s after applyChanges d=%s' % (change, d))
			d = Doc(d, self.w)
			break # FIXME: loops forever
			changes = list(self.suggest(d, 1))
		res = str(d).decode('utf8')
		logger.debug('correct res=%s %s' % (type(res),res))
		return res

