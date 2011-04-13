#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from word import Words
from phon import Phon
from gram import Grams
from doc import Doc

Expect = [
	('their it is', 'there it is'),
	('nope, i was write', 'nope, i was right'),
]

import itertools

if __name__ == '__main__':
	import bz2
	corpus = ['There it is!','I was right all along.',"I write their stuff? Nope I don't."]
	corpus = bz2.BZ2File('../data/corpus/big.txt.bz2')
	doc = ['Their it is.','','Nope, I was write, Xxyz!']
	print('corpus=%s' % (corpus,))
	print('doc=%s' % (doc,))
	w = Words()
	p = Phon(w)
	g = Grams(w)
	g.add(corpus)
	print('g.ngrams=%s' % \
		([sorted(list(n.items()), key=lambda x:x[1], reverse=True)[:50]
			for n in g.ngrams],))
	d = Doc(doc, w)
	print('d.tok=', d.tok)
	print('d.ngrams=', list(d.ngrams())[:100])
	print('d.unknownToks=', list(d.unknownToks()))
	ng0 = list(d.checkNGrams(g))
	print('d.checkNGrams=', ng0,)
	# find a list of words that sounds like each word in each ngram
	ng0b = [tuple(p.soundsLike(t[0],g) for t in n) for n in ng0]
	print('p.soundsLike...', ng0b)
	ng0c = [list(itertools.product(*n)) for n in ng0b]
	print('alternatives...', ng0c)
	ng0d = [[(n, g.freq(n)) for n in l if g.freq(n) > 0] for l in ng0c]
	proposedChanges = list(zip(ng0, ng0d))
	print('alternative popularity...', proposedChanges)
	print(doc)
	print(d.demoChanges(doc, proposedChanges))

