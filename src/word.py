#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import collections

Alphabet = 'abcdefghijklmnopqrstuvwxyz'

def edits1(word):
	splits     = [(word[:i], word[i:]) for i in range(len(word) + 1)]
	deletes    = [a + b[1:] for a, b in splits if b]
	transposes = [a + b[1] + b[0] + b[2:] for a, b in splits if len(b)>1]
	replaces   = [a + c + b[1:] for a, b in splits for c in Alphabet if b]
	inserts    = [a + c + b     for a, b in splits for c in Alphabet]
	return set(deletes + transposes + replaces + inserts)

"""
imitate the interface of a Counter() that Words is expecting
so we can use ngram3bin without him knowing
"""
class NGram3BinWordCounter:
	def __init__(self, ng):
		self.ng = ng
	def __contains__(self, word):
		# foo in me
		return self.ng.word2id(word) != 0
	def get(self, word, default=0):
		try:
			return self.ng.wordfreq(word)
		except (ValueError, TypeError):
			raise KeyError
	def __getitem__(self, word):
		# me[key]
		if type(word) == int:
			raise IndexError
		try:
			return self.ng.wordfreq(word)
		except:
			raise KeyError
	def __setitem__(self, word, val):
		# me[key] = val
		pass
	def update(self, wordfreqlist):
		pass

"""
Word statistics
"""
class Words:

	def __init__(self, frq=collections.Counter()):
		self.frq = frq

	def add(self, word):
		self.frq[word] += 1

	def addl(self, words):
		self.frq.update(words)

	def freq(self, word):
		return self.frq[word]

	def known_edits2(self, word):
		return set(e2 for e1 in edits1(word) for e2 in edits1(e1) if e2 in self.frq)

	def known(self, words): return set(w for w in words if w in self.frq)

	# FIXME: douce -> douse
	# FIXME: iv -> ivy
	def correct(self, word):
		candidates = self.known([word]) or self.known(edits1(word)) or self.known_edits2(word) or [word]
		return max(candidates, key=self.frq.get)

	# FIXME: bid -> big
	# FIXME: hungreh -> hungry
	def similar(self, word):
		e = self.known(edits1(word))
		if len(word) > 2:
			e |= self.known_edits2(word)
		return e

	@staticmethod
	def signature(word):
		"sorted list of ('letter',frequency) for all letters in word"
		return [(c,len(list(l))) for c,l in groupby(sorted(word))]

if __name__ == '__main__':
	pass

