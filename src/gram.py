#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections import defaultdict
import re, sys, traceback
import unittest

"""
Tokenizing regular expression
Group:
	letters
	numbers and any punctuation
		group things like dates, times, ip addresses, etc. into a single token
"""
TokRgx = re.compile('\d+(?:[^\w\s]+\d+)*|\w+|\n')
def tokenize(str):
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
			defaultdict(int),
			defaultdict(int),
		)
		self.surround = defaultdict(dict) # (x,y,z) : [(x,z)] : [y]
		if f:
			self.add(f)
	def freq(self, ng):
		if type(ng) == str:
			return self.words.freq(ng)
		if len(ng) == 1:
			return self.words.freq(ng[0])
		return self.ngrams[len(ng)][ng]
	# given an iterable 'f', tokenize and produce a {word:id} mapping and ngram frequency count
	def add(self, f):
		if type(f) == list:
			contents = '\n'.join(f)
		else:
			contents = f.read()
			if type(contents) == bytes:
				contents = contents.decode('utf8')
		try:
			toks = tokenize(contents)
			self.words.addl(toks)
			for x,y in zip(toks, toks[1:]):
				self.ngrams[2][(x,y)] += 1
			for x,y,z in zip(toks, toks[1:], toks[2:]):
				self.ngrams[3][(x,y,z)] += 1
				try:
					self.surround[(x,z)][y] += 1
				except KeyError:
					self.surround[(x,z)][y] = 1
			#for x,y,z,zz in zip(toks, toks[1:], toks[2:], toks[3:]):
				#self.ngrams[(x,y,z,zz)] += 1
		except UnicodeDecodeError:
			t,v,tb = sys.exc_info()
			traceback.print_tb(tb)

import pickle

if __name__ == '__main__':
	unittest.main()

