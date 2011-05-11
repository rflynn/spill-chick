#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from operator import itemgetter
import sys
from ngram3bin import ngram3bin
from ngramdiff import TokenDiff,NGramDiff,NGramDiffScore
from util import *

"""
Grams-interface to our binary ngram database
"""
class GramsBin:

	def __init__(self, wordpath, ngrampath):
		self.ng = ngram3bin(wordpath, ngrampath)

	def freq(self, ng, sum_=sum):
		#print 'freq()=',ng
		l = len(ng)
		if l > 1:
			ids = [ self.ng.word2id(w) for w in ng ]
			if l > 3:
				# chop up id list into ngram3-sized chunks
				smaller = [tuple(ids[i:i+3]) for i in range(len(ids)-3+1)]
				fr = sum_(self.ng.freq(*s) for s in smaller)
			else:
				fr = self.ng.freq(*ids)
			return fr
		else:
			return self.ng.wordfreq(ng[0])

	def freqs(self, s):
		#print('freq(s)=',s)
		return self.ng.wordfreq(s)

	def ngram_like(self, ng, ngfreq):
		"""
		given an ngram (x,y,z), return a list of ngrams sharing all but one element, i.e.
		(_,y,z)
		(x,_,z)
		(x,y,_)
		"""
		if len(ng) != 3:
			return []
		#print 'like()=',ng
		ids = tuple(map(self.ng.word2id, [n[0] for n in ng]))
		#print('like(ids)=',ids)
		like = self.ng.like(*ids)
		#print 'like(',ng,')=',like
		like2 = []
		for l in set(like):
			t,tfreq = tuple(map(self.ng.id2word, l[:3])), l[3]
			# calculate the single differing token and build an NGramDiff
			di = 0 if l[0] != ids[0] else 1 if l[1] != ids[1] else 2
			newtok = (t[di],) + ng[di][1:]
			damlev = damerau_levenshtein(ng[di][0], t[di])
			ngd = NGramDiff(ng[:di],
					TokenDiff(ng[di:di+1], [newtok], damlev),
					ng[di+1:], self, ngfreq, tfreq)
			like2.append(ngd)
		like3 = sorted(like2, reverse=True)
		return like2

