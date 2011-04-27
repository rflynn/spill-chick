#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ex: set ts=8 noet:
# Copyright 2011 Ryan Flynn <parseerror+spill-chick@gmail.com>

"""
Test our word/grammar algorithm
"""

import logging
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
import algo

logger = logging.getLogger('spill-chick')
hdlr = logging.FileHandler('/var/tmp/spill-chick.log')
logger.addHandler(hdlr)
logger.setLevel(logging.DEBUG)

def handleError(self, record):
  raise
logging.Handler.handleError = handleError

#logger.basicConfig(file='chick.log')#stream=sys.stderr)

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
def rsort1(l):
	return rsort(l, key=itemgetter(1))
def rsort2(l):
	return rsort(l, key=itemgetter(2))
def sort1(l):
	return sorted(l, key=itemgetter(1))
def sort2(l):
	return sorted(l, key=itemgetter(2))
def flatten(ll):
	return chain.from_iterable(ll)
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
		self.p = Phon(self.w)
		logger.debug('done.')
		# sanity-check junk
		# note: string/unicode fucks python2
		"""
	logger.debug('w.correct(naieve)=',w.correct(u'naieve'))
	logger.debug('g.freq((didn))=',g.freq(('didn',)))
	logger.debug('g.freq((a,mistake))=',g.freq(('a','mistake')))
	logger.debug('g.freq((undoubtedly,be,changed))=',g.freq(('undoubtedly','be','changed')))
	logger.debug('g.freq((undoubtedly,be))=',g.freq(('undoubtedly','be')))
	logger.debug('g.freq((be,changed))=',g.freq(('be','changed')))
	logger.debug('g.freq((it,it,did))=',g.freq(('it','it','did')))
	logger.debug('g.freq((it,it))=',g.freq(('it','it')))
	logger.debug('g.freq((it,did))=',g.freq(('it','did')))
		"""

	def alternatives(self, d, t, freq):
		"""
		given tok ('token', line, index) return a list of possible alternative tokens.
		only return alternatives that within the realm of popularity of the original token.
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

	# FIXME: this is much too slow and yields little benefit
	# figure out a much cheaper way of doing a subset of this
	def inter_token(self, toks, freq):
		"""
		given a list of tokens, disregard token borders and attempt to find alternate valid
		token lists
		"""
		if sum(map(len, toks)) > 12:
			logger.debug('too long for exhaustive')
			return []
		s = list(algo.splits(toks, freq, self.g))
		return s

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
			logger.debug('phonwords2=', phonwords2)
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
	def intersect_alt_tok(part, alt, toks):
		"""
		part are partial matches, i.e. for (x,y,z) they're (x,y,_)
		alt[tok] is a set of close words to tok
		for each token in toks we find intersections between alt[tok] and part[n]
		"""
		part_pop = [set() for _ in toks]
		for pa in part:
			for t,(i,p) in zip(toks, enumerate(pa[:-1])):
				if p in alt[t]:
					part_pop[i].add(p)
				#elif levenshtein(p, t) < min(3, len(t)/2):
				#	part_pop[i].add(p)
		return [list(s) for s in part_pop]

	def popular_alts(self, alt, toks):
		"""
		produce ngrams consisting of token alternatives meeting a certain frequency
		sometimes someone really botches the spelling and comes up with a garbage term
		"""
		freqlog = lambda fr: round(log(fr+1))
		freq = [(t, freqlog(self.g.freqs(t)), alt[t]) for t in toks]
		freq2 = [[a for a in al if freqlog(self.g.freqs(a))+1 >= fr]
			for k,fr,al in freq]
		logger.debug('popular_alts=%s' % freq2)
		return freq2

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

	def do_suggest(self, target_ngram, freq, ctx, d):
		"""
		given an infrequent ngram from a document, attempt to calculate a more frequent one
		that is similar textually and/or phonetically but is more frequent
		"""

		toks = [t[0] for t in target_ngram]
		logger.debug('toks=%s' % toks)

		# find potential alternative tokens for the tokens in the unpopular ngrams
		alt = dict([(t, self.alternatives(d,t,freq)) for t in toks])
		logger.debug('alt=%s' % alt)

		# list all ngrams containing partial matches for our ngram
		part = self.g.ngram_like(toks)
		logger.debug('part=%s...' % part[:50])

		"""
		part & alt
		part is based on our corpus and alt based on token similarity.
		an intersection between the two means we've found as good a candidate as we'll get.
		"""
		part_pop = Chick.intersect_alt_tok(part, alt, toks)
		logger.debug('part_pop=%s' % part_pop)

		if not any(part_pop):
			part_pop = self.popular_alts(alt, toks)

		"""
		toks = [t[0] for t in target_ngram]
		logger.debug('toks=',toks)
		the code above is our best shot for repairing simple transpositions, etc.
		however, if any of the tokens do not intersect part & alt...
		for more mangled stuff we try a variety of techniques,
		falling through to more desperate options should each fail
		"""
		if not all(part_pop) or part_pop == [[t] for t in toks]:
			didPhon = True
			phong = self.phonGuess(toks, freq)
			logger.debug('phong=%s' % phong)
			if phong != []:
				part_pop = phong
			else:
				#intertok = inter_token(toks, w.frq, g)
				#logger.debug('intertok=', intertok)
				#if intertok != []:
					#part_pop = [[x] for x in intertok[0]]
				#else:
				for i in range(len(part_pop)):
					if part_pop[i] == []:
						dec = [(t, self.g.freqs(t), levenshtein(t, toks[i]))
							for t in alt[toks[i]] if t != toks[i]]
						part_pop[i] = [x[0] for x in sort2(dec)][:3]
			# add tokens back into part_pop
			logger.debug("part_pop before...=%s" % part_pop)
			part_pop = [p + ([] if t in p else [t])
					for t,p in zip(toks,part_pop)]
			logger.debug("part_pop'=%s" % part_pop)
		else:
			didPhon = False
		partial = list(product(*part_pop))
		partial += list(Chick.permjoin(toks))[1:]
		logger.debug('partial=%s' % partial)
		best = partial
		# NOTE: i really want izip_longest() but it's not available!
		if best and len(best[0]) < len(target_ngram):
			best[0] = tuple(list(best[0]) + [''])
		best = [x[0] for x in rsort1([(b, self.g.freq(Chick.canon(b))) for b in best])]
		logger.debug('%s best=%s' % (lineno(), best))
		# if our best suggestions are no more frequent than what we started with, give up!
		"""
		if best and g.freq(canon(best[0])) <= freq:
			best = []
		logger.debug('best=',best)
		"""
		if len(best) > 5:
			best = best[:5]
		return best

	# currently if we're replacing a series of tokens with a shorter one we pad with an empty string
	# this remove that string for lookup
	@staticmethod
	def canon(ng):
		if ng[-1] == '':
			return tuple(list(ng)[:-1])
		return ng

	def ngram_suggest(self, target_ngram, freq, d):
		"""
		we calculate ngram context and collect solutions for each context
		permutation containing the target. then merge these suggestions
		into a cohesive, best suggestion.
			c d e
		    a b c d e f g
		given ngram (c,d,e), calculate context and solve:
		[S(a,b,c), S(b,c,d), S(c,d,e), S(d,e,f), S(e,f,g)]
		"""

		logger.debug('target_ngram=' + str(target_ngram))
		tlen = len(target_ngram)

		context = list(d.ngram_context(target_ngram, tlen))
		logger.debug('context=' + str(context))
		clen = len(context)

		logger.debug('tlen=%d clen=%d' % (tlen, clen))
		#context_ngrams = [tuple(context[i:i+tlen]) for i in range(clen-tlen+1)]
		context_ngrams = list2ngrams(context, tlen)
		logger.debug('context_ngrams=%s' % context_ngrams)

		# gather suggestions for each ngram overlapping target_ngram
		sugg = [(ng, self.do_suggest(ng, self.g.freq([x[0] for x in ng]), context_ngrams, d))
			for ng in context_ngrams]

		logger.debug('sugg=%s' % sugg)
		for ng,su in sugg:
			for s in su:
				logger.debug('sugg %s%s %u' % (' ' * ng[0][3], ' '.join(s), self.g.freq(Chick.canon(s))))

		def apply_suggest(ctx, ng, s):
			# replace 'ng' slice of 'ctx' with contents of text-only ngram 's'
			logger.debug('apply_suggest(ctx=%s ng=%s s=%s)' % (ctx, ng, s))
			ctx = copy.copy(ctx)
			index = ctx.index(ng[0])
			ctx2 = ctx[:index] + \
				[(t, c[1], c[2], c[3]) for c,t in zip(ctx[index:], s)] + \
				ctx[index+len(ng):]
			#return (' '.join([c[0] for c in ctx2 if c[0]]), ng, s)
			return (tuple(c[0] for c in ctx2 if c[0]), ng, s)

		def realize_suggest(ctx, sugg):
			"""
			ctx is a list of positional ngrams; our 'target'
			sugg is a list of changesets.
			return map ctx x sugg
			"""
			return [[apply_suggest(ctx, ng, s) for s in su] for ng,su in sugg]

		# merge suggestions based on what they change
		realized = realize_suggest(context, sugg)
		logger.debug('realized=%s' % realized)

		realcnt = {}
		for real in realized:
			logger.debug('real=%s' % real)
			for sctx,ng,s in real:
				"""
				sum up the frequency of all ngrams in the realized result
				note: this is inefficient and should be above and intelligently merged
				"""
				fr = round(sum(map(self.g.freq, list2ngrams(sctx, tlen))) / len(sctx))
				# TODO: should we adjust 'fr' based on the minimum ngram frequency
				# or not?
				"""
				sctx is the realized string that this recommends
				keep track of the total frequency and also the number of suggestions
				number of suggestions is more important!
				"""
				try:
					r = realcnt[sctx]
					r = (r[0] + fr, r[1] + 1)
				except KeyError:
					r = (fr, 1)
				realcnt[sctx] = r
				logger.debug('sctx=<%s> fr=%u' % (sctx, fr))
		logger.debug('realcnt=%s' % realcnt)

		######################## FIXME: we should levenshtein-score suggestions from
		######################## alternatives(), but not from soundsLike(), since it makes
		######################## no sense to.

		######################## FIXME: also, changes from alternatives() should be scored
		######################## phonetically; the closer to the original the better

		"""
		now incorporate sound and levenshtein distance into our final candidates
		"""

		toks = tuple(t[0] for t in context)
		tokSound = ' '.join(self.p.phraseSound(toks))

		realcnt2 = {}
		for k,(kFreq,kCnt) in realcnt.items():
			if kFreq >= freq:
				# FIXME: too fragile. we want to be able to correct phonic mis-spellings
				# and for short phrases phonics is more important than score
				# but for longer things valuing sound-a-likes means we recommend
				# "wood" for "would" in rediculous situations
				kSound = ' '.join(self.p.phraseSound(k)) if len(k) < 4 else ''
				kLev = sum(levenshtein(t,k) for t,k in zip(toks,k))
				# TODO: can't decide whether kCnt or kFreq should be first;
				# kCnt 21/32
				# kFreq 20/32
				# kFreq / kCnt 20/32
				realcnt2[k] = (int(kSound == tokSound and k != toks), kFreq/kCnt, kCnt, kFreq, kLev)

		logger.debug("realcnt2'={}",realcnt2)

		"""
		remove any suggestions that do not have suggestions for each ngram
		that is, for suggestions ngram length 3, proposed solution a b c d e
		must contain suggestions supporting (a,b,c),(b,c,d),(c,d,e)
		a missing link means the suggestion is not a good one
		this prevents popular single words from overpowering less-common ones
		where they do not actually occur.
		this is the real power of ngram context

		FIXME: hmmm not so sure actually. given "the dog was dense", expecting "the fog was dense"
		we get a much higher score for "the dog was", even though "fog was dense" outscores "dog was dense".
		the fact that people talk about their dogs more than fog kills us here.
		"""
		reallink = rsort1(realcnt2.items())
		logger.debug('reallink=%s' % reallink)
		reallink2 = list(takewhile(lambda x:x[1] > 0, reallink))
		logger.debug('reallink2=%s' % reallink2)

		if not reallink2:
			return [] # got nothin'

		# calculate the most-recommended change
		realbest = reallink2[0]
		logger.debug('realbest=' + str(realbest))

		"""
		if we didn't substantially improve the freq then don't recommend it.
		prevent popular phrases from overriding similar but less frequent ones
		"""
		if realbest[1][2] <= freq ** 2:
			return []

		"""
		now that we've realized our suggestions and chosen a solution to recommend,
		we need to work backwards to figure out which part of 'sugg' produces this
		answer and return it
		"""
		# list of lists of suggestions that produce realbest
		bestsugg = [[r[2] for r in real if r[0] == realbest[0]] for real in realized]
		# choose the first non-empty list
		bestsugg2 = list(filter(None, bestsugg))[0][0]
		logger.debug('bestsugg2=' + str(bestsugg2))
		# now we know which ngram the change belongs to, figure out which it applies to
		bestorig = [s[0] for s in sugg if bestsugg2 in s[1]][0]
		logger.debug('bestorig=' + str(bestorig))

		"""
		return the suggestion that realizes the best change,
		and the ngrampos it originates from
		"""

		ret = list(zip_longest(bestorig, bestsugg2, ''))
		logger.debug('ret=%s' % ret)
		# isolate the changes down to the word
		# FIXME: how to handle deleted/inserted words?
		ret2 = [(r[0], r[1]) for r in ret if r[0][0] != r[1]]
		logger.debug('ret2=%s' % ret2)
		return ret2

	def suggest(self, txt, max_suggest=1, skip=[]):
		"""
		given a string, run suggest() and apply the first suggestion
		"""
		logger.debug('Chick.suggest(txt=%s max_suggest=%s, skip=%s)' % (txt, max_suggest, skip))

		d = Doc(txt, self.w)
		logger.debug('doc=%s' % d.tok)

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
		utChanges2 = list(dropwhile(lambda x: x in skip, utChanges))
		if utChanges2:
			yield utChanges2
		#d.applyChanges(utChanges)

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
		least_common = list(takewhile(lambda x:x[1] <= 1, least_common))

		while least_common:
			target_ngram,target_freq = least_common.pop(0)
			best = self.ngram_suggest(target_ngram, target_freq, d)
			best2 = best[:max_suggest]
			logger.debug('ngram_suggest=%s' % best2)
			yield best2
			"""
			if best:
				# present our potential revisions
				proposedChanges = best
				logger.debug('proposedChanges...%s' % proposedChanges)
				res = d.demoChanges(proposedChanges)
				logger.debug(res)
				d.applyChanges(proposedChanges)
			"""
			# FIXME: save progress
			#least_common = sort1(d.ngramfreq(self.g, ngsize))
			#least_common = []
			logger.debug('least_common=%s...' % least_common[:20])

	def correct(self, txt):
		"""
		given a string, identify the least-common n-gram not present in 'skip'
		and return a list of suggested replacements
		"""
		d = Doc(txt, self.w)
		changes = list(self.suggest(d, 1))
		while changes:
			logger.debug('changes=%s' % changes)
			change = changes[0]
			d.applyChanges(change)
			logger.debug('change=%s after applyChanges d=%s' % (change, d))
			d = Doc(d, self.w)
			changes = list(self.suggest(d, 1))
		res = str(d).decode('utf8')
		logger.debug('correct res=%s %s' % (type(res),res))
		return res

