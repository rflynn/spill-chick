#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Doc represents a document being checked against existing Grams
"""

import gram

"""
Tokenize document contents; each token is associated with positional data
"""
class Doc:
	def __init__(self, f, w):
		self.f = f
		self.words = w
		self.tok = []
		for lcnt,line in enumerate(f):
			line = line.lower()
			toks = gram.tokenize(line)
			tpos = 0
			ll = []
			for t in toks:
				tpos = line.index(t, tpos)
				ll.append((t, lcnt, tpos))
			self.tok += ll

	def unknownToks(self):
		for t in self.tok:
			if self.words.id(t[0]) == 0:
				yield t

	def ngrams(self, size=2):
		for i in range(0, len(self.tok)+1-size):
			ngram = tuple(t[0] for t in self.tok[i:i+size])
			yield ngram

	def checkNGrams(self, g, size=2):
		for ng in self.ngrams(size):
			if g.ngramfreq(ng) == 0:
				yield ng

if __name__ == '__main__':
	d = Doc(['a b c','d e f'])
	print(d.tok)

