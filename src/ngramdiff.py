#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
token and ngram comparison
"""

from math import sqrt,log
from util import damerau_levenshtein

class TokenDiff:
	"""
	represent the modification of zero or more 'old' (original) tokens and their
	'new' (proposed) replacement. solves the problem of tracking inter-token changes.
	change: TokenDiff([tok], [tok'])
	insert: TokenDiff([], [tok'])
	delete: TokenDiff([tok], [])
	split:  TokenDiff([tok], [tok',tok'])
	merge:  TokenDiff([tok,tok], [tok'])
	"""
	def __init__(self, old, new, damlev):
		self.old = list(old)
		self.new = list(new)
		self.damlev = damlev # Damerau-Levenshtein distance
	def oldtoks(self): return [t[0] for t in self.old]
	def newtoks(self): return [t[0] for t in self.new]
	def __str__(self):
		return 'TokenDiff((%s,%s))' % (self.old, self.new)
	def __repr__(self):
		return str(self)
	def __eq__(self, other):
		return self.old == other.old and \
		       self.new == other.new

class NGramDiff:
	"""
	represent a list of tokens that contain a single change, represented by a TokenDiff.
	alternative, think of it as an acyclic directed graph with a single branch and merge
	conceptually:
		  prefix   diff    suffix
		O---O---O---O---O---O---O
	                 \     /
		          `-O-'
	"""
	def __init__(self, prefix, diff, suffix, g, oldfreq=None, newfreq=None, soundalike=False):
		self.prefix = list(prefix)
		self.diff = diff
		self.suffix = list(suffix)
		self.oldfreq = g.freq(self.oldtoks()) if oldfreq is None else oldfreq
		self.newfreq = g.freq(self.newtoks()) if newfreq is None else newfreq
		self.soundalike = soundalike
	def old(self): return self.prefix + self.diff.old + self.suffix
	def new(self): return self.prefix + self.diff.new + self.suffix
	def oldtoks(self): return [t[0] for t in self.old()]
	def newtoks(self): return [t[0] for t in self.new()]
	def __repr__(self):
		return str(self)
	def __str__(self):
		return 'NGramDiff(%s,%s,%s)' % (self.prefix, self.diff, self.suffix)
	def __eq__(self, other):
		return self.diff == other.diff and \
		       self.prefix == other.prefix and \
		       self.suffix == other.suffix
	def __lt__(self, other):
		return other.newfreq < self.newfreq

class NGramDiffScore:
	# based on our logarithmic scoring below
	DECENT_SCORE = 3.0
	GOOD_SCORE = 5.0
	"""
	decorate an NGramDiff obj with scoring
	"""
	def __init__(self, ngd, p, score=None):
		self.ngd = ngd
		self.sl = ngd.diff.new and ngd.diff.old and ngd.diff.new[0][0][0] == ngd.diff.old[0][0][0]
		if score:
			self.score = score
			self.ediff = score
		else:
			self.score = self.calc_score(ngd, p)
	def calc_score(self, ngd, p):
		ediff = self.similarity(ngd, p)
		self.ediff = ediff
		if ngd.newfreq == 0:
			score = -float('inf')
		else:
			score = ((log(max(1, ngd.newfreq)) -
				 (2 + ediff + (not self.sl))) + (ngd.diff.damlev - ediff))
		return score
	def __str__(self):
		return 'NGramDiffScore(score=%4.1f ngd=%s)' % (self.score, self.ngd)
	def __repr__(self):
		return str(self)
	def __eq__(self, other):
		return other.score == self.score
	def __lt__(self, other):
		return other.score < self.score
	def __add__(self, other):
		return NGramDiffScore(self.ngd, None, self.score + other.score)
	@staticmethod
	def overlap(s1, s2):
		"""
		given a list of sound()s, count the number that do not match
			 1  2  3  4  5  6
			'T AH0 M AA1 R OW2'
			'T UW1 M'
			 =     =
			 6 - 2 = 4
		"""
		mlen = max(len(s1), len(s2))
		neq = sum(map(lambda x: x[0] != x[1], zip(s1, s2)))
		return mlen - neq
	def similarity(self, ngd, p):
		"""
		return tuple (effective difference, absolute distance)
		given a string x, calculate a similarity distance for y [0, +inf).
		smaller means more similar. the goal is to identify promising
		alternatives for a given token within a document; we need to consider
		the wide range of possible errors that may have been made
		"""
		if ngd.soundalike:
			return 0
		x = ' '.join(ngd.diff.oldtoks())
		y = ' '.join(ngd.diff.newtoks())
		# tokens identical
		if x == y:
			return 0
		damlev = ngd.diff.damlev
		sx,sy = p.phraseSound([x]),p.phraseSound([y])
		if sx == sy and sx:
			# sound the same, e.g. there/their. consider these equal.
			return damlev
		# otherwise, calculate phonic/edit difference
		return max(damlev,
			   min(NGramDiffScore.overlap(sx, sy),
			       abs(len(x)-len(y))))

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

	pass

