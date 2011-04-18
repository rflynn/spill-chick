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
        if sum(map(len, toks)) <= 12:
            s = list(algo.splits(toks, freq, g))
            return s
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
        print('g.freq((it,use))=',g.freq(('it','use')))


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

        def rsort(l, **kw):
            return sorted(l, reverse=True, **kw)
        def rsortn(l, n):
            return rsort(l, key=itemgetter(n))
        def sortn(l, n):
            return sorted(l, key=itemgetter(n))

        def alternatives(w, p, g, d, t):
            """
            given tok ('token', line, index) return a list of possible alternative tokens.
            only return alternatives that within the realm of popularity of the original token.
            """
            edit = w.similar(t)
            phon = p.soundsLike(t,g)
            uniq = edit | set(phon)
            minpop = lambda x: round(log(g.freqs(x)))
            alt = [(x,levenshtein(t,x),minpop(x)) for x in uniq if minpop(x) > 0]
            #alt = rsort_nth(alt, 2)
            #alt = sort_nth(alt, 1)
            alt2 = [x[0] for x in alt]
            return set(alt2)

        alt_know = alternatives(w,p,g,None,'know')
        print('alt(know)=',alt_know)
        alt_now = alternatives(w,p,g,None,'now')
        print('alt(now)=',alt_now)
        #assert 'know' in alt_now

        passcnt = 0
        for str,exp in Tests:
            d = Doc(str, w)
            print('doc=', d.tok)

            # start out like a regular spellchecker
            # address unknown tokens (ngram size 1) first
            ut = list(d.unknownToks())
            print('unknownToks=',ut)
            utChanges = [(u, w.correct(u[0])) for u in ut]
            print('utChanges=',utChanges)
            d.applyChanges(utChanges)

            """
            now the hard part.
            locate uncommon n-gram sequences which may indicate grammatical errors
            see if we can determine better replacements for them given their context
            """

            # order n-grams by unpopularity
            ngsize = min(3, d.totalTokens())
            while ngsize >= min(3, d.totalTokens()):
                ngsize = min(3, d.totalTokens())
                print('ngsize=',ngsize)
                print('ngram(1) freq=',list(d.ngramfreq(g,1)))

                # locate the least-common ngrams
                least_common = sortn(d.ngramfreq(g, ngsize), 1)
                print('least_common=', least_common[:20])
                if least_common == []:
                    break

                target_ngram = least_common[0]
                print('target_ngram=',target_ngram)
                toks = [x[0] for x in target_ngram[0]]
                print('toks=',toks)

                # find potential alternative tokens for the tokens in the unpopular ngrams
                alt = dict([(t, alternatives(w,p,g,d,t)) for t in toks])
                print('alt=',alt)

                # list all ngrams containing partial matches for our ngram
                part = g.ngram_like(toks)
                print('part=', part)

                """
                part & alt
                part is based on our corpus and alt based on token similarity.
                an intersection between the two means we've found as good a candidate as we'll get.
                """
                part_pop = [[p for p in pa if p in alt[t]] for t,pa in zip(toks, part)]
                print('part_pop=', part_pop)

                if any(p == [] for p in part_pop):
                    """
                    incomplete intersection. either we just haven't seen it or they've truly mangled it.
                    """
                    intertok = inter_token(toks, w.frq, g)
                    print('intertok=', intertok)
                    if intertok != []:
                        part_pop = [(x,) for x in intertok[0]]

                    if intertok == []:
                        for i in range(len(part_pop)):
                            if part_pop[i] == []:
                                dec = [(t, g.freqs(t), levenshtein(t, toks[i]))
                                        for t in alt[toks[i]] if t != toks[i]]
                                part_pop[i] = [x[0] for x in sortn(dec, 2)][:3]
                        print("part_pop'=", part_pop)

                partial = list(product(*part_pop))
                print('partial=', partial)

                best = partial
                print('best=',best)

                if best:
                    # present our potential revisions
                    proposedChanges = list(zip(target_ngram[0], best[0]))
                    print('proposedChanges...', proposedChanges)
                    res = d.demoChanges(proposedChanges)
                    print(res)
                    d.applyChanges(proposedChanges)

                """
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
                """
                ngsize -= 1

            passcnt += d.lines == exp
            print('-----------','pass' if d.lines == exp else 'fail','------------')
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
    

