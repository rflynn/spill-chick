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
collection of parsed text data
"""
class Grams:
	def __init__(self, w, f=None):
		self.words = w
		self.ngrams = defaultdict(int) # ngram id -> frequency
		if f:
			self.add(f)
	def ngramfreq(self, ng):
		return self.ngrams[ng]
	# given an iterable 'f', tokenize and produce a {word:id} mapping and ngram frequency count
	def add(self, f, ngsize=2):
		leftover = []
		try:
			for line in f:
				tok = tokenize(line)
				self.words.addl(tok)
				ids = leftover + tok #[self.words.id(t) for t in tok]
				# ngram frequency
				for i in range(0, len(ids)-ngsize+1):
					ng = tuple(ids[i:i+ngsize])
					self.ngrams[ng] += 1
				leftover = ids[-ngsize:]
		except UnicodeDecodeError:
			t,v,tb = sys.exc_info()
			traceback.print_tb(tb)

import pickle

if __name__ == '__main__':
	f = ['a b c','d e f']
	g = Grams(f)
	print(g)

	#print([tuple(id2w[id] for id in ng) for ng in ngram_match('the', w2id, ngrams)[:100]])

