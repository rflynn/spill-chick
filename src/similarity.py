#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
we need a good way to compare the similarity of two tokens
incorporate:
	edit-distance
		consonants/vowels
	sound
	popularity/frequency
"""

from math import sqrt,log

# based on our logarithmic scoring below
DECENT_SCORE = 5.0
GOOD_SCORE = 10.0

def damerau_levenshtein(seq1, seq2):
    """Calculate the Damerau-Levenshtein distance between sequences.

    This distance is the number of additions, deletions, substitutions,
    and transpositions needed to transform the first sequence into the
    second. Although generally used with strings, any sequences of
    comparable objects will work.

    Transpositions are exchanges of *consecutive* characters; all other
    operations are self-explanatory.

    This implementation is O(N*M) time and O(M) space, for N and M the
    lengths of the two sequences.

    >>> dameraulevenshtein('ba', 'abc')
    2
    >>> dameraulevenshtein('fee', 'deed')
    2

    It works with arbitrary sequences too:
    >>> dameraulevenshtein('abcd', ['b', 'a', 'c', 'd', 'e'])
    2
    """
    # codesnippet:D0DE4716-B6E6-4161-9219-2903BF8F547F
    # Conceptually, this is based on a len(seq1) + 1 * len(seq2) + 1 matrix.
    # However, only the current and two previous rows are needed at once,
    # so we only store those.
    oneago = None
    thisrow = range(1, len(seq2) + 1) + [0]
    for x in xrange(len(seq1)):
        # Python lists wrap around for negative indices, so put the
        # leftmost column at the *end* of the list. This matches with
        # the zero-indexed strings and saves extra calculation.
        twoago, oneago, thisrow = oneago, thisrow, [0] * len(seq2) + [x + 1]
        for y in xrange(len(seq2)):
            delcost = oneago[y] + 1
            addcost = thisrow[y - 1] + 1
            subcost = oneago[y - 1] + (seq1[x] != seq2[y])
            thisrow[y] = min(delcost, addcost, subcost)
            # This block deals with transpositions
            if (x > 0 and y > 0 and seq1[x] == seq2[y - 1] and seq1[x-1] == seq2[y] and seq1[x] != seq2[y]):
                thisrow[y] = min(thisrow[y], twoago[y - 2] + 1)
    return thisrow[len(seq2) - 1]

def overlap(s1, s2):
	"""
	given a list of sound()s, count the number that do not match
		 1  2  3  4  5  6
		'T AH0 M AA1 R OW2'
		'T UW1 M'
                 =     =
		6 - 2 = 4
	"""
	mlen = max(len(s1), len(s2))
	neq = sum(map(lambda x: x[0] != x[1], zip(s1, s2)))
	return mlen - neq

def similarity(x, y, p):
	"""
	given a string x, calculate a similarity distance for y [0, +inf).
	smaller means more similar. the goal is to identify promising
	alternatives for a given token within a document; we need to consider
	the wide range of possible errors that may have been made
	"""
	# tokens identical
	if x == y:
		return 0
	sx,sy = p.phraseSound([x]),p.phraseSound([y])
	if sx == sy and sx:
		# sound the same, e.g. there/their. consider these equal.
		return 0
	# otherwise, calculate phonic/edit difference
	return max(damerau_levenshtein(x, y),
		   min(overlap(sx, sy),
		       abs(len(x)-len(y))))

def sim_score(x, y, p, g):
	"""
	given strings x and y, produce tuple of similarity scores using different means
	"""
	return (similarity(x, y, p),
	        int(x[0] == y[0]), # starts with same letter
	        g.freqs(y)) # frequency; never a good first option but separates the wheat from the chaff

def sim_order(tok, alts, p, g):
	"""
	given a token and a list of alternative tokens, score and sort alts
	in descending order of similarity to tok
	"""
	sim1 = [(alt, sim_score(tok, alt, p, g)) for alt in alts]
	sim2 = sorted(sim1, key=lambda x:x[1][1], reverse=True)
	sim3 = sorted(sim2, key=lambda x:x[1][2], reverse=True)
	sim4 = sorted(sim3, key=lambda x:x[1][0])
	return sim4

def sim_score_ngram(ng, alt, p, g):
	"""
	given ngrams ng and alt calculate a sum-total of differences for each token
	"""
	sim,sl = 0,0
	if len(alt) == len(ng)+1:
		for n,al in zip(ng,alt[:-1]):
			# need a better way of handling token split/merge, for now just
			# skip diff
			sim += similarity(n, al, p)
			sl += int(n and al and n[0] != al[0]) # starts with same letter
	return (
		# scoring metric favors small difference over high frequency
		log(max(1,alt[-1])) - (2+sim+sl),
		# these are not directly used, but available for inspection later
		sim,	# how much i changed
		alt[-1]) # frequency

def sim_order_ngrampop(ng, alts, p, g):
	#print 'ng=',ng,'alts=',alts[:10],'...'
	sim1 = [(alt, sim_score_ngram(ng, alt, p, g)) for alt in alts]
	sim2 = sorted(sim1, key=lambda x:x[1][2], reverse=True)
	sim3 = sorted(sim2, key=lambda x:x[1][1], reverse=True)
	sim4 = sorted(sim3, key=lambda x:x[1][0], reverse=True)
	#print 'sim_order_ngrampop=',sim4[:50],'...'
	return sim4

if __name__ == '__main__':
	import sys
	sys.path.append('..')
	from grambin import GramsBin
	from word import Words,NGram3BinWordCounter
	from phon import Phon
	import logging

	logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
	logging.debug('loading...')
	g = GramsBin(
		'/home/pizza/proj/spill-chick/data/corpus/google-ngrams/word.bin',
		'/home/pizza/proj/spill-chick/data/corpus/google-ngrams/ngram3.bin')
	w = Words(NGram3BinWordCounter(g.ng))
	p = Phon(w,g)
	logging.debug('loaded.')

	# test single tokens
	for tok,alts in [	
		('bomb', ['bob','comb','tom','tomb','womb','ohm','boo','bbbb','unrelated','i']),
		('apart', ['part','par','party','partly','aaaaa','unrelated','i']),
		('eatin', ['eden','gethsemane']), ]:
		# for some reason max(len(s),...) blows up when s is str but not unicode, wtf
		tok,alts = unicode(tok),map(unicode,alts)
		sim = sim_order(tok, alts, p, g)
		print('%s %s' % (tok, [(str(alt),score) for alt,score in sim]))

	# test full ngrams
	for ng,alts in [	
		(('bridge','the','gas'),
		 [('in','the','gap', 5077L), ('through','the','gap', 4397L), ('bridging','the','gap', 3547L), ('fill','the','gap', 3072L), ('close','the','gap', 2388L), ('to','the','gap', 2044L), ('and','the','gap', 1969L), ('that','the','gap', 1859L), ('closing','the','gap', 1672L), ('into','the','gap', 1649L), ('at','the','gap', 1316L), ('across','the','gap', 1156L), ('up','the','gap', 1122L), ('bridges','the','gap', 842L), ('is','the','gap', 832L), ('closed','the','gap', 820L),('bridge','the','gap', 6241L)])
		]:
		# for some reason max(len(s),...) blows up when s is str but not unicode, wtf
		def ed(ng,f): return tuple(map(f,ng[:-1]) + [ng[-1]])
		def enc(ng): return ed(ng,unicode)
		def dec(ng): return ed(ng,str)
		ng,alts = map(unicode,ng), map(enc, alts)
		sim = sim_order_ngrampop(ng, alts, p, g)
		print('%s %s' % (ng, [(dec(s),sc) for (s,sc) in sim]))

