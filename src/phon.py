#!/usr/bin/env python3

import collections, re, sys
import gzip
from word import Words

class Phon:
	def __init__(self, w):
		self.words = w
		self.word = collections.defaultdict(list)
		self.phon = collections.defaultdict(list)
		with gzip.open('../data/cmudict/cmudict.0.7a.gz', 'rb') as f:
			for line in f:
				line = line.decode('utf8')
				if line.startswith(';;;'):
					continue
				line = line.strip().lower()
				word, phon = line.split('  ')
				w.add(word)
				self.word[word].append(phon)
				self.phon[phon].append(word)

	def soundsLike(self, word):
		l = []
		for w in self.word[word]:
			l += self.phon[w]
		return l

if __name__ == '__main__':

	def words(str):
		return re.findall('[a-z\']+', str.lower()) 

	def pron(wl, wd):
		print(' '.join([str(wd[w][0]) if w in wd else '<%s>' % (w,) for w in wl]))

	P = Phon(Words())
	for a in sys.argv[1:]:
		pron(words(a), P.W)

	print(P.word['there'])
	print(P.phon[P.word['there'][0]])

