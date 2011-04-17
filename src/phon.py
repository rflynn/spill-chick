#!/usr/bin/env python3

"""
Handle phonetics; i.e. the way things sound
"""

import collections, re, sys, gzip, pickle, os, mmap
from word import Words

class Phon:
	def __init__(self, w):
		self.words = w
		self.word = collections.defaultdict(list)
		self.phon = collections.defaultdict(list)
		self.load()
	def load(self):
		path = '../data/cmudict/'
		file = 'cmudict.0.7a'
		# extract file if necessary
		if not os.path.exists(path+file):
			with open(path+file, 'wb') as dst:
				with gzip.open(path+file+'.gz', 'rb') as src:
					dst.write(src.read())
		with open(path+file, 'r') as f:
			for line in f:
				if line.startswith(';;;'):
					continue
				line = line.strip().lower()
				word, phon = line.split('  ')
				self.words.add(word)
				self.word[word].append(phon)
				self.phon[phon].append(word)

	"""
	return a list of words that sound like 'word', as long as they appear in ng
	"""
	def soundsLike(self, word, ng):
		l = []
		for w in self.word[word]:
			for x in self.phon[w]:
				fr = ng.freqs(x)
				if fr > 0:
					l.append((x,fr))
		return [w for w,fr in sorted(l, key=lambda x:x[1], reverse=True)]

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

