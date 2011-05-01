#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from operator import itemgetter
import sys
from ngram3bin import ngram3bin

"""
Grams-interface to our binary ngram database
"""
class GramsBin:

	def __init__(self, wordpath, ngrampath):
		self.ng = ngram3bin(wordpath, ngrampath)

	def freq(self, ng):
		#print('freq()=',ng)
		l = len(ng)
		if l > 1:
			ids = [ self.ng.word2id(w) for w in ng ]
			if l > 3:
				# chop up id list into ngram3-sized chunks
				smaller = [tuple(ids[i:i+3]) for i in range(len(ids)-3+1)]
				fr = sum(self.ng.freq(*s) for s in smaller)
			else:
				fr = self.ng.freq(*ids)
			return fr
		else:
			return self.ng.wordfreq(ng[0])

	def freqs(self, s):
		#print('freq(s)=',s)
		return self.ng.wordfreq(s)

	def ngram_like(self, ng):
		if len(ng) != 3:
			return []
		#print('like()=',ng)
		ids = tuple(map(self.ng.word2id, ng))
		#print('like(ids)=',ids)
		like = self.ng.like(*ids)
		#print('like(',ng,')=',like)
		like2 = sorted(set([
			(self.ng.id2word(t[0]),
			 self.ng.id2word(t[1]),
			 self.ng.id2word(t[2]), t[3])
				for t in like]), key=itemgetter(3), reverse=True)
		return like2

