#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections import defaultdict

"""
Word statistics
"""
class Words:
	def __init__(self, f=None):
		self.w2id = dict() # word -> id
		self.id2w = dict() # id -> word
		self.idfreq = defaultdict(int) # word id -> frequency
	def add(self, word):
		self.addl([word])
		return self.w2id[word]
	def addl(self, words):
		for word in words:
			if word not in self.w2id:
				id = len(self.w2id)+1
				self.w2id[word] = id
				self.id2w[id] = word
				self.idfreq[id] = 1
			else:
				self.idfreq[self.w2id[word]] += 1
	# return token id or 0 if it does not exist
	def id(self, tok):
		try:
			return self.w2id[tok]
		except KeyError:
			return 0
	def word(self, id):
		try:
			return self.id2w[id]
		except KeyError:
			return None

if __name__ == '__main__':
	pass

