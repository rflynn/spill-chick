#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Handle phonetics; i.e. the way things sound
"""

import collections, re, sys, gzip, pickle, os, mmap
from word import Words
from gram import tokenize

class Phon:
	def __init__(self, w, g):
		self.words = w
		self.word = collections.defaultdict(list)
		self.phon = collections.defaultdict(list)
		self.load(g)
	def load(self, g):
		path ='/home/pizza/proj/spill-chick/data/cmudict/cmudict.0.7a'
		# extract file if necessary
		if not os.path.exists(path):
			with open(path, 'wb') as dst:
				with gzip.open(path+'.gz', 'rb') as src:
					dst.write(src.read())
		redigits = re.compile('\d+')
		multichar = re.compile('(\S)(\S+)')
		# TODO: loading this ~130,000 line dictionary in python represents the majority
		# of the program's initialization time. move it over to C.
		with open(path, 'r') as f:
			for line in f:
				if line.startswith(';;;'):
					continue
				line = line.decode('utf8')
				line = line.strip().lower()
				word, phon = line.split('  ')
				"""
				skip any words that do not appear in our ngrams.
				this makes a significant difference when trying to reconstruct phrases
				phonetically; small decreases in terms have large decreases in products.
				note: you may think that every word in a dictionary would appear
				at least once in a large corpus, but we truncate corpus n-grams at a
				certain minimum frequency which may exclude very obscure words from ultimately
				appearing at all.
				"""

				# TODO: what i really should do is eliminate all words that appear less
				# than some statistically significant time; the vast majority of the
				# phonetic phrases I currently try are filled with short obscure words
				# and are a complete waste
				# FIXME: instead of hard-coding frequency, calculate statistically
				if word.count("'") == 0 and g.freqs(word) < 500:
					continue
				"""
				implement a very rough phonic fuzzy-matching
				phonic codes consist of a list of sounds such as:
					REVIEW  R IY2 V Y UW1
				we simplify this to
					REVIEW  R I V Y U
				this allows words with close but imperfectly sounding matches to
				be identified. for example:
					REVUE   R IH0 V Y UW1
					REVIEW  R IY2 V Y UW1
				is close but not a perfect match. after regex:
					REVUE  R I V Y U
					REVIEW R I V Y U
				"""
				phon = re.sub(multichar, '\\1', phon)
				# now merge leading vowels except 'o' and 'u'
				if len(phon) > 1:
					phon = re.sub('^[aei]', '*', phon)
				self.words.add(word)
				self.word[word].append(phon)
				toks = tokenize(word)
				self.phon[phon].append(toks)

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

	def phraseSound(self, toks):
		"""
		given a list of tokens produce a normalize list of their component sound
		an unknown token generates None
		TODO: ideally we would be able to "guess" the sound of unknown words.
		this would be a huge improvement!
		given 'waisting' we should be able to break it into 'waist' 'ing'
		"""
		def head(l):
			return l[0] if l else None
		s = [head(self.word.get(t,[''])) for t in toks]
		#print('phraseSound(',toks,')=',s)
		if not all(s):
			return []
		# nuke numbers, join into one string
		t = ' '.join([re.sub('\d+', '', x) for x in s])
		# nuke consecutive duplicate sounds
		u = re.sub('(\S+) \\1 ', '\\1 ', t)
		v = u.split()
		#print('phraseSound2=',v)
		return v

	def soundsToWords(self, snd):
		if snd == []:
			yield []
		for j in range(1, len(snd)+1):
			t = ' '.join(snd[:j])
			words = self.phon.get(t)
			if words:
				for s in self.soundsToWords(snd[j:]):
					yield [words] + s

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

	P.phraseSound(['making','mistake'])
	P.phraseSound(['may','king','mist','ache'])
	x = P.phraseSound(['making','miss','steak'])
	from itertools import product
	for f in P.soundsToWords(x):
		print(f)
		#print(list(product(*f)))

