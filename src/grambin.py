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
		self.ng = ngram3bin(wordpath,ngrampath)

	def freq(self, ng):
		#print('freq()=',ng)
		l = len(ng)
		if l == 3:
			ids = ( self.ng.word2id(ng[0]),
				self.ng.word2id(ng[1]),
				self.ng.word2id(ng[2]) )
			fr = self.ng.freq(*ids)
			print('freq(',ng,')=',fr)
			return fr
		elif l == 1:
			return self.ng.wordfreq(ng[0])
		#print('freq len=',l)
		return 0

	def freqs(self, s):
		#print('freq(s)=',s)
		return self.ng.wordfreq(s)

	def ngram_like(self, ng):
		if len(ng) <= 1:
			return []
		#print('like()=',ng)
		ids = tuple(map(self.ng.word2id, ng))
		#print('like(ids)=',ids)
		like = self.ng.like(*ids)
		#print('like(',ng,')=',like)
		like2 = sorted([
			(self.ng.id2word(t[0]),
			 self.ng.id2word(t[1]),
			 self.ng.id2word(t[2]), t[3])
				for t in like], key=itemgetter(3), reverse=True)
		return like2

