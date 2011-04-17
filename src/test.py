#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ex: set ts=4 et:

"""
Test our word/grammar algorithm
"""

from math import log
from operator import itemgetter
from itertools import takewhile, product, cycle
from collections import defaultdict
from word import Words
from phon import Phon
from gram import Grams
from doc import Doc

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

    """
    this part is EXPONENTIALLY expensive and should only be used for small (len()<=16) substrings
    where no decent solutions are found above
    """
    """
    merge overlapping ngrams. tokens are accompanied by positional data which guarentees uniqueness.
    allows us to address larger sections than we can handle by static ngrams alone.
    note: groupby() doesn't handle two-item keys
    """
    import algo
    """
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
    """

    def inter_token(toks, freq, g):
        print('toks=',toks)
        if sum(map(len, toks)) <= 12:
            s = list(algo.splits(toks, freq, g))
            print('s[',len(s),']=',s[:1000])
            js0 = s
            js1 = [(toks, sum([freq.get(t,0) for t in toks])) for toks in js0]
            js2 = sorted(js1, key=lambda x:x[1], reverse=True)
            print('inter_token()=',js2[:5])
            return js2
        else:
            print('too long for exhaustive')
            return []

    def test():
        print('loading...')
        sys.stdout.flush()
        w = Words()
        print('  phon')
        sys.stdout.flush()
        p = Phon(w)
        print('  corpus...')
        sys.stdout.flush()
        g = Grams(w)
        for filename in ['big.txt','idioms.txt','dict-debian-american-english.bz2']:#,'wiki-titles-scrubbed.txt']:
            print('   ',filename)
            sys.stdout.flush()
            try:
                o = bz2.BZ2File if filename.endswith('.bz2') else open
                with o('../data/corpus/'+filename, 'r') as f:
                    g.add(f)
            except:
                pass
        print('done.')

        print('w.correct(naieve)=',w.correct('naieve'))
        print('g.freq((i,know))=',g.freq(('i','know')))


        # load test cases
        Tests = []
        with open('../test/test.txt','r') as f:
            for l in f:
                l = l.strip()
                if l == '#--end--':
                    break
                if len(l) > 1 and l[0] != '#':
                    before, after = l.strip().split(' : ')
                    after = re.sub('\s*#.*', '', after.rstrip()) # replace comments
                    Tests.append(([before],[after]))


        def alternatives(w, p, g, d, t):
            """
            given tok ('token', line, index) return a list of possible alternative tokens.
            only return alternatives that within the realm of popularity of the original token.
            """
            edit = w.similar(t)[:30]
            phon = p.soundsLike(t,g)
            uniq = set(edit + phon)
            minpop = lambda x: round(log(g.freqs(x)))
            alts = [(x,levenshtein(t,x),minpop(x)) for x in uniq if minpop(x) > 0]
            alts = sorted(alts, key=itemgetter(2), reverse=True)
            alts = sorted(alts, key=itemgetter(1))
            return alts

        alt_know = alternatives(w,p,g,None,'know')
        print('alt(know)=',alt_know)
        alt_now = alternatives(w,p,g,None,'now')
        print('alt(now)=',alt_now)
        #assert 'know' in alt_now

        passcnt = 0
        for str,exp in Tests:
            print('doc=', str)
            d = Doc(str, w)

            # start out like a regular spellchecker
            # address unknown tokens (ngram size 1) first
            ut = list(d.unknownToks())
            print('unknownToks=',ut)

            # now the hard part.
            # locate uncommon n-gram sequences which may indicate grammatical errors
            # see if we can determine better replacements for them given their context

            # order n-grams by unpopularity
            ngsize = min(3, d.totalTokens())
            while ngsize >= min(3, d.totalTokens()):
                print('ngsize=',ngsize)
                print('ngramfreq=',list(d.ngramfreq(g,1)))

                # locate the least-common ngrams
                ng0 = list(takewhile(lambda x:x[1] <= 1,
                    sorted(d.ngramfreq(g, ngsize), key=lambda x:x[1])))
                print('d.ngramfreq=', ng0[:20])
                ng0x = [x[0] for x in ng0]
                print('ng0x=',ng0x)

                # find potential alternative tokens for the tokens in the unpopular ngrams
                alt = dict([(t[0],[]) for ng in ng0x for t in ng])
                print('alt=',alt)
                # calculate alternatives for each unique token
                for t in alt.keys():
                    print('alt(',t,')=',alternatives(w,p,g,d,t))
                    alt[t] = [x[0] for x in alternatives(w,p,g,d,t)]
                # map alternatives back to tokens
                ng0b = [tuple(alt[t[0]] for t in n) for n in ng0x]
                print('alternatives...', ng0b)

                # consider inter-token possibilities as well.
                # not quite sure when/how to invoke this or integrate it.
                # when we have an unknown token/ngram? always?
                tokenlists = [tuple(t[0] for t in n) for n in ng0x]
                print('tokenlists=',tokenlists)
                if tokenlists != []:
                    intertok = inter_token(tokenlists[0], w.frq, g)
                    def list_intersect(l,m):
                        return list(filter(lambda x:x in l, m))
                    # list all ngrams containing partial matches for our ngram
                    partial = g.ngram_like(tokenlists[0])
                    print('partial=', partial)
                    # intersect with potential alternatives
                    print('ng0x before partial=',ng0x)
                    print('alt before partial=',alt)

                    ng0b = [tuple(list_intersect(p, alt[k])
                                for p,k in zip(partial, toks))
                                    for toks in tokenlists]
                    print('intersected alternatives=',ng0b)

                def mapstar(f, l):
                    return [f(*x) for x in l]

                # given our possible alternatives in ng0b, find the 
                ng0c = [list(product(*n)) for n in ng0b]
                print('alt ngrams...', ng0c[:100], '...')
                ng0d = [[(n, g.freq(n), sum(mapstar(levenshtein,zip(n,tl))))
                            for n,tl in zip(l,cycle(tokenlists))]
                                for l in ng0c]
                print('magic=', ng0d)
                ng0d = [sorted(x, key=lambda x:x[1]/max(1,x[2]), reverse=True) for x in ng0d]
                #ng0d = [list(takewhile(lambda x:x[1] > 0, x)) for x in ng0d]

                print('popular...', ng0d)

                # present our potential revisions
                proposedChanges = list(zip(ng0x, ng0d))
                print('proposedChanges...', proposedChanges)
                def merge_changes(changes):
                    revs = []
                    # isolate only the actual changes
                    for c in changes:
                        src,dstl = c
                        if dstl != []:
                            dst = dstl[0][0]
                            for s,d in zip(src,dst):
                                if s[0] != d and (s,d) not in revs:
                                    revs.append((s,d))
                    return revs

                mergedChanges = merge_changes(proposedChanges)
                print('mergedChanges=', mergedChanges)
                changePerTok = defaultdict(list)
                for t,c in mergedChanges:
                    changePerTok[t].append(c)
                print('changePerTok=', changePerTok)
                finalChanges = [(k,v[0]) for k,v in changePerTok.items()]
                finalChanges = sorted(finalChanges, key=lambda x:x[0][1]) # sort by line
                finalChanges = sorted(finalChanges, key=lambda x:x[0][2]) # then by index
                print('finalChanges=', finalChanges)
                res = d.demoChanges(finalChanges)
                print(res)
                passcnt += res == exp
                print('-----------','pass' if res == exp else 'fail','------------')
                ngsize -= 1
                #assert res == exp
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
    

