#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections import defaultdict
import re
import sys
import traceback

TokRgx = re.compile("\w+(?:'\w+)?")
def tokenize(str):
	return re.findall(TokRgx, str.lower())

"""
store corpus ngrams
"""
class Grams:
	def __init__(self, w, ngmax=2, f=None):
		self.words = w
		self.ngmax = ngmax
		self.ngrams = [defaultdict(int), defaultdict(int)] # ngram id -> frequency
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
				tok = tokenize(line)
				self.words.addl(tok)
				ids = tok #[self.words.id(t) for t in tok]
				# ngram frequency
				# len=1
				for i in ids:
					self.ngrams[0][i] += 1
				# len=2
				for i in range(0, len(ids)-1):
					ng = tuple(ids[i:i+2])
					self.ngrams[1][ng] += 1
		except UnicodeDecodeError:
			t,v,tb = sys.exc_info()
			traceback.print_tb(tb)

import pickle

if __name__ == '__main__':
	f = ['a b c','d e f']
	g = Grams(f)
	print(g)

	#print([tuple(id2w[id] for id in ng) for ng in ngram_match('the', w2id, ngrams)[:100]])

