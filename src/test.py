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
	corpus = ['There it is!','I was right all along.',"I write their stuff? Nope I don't."]
	doc = ['Their it is.','Nope, I was write.']
	print('corpus=%s' % (corpus,))
	print('doc=%s' % (doc,))
	w = Words()
	p = Phon(w)
	g = Grams(w)
	g.add(corpus)
	print('g.ngrams=%s' % (g.ngrams,))
	d = Doc(doc, w)
	print('d.tok=%s' % (d.tok,))
	print('d.ngrams=%s' % (list(d.ngrams()),))
	print('d.unknownToks=%s' % (list(d.unknownToks()),))
	ng0 = list(d.checkNGrams(g))
	print('d.checkNGrams=%s' % (ng0,))
	# find a list of words that sounds like each word in each ngram
	ng0b = [tuple(p.soundsLike(x,g) for x in n) for n in ng0]
	print('p.soundsLike... %s' % (ng0b,))
	ng0c = [list(itertools.product(*n)) for n in ng0b]
	print('alternatives... %s' % (ng0c,))
	ng0d = [[(n, g.freq(n)) for n in l if g.freq(n) > 0] for l in ng0c]
	print('alternative popularity... %s' % (ng0d,))

