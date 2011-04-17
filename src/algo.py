#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Goal: maximize self-consistency of a corpus of documents
calculate frequency of all ngrams 1..n
sort ngrams on freq:asc, size:asc
for ng in ngrams below some threshold:
	calculate feasible permutations for ng
		note: focus only on one area at a time, as the resulting change will modify the rest of the document
		for tok in ng:
			calculate list of permutations: spelling edits, pronunciation
		account for merging/splitting of tokens, etc.
"""

import re
from math import log,sqrt
from collections import defaultdict

def tokenize(text): return re.findall('[a-z]+', text.lower()) 

Freq = {
	'i':1, 'know':1, 'right':1,
	'fuck':1,
	'conduct':2, 'research':2, 'search':2, 'con':1, 'duct':1,
	'hi':3, 'there':2, 'hit':2, 'here':2, 'how':3, 'are':3, 'you':3,
	'ho':1,
	'a':3, 'them':2, 'anathema':1,
}

"""
given a list of tokens, yield all possible permutations of joining two or more tokens together
i.e. joins([a,b,c,d]) -> [[a,b,c,d],[a,b,cd],[a,bc,d],[ab,c,d],[a,bcd],[abc,d],[abcd]]

AHA, i realize now that i'm simply trying to list sum permutations:
i.e. joins([1,1,1,1]) -> [[1,1,1,1],[1,1,2],[1,2,1],[2,1,1],[1,3],[3,1],[4]]
complexity: 2**(len(toks)-1)
"""
def joins(toks):
	if len(toks) < 2:
		yield toks
	else:
		for i in range(len(toks)):
			for j in range(i+1, len(toks)-i+1):
				pref = toks[:i] + [''.join(toks[i:i+j])]
				for suf in joins(toks[i+j:]):
					yield pref + suf

"""
find first substring str[x:y] where exists freq[str[x:y]] where y >= l
return tuple (prefix before substring, the substring, the rest of the string)
"""
def nextword(str, freq, l=1):
	for i in range(len(str)):
		for j in range(i+l, min(i+18, len(str))):
			if freq.get(str[i:j]):
				return (str[:i], str[i:j], str[j:])
	return (str,'','')

"""
given a string of one or more valid substring words, yield a list of permutations
freq is a dict() of all recognized words in str
"""
def spl(str, freq):
	if len(str) < 2:
		yield [str]
	else:
		i = 0
		while i < len(str):
			pref,word,suf = nextword(str, freq, i)
			#print((i,str,pref,word,suf))
			if not word:
				#if i == 0 or freq.get(pref):
					# on subsequent loops we accumulate garbage non-word-suffixes
				yield [pref]
				break
			else:
				w = []
				if pref: w.append(pref)
				w.append(word)
				for sufx in spl(suf, freq):
					if sufx:
						yield w + sufx
				i += len(word) + 1

"""
given a list of tokens, yield all possible permutations via splitting
"""
def splits(toks, freq):
	score = dict()
	# list all possible substrings that are known words
	str = ''.join(toks)
	for i in range(len(str)+1):
		for j in range(i+1, len(str)+1):
			w = str[i:j]
			sc = freq.get(w, 0)
			if sc > 0:
				score[w] = sc
	# find all permutations that contain at least one word
	for x in spl(str, score):
		yield tuple(x)

def weight(tok):
	factor = 1 + len(tok)
	return round(Freq.get(tok,0) * factor, 1)

def correct(str):
	toks = tokenize(str)
	"""
	j = frozenset(tuple(t) for t in joins(toks))
	print('j=',j)
	"""
	s = list(splits(toks, Freq))
	print('s=',s[:4])
	js0 = list(s)# + list(j)
	js1 = [(k, sum(map(weight, k))) for k in js0]
	js2 = sorted(js1, key=lambda x:x[1], reverse=True)
	print('js=',js2[:5])
	guess = str
	if js2 != []:
		guess,gscore = js2[0]
		oscore = sum(map(weight, toks))
		print('gscore=',gscore,'oscore=',oscore)
		if gscore > oscore * 2: # FIXME: there is no good way to do this
			guess = ' '.join(guess)
		else:
			guess = str
	return guess

if __name__ == '__main__':
	Tests = [
		'iknowright : i know right',
		'f u c k y o u : fuck you',
		'xxxhowareyouxxx : xxx how are you xxx',
		'con duct re search : conduct research',
		'hitherehowareyou : hi there how are you',
		'hithe re : hi there',
		'anathema : anathema' # unlikely but valid word
	]
	passcnt = 0
	for t in Tests:
		str,exp = t.strip().split(' : ')
		print(str)
		res = correct(str)
		if res == exp:
			passcnt += 1
		else:
			print('*** FAIL: %s -> %s (%s)' % (str,res,exp))
	print('Tests %u/%u.' % (passcnt, len(Tests)))

