#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections import defaultdict
try:
	from collections import Counter
except ImportError: # python 2.6?
	pass
import re, sys, traceback
import unittest
from operator import itemgetter

"""
Tokenizing regular expression
Group:
	letters
	numbers and any punctuation
		group things like dates, times, ip addresses, etc. into a single token
"""
TokRgxNL = re.compile('\d+(?:[^\w\s]+\d+)*|\w+|\n', re.UNICODE)
TokRgx = re.compile('\d+(?:[^\w\s]+\d+)*|\w+', re.UNICODE)
def tokenize(str):
	return re.findall(TokRgxNL, str.lower())
def tokenize_no_nl(str):
	return re.findall(TokRgx, str.lower())

class TokenizerTest(unittest.TestCase):
	def test_tokenize(self):
		Expect = [
			('', []),
			('a', ['a']),
			('A', ['a']),
			('Aa', ['aa']),
			('a b', ['a','b']),
		]
		for s,xp in Expect:
			res = tokenize(s)
			self.assertEqual(xp, res)

"""
store corpus ngrams
"""
class Grams:
	def __init__(self, w, ngmax=3, f=None):
		self.words = w
		self.ngmax = ngmax
		self.ngrams = ( # ngram id -> frequency
			None,
			None,
			Counter(),
			Counter(),
			Counter(),
		)
		if f:
			self.add(f)
	def freq(self, ng):
		#assert type(ng) == tuple
		if len(ng) == 1:
			return self.words.freq(ng[0])
		if ng == (): # FIXME: shouldn't need this
			return 0
		return self.ngrams[len(ng)][ng]
	def freqs(self, s):
		return self.words.freq(s)
	# given an iterable 'f', tokenize and produce a {word:id} mapping and ngram frequency count
	def add(self, f):
		if type(f) == list:
			contents = '\n'.join(f)
		else:
			try:
				contents = f.read(1 * 1024 * 1024) # FIXME
				if type(contents) == bytes:
					contents = contents.decode('utf8')
			except UnicodeDecodeError:
				t,v,tb = sys.exc_info()
				traceback.print_tb(tb)
		toks = tokenize_no_nl(contents)
		self.words.addl(toks)
		self.ngrams[2].update(zip(toks, toks[1:]))
		self.ngrams[3].update(zip(toks, toks[1:], toks[2:]))
		self.ngrams[4].update(zip(toks, toks[1:], toks[2:], toks[3:]))
		print('      ngrams[2] %8u' % len(self.ngrams[2]))
		print('      ngrams[3] %8u' % len(self.ngrams[3]))
		print('      ngrams[4] %8u' % len(self.ngrams[4]))

	"""
	given ngram of arity n, return all known ngrams containing n-1 matches;
	that is, where all but one of the tokens match.
	this is obviously O(n) and because it is exhaustive it is inefficient.
	consider eventually either moving ngrams into an sqlite database or a
	custom in-memory structure in C
	select x,y,z
	from ngram3
	where (x = 'x') + (y = 'y') + (z = 'z') = 2
	order by freq desc
	"""
	def ngram_like(self, ng):
		if len(ng) <= 1:
			return []
		assert len(ng) in (2,3)
		def uniq(s0,n):
			d = dict([(s[0][n],s[1]) for s in s0])
			s = sorted(d.items(), key=itemgetter(1), reverse=True)
			return [x for x,y in s]
		if len(ng) == 2:
			f = lambda x: x[0] == ng[0] or \
				      x[1] == ng[1]
		elif len(ng) == 3:
			f = lambda x:(x[0] == ng[0]) + \
				     (x[1] == ng[1]) + \
				     (x[2] == ng[2]) == 2
		lng = len(ng)
		s0 = filter(f, self.ngrams[lng].keys())
		s1 = [(k,self.ngrams[lng][k]) for k in s0]
		cnt = tuple(uniq(s1,n) for n in range(lng))
		return cnt

import pickle

if __name__ == '__main__':
	unittest.main()

