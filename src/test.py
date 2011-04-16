#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test our word/grammar algorithm
"""

from word import Words
from phon import Phon
from gram import Grams
from doc import Doc
from itertools import takewhile, product

def levenshtein(a,b):
    "Calculates the Levenshtein distance between a and b."
    n, m = len(a), len(b)
    if n > m:
        # Make sure n <= m, to use O(min(n,m)) space
        a,b = b,a
        n,m = m,n
        
    current = range(n+1)
    for i in range(1,m+1):
        previous, current = current, [i]+[0]*n
        for j in range(1,n+1):
            add, delete = previous[j]+1, current[j-1]+1
            change = previous[j-1]
            if a[j-1] != b[i-1]:
                change = change + 1
            current[j] = min(add, delete, change)
            
    return current[n]

if __name__ == '__main__':
	import bz2, sys, re

	def test():
		print('loading...',end=' ')
		sys.stdout.flush()
		w = Words()
		print('phon',end=' ')
		sys.stdout.flush()
		p = Phon(w)
		print('corpus',end=' ')
		sys.stdout.flush()
		g = Grams(w)
		g.add(open('../data/corpus/big.txt'))
		g.add(bz2.BZ2File('../data/corpus/dict-debian-american-english.bz2'))
		g.add(open('../data/corpus/idioms.txt', 'r'))
		print('done.')

		print('w.correct("naieve")=',w.correct('naieve'))

		Tests = []
		with open('../test/test.txt','r') as f:
			for l in f:
				if len(l) > 1 and l[0] != '#':
					before, after = l.strip().split(' : ')
					after = re.sub('\s*#.*', '', after.rstrip()) # replace comments
					Tests.append(([before],[after]))

		def alt_surround(g, d, tok):
			"""
			given a token's position, cross-reference its surrounding document tokens
			with the corpus
			"""
			sur = []
			s = d.surroundTok(tok)
			if s:
				t = tok[0]
				lt = len(t)*2
				tl = (len(t)+1)/2
				sk = (s[0][0],s[2][0])
				sur = [x for x in g.surround[sk].keys()
						if lt > len(x) >= tl and levenshtein(t,x) <= tl]
				"""
				sur = [y for x,y,z in g.ngrams[3].keys()
						if x == s[0][0] and z == s[2][0]
							and len(t)*2 > len(y) >= tl and levenshtein(t,y) <= tl]
				"""
			return sur

		def alternatives(w, p, g, d, tok):
			"given tok ('token', line, index) return a list of possible alternatives"
			t = tok[0]
			edit = w.correct(t)
			surr = alt_surround(g, d, tok)
			phon = p.soundsLike(t,g)
			return [edit] + list(s for s in set(surr + phon) if s != edit)

		passcnt = 0
		for str,exp in Tests:
			print('doc=', str)
			d = Doc(str, w)
			
			# order n-grams by unpopularity
			ngsize = min(2, d.totalTokens())
			ng0 = list(takewhile(lambda x: x[2] <= 10, # only pay attention to unknown ngrams
				sorted(d.ngramfreq(g, ngsize), key=lambda x:x[2])))
			ng0x = [x[0] for x in ng0]
			print('d.ngramfreq=', ng0[:20])

			# find potential alternative words
			# unique tokens we want to find alternatives for; don't repeat this potentially expensive process.
			#[item for sublist in l for item in sublist]
			alt = dict([(t,[]) for ng in ng0x for t in ng])
			print('alt=',alt)
			for t in alt.keys():
				alt[t] = alternatives(w,p,g,d,t)
			ng0b = [tuple(alt[t] for t in n) for n in ng0x]
			print('alternatives...', ng0b)
			ng0c = [list(product(*n)) for n in ng0b]
			print('alt ngrams...', ng0c)
			ng0d = [[(n, g.freq(n)) for n in l] for l in ng0c]
			ng0d = [sorted(x, key=lambda x:x[1], reverse=True) for x in ng0d]
			print('popular...', ng0d)

			# FIXME: firstly, order changes by popularity.
			# do not allow anything less-popular to overwrite anything more popular
			# also, we're replacing too much stuff, period. limit it.
			"""
			FIXME: ('think','so') has a popularity of 27 yet 'think' is overwritten by 'point', which is less-popular
doc= ['a think so']
d.ngramfreq= [((('a', 0, 0), ('think', 0, 2)), 0, 0.0), ((('think', 0, 2), ('so', 0, 8)), 27, 45.7)]
alt= {('a', 0, 0): [], ('think', 0, 2): [], ('so', 0, 8): []}
alternatives... [(['a'], ['think', 'point']), (['think', 'point'], ['so', 'sew', 'sow(1)', 'tso(1)'])]
alt ngrams... [[('a', 'think'), ('a', 'point')], [('think', 'so'), ('think', 'sew'), ('think', 'sow(1)'), ('think', 'tso(1)'), ('point', 'so'), ('point', 'sew'), ('point', 'sow(1)'), ('point', 'tso(1)')]]
popular... [[(('a', 'point'), 21), (('a', 'think'), 0)], [(('think', 'so'), 27), (('point', 'so'), 1), (('think', 'sew'), 0), (('think', 'sow(1)'), 0), (('think', 'tso(1)'), 0), (('point', 'sew'), 0), (('point', 'sow(1)'), 0), (('point', 'tso(1)'), 0)]]
proposedChanges... [((('a', 0, 0), ('think', 0, 2)), [(('a', 'point'), 21), (('a', 'think'), 0)]), ((('think', 0, 2), ('so', 0, 8)), [(('think', 'so'), 27), (('point', 'so'), 1), (('think', 'sew'), 0), (('think', 'sow(1)'), 0), (('think', 'tso(1)'), 0), (('point', 'sew'), 0), (('point', 'sow(1)'), 0), (('point', 'tso(1)'), 0)])]
mergedChanges= [(('think', 0, 2), 'point')]
['a point so']
			"""

			# present our potential revisions
			proposedChanges = list(zip(ng0x, ng0d))
			print('proposedChanges...', proposedChanges)
			def merge_changes(changes):
				revs = []
				# isolate only the actual changes
				for c in changes:
					src,dstl = c
					dst = dstl[0][0]
					for s,d in zip(src,dst):
						if s[0] != d and (s,d) not in revs:
							revs.append((s,d))
				return revs

			mergedChanges = merge_changes(proposedChanges)
			print('mergedChanges=', mergedChanges)
			res = d.demoChanges(mergedChanges)
			print(res)
			passcnt += res == exp
			print('-----------','pass' if res == exp else 'fail','------------')
			#assert res == exp

			"""
			this part is EXPONENTIALLY expensive and should only be used for small (len()<=16) substrings
			where no decent solutions are found above
			"""
			"""
			merge overlapping ngrams. tokens are accompanied by positional data which guarentees uniqueness.
			allows us to address larger sections than we can handle by static ngrams alone.
			note: groupby() doesn't handle two-item keys
			"""
			"""
			import algo
			def merge_posngrams(ngrams):
				if ngrams == []:
					return []
				m = [list(ngrams[0])]
				for ng in ngrams[1:]:
					if ng[0] == m[-1][-1]:
						m[-1].append(ng[-1])
					else:
						m.append(list(ng))
				return list(map(tuple, m))
			merged = list(merge_posngrams([n[0] for n in ng0x]))
			print('merged ngrams=',merged)
			def weight(tok, freq):
				factor = 1 + len(tok)
				return round(freq.get(tok,0) * factor, 1)
			# FIXME: only run this on unidentified tokens or truly mangled stuff, don't feed actual words in here
			# FIXME: this should only be a last resort if we are unable to generate any decent suggestions otherwise
			# given the merged unpopular ngrams try to find more popular combinations via merging/splitting
			for m in merged:
				toks = [n[0] for n in m]
				print('toks=',toks)
				if sum(map(len, toks)) <= 8:
					s = list(algo.splits(toks, w.frq))
					print('s=',s[:1000])
					js0 = s
					js1 = [(toks, sum([weight(t, w.frq) for t in toks])) for toks in js0]
					js2 = sorted(js1, key=lambda x:x[1], reverse=True)
					print('js=',js2[:5])
				else:
					print('too long for exhaustive')
			"""

		print('Tests %u/%u passed.' % (passcnt, len(Tests)))

	from sys import argv
	if len(argv) > 1 and argv[1] == '--profile':
		import cProfile, pstats
		cProfile.run('test()', 'test.prof')
		st = pstats.Stats('test.prof')
		st.sort_stats('time')
		st.print_stats()
	else:
		test()
	

