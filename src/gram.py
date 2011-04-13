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
TokRgx = re.compile('\d+(?:[^\w\s]+\d+)*|\w+')
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
	def __init__(self, w, ngmax=2, f=None):
		self.words = w
		self.ngmax = ngmax
		self.ngrams = (defaultdict(int), defaultdict(int)) # ngram id -> frequency
		if f:
			self.add(f)
	def freq(self, ng):
		if type(ng) == str:
			return self.ngrams[0][ng]
		return self.ngrams[len(ng)-1][ng]
	# given an iterable 'f', tokenize and produce a {word:id} mapping and ngram frequency count
	def add(self, f):
		leftover = []
		try:
			for line in f:
				if type(line) == bytes:
					line = line.decode('utf8')
				tok = tokenize(line)
				self.words.addl(tok)
				# ngram frequency
				# len=1
				for t in tok:
					self.ngrams[0][t] += 1
				# len=2
				for i in range(0, len(tok)-1):
					ng = tuple(tok[i:i+2])
					self.ngrams[1][ng] += 1
		except UnicodeDecodeError:
			t,v,tb = sys.exc_info()
			traceback.print_tb(tb)

import pickle

if __name__ == '__main__':
	unittest.main()

