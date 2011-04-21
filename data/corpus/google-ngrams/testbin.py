
from ngram3bin import ngram3bin
ng = ngram3bin('word.bin','ngram3.bin')
[ng.word2id(w) for w in ['activities','as','buddhist']]
[ng.id2word(ng.word2id(w)) for w in ['activities','as','buddhist']]
ng.find(5,6,7)
ng.find(*[ng.word2id(w) for w in ['activities','as','buddhist']])

"""
from ngram3bin import ngram3bin
ng = ngram3bin('word.bin','ngram3.bin')
print('ng=', ng)
#print('word2id(a:4)=', ng.word2id('a'))
print('word2id(activities:5)=', ng.word2id('activities'))
#print('word2id(of:6)=', ng.word2id('of'))
print('word2id(buddhist:43)', ng.word2id('buddhist'))
#print('word2id(as:8)=', ng.word2id('as'))
#print('word2id(bibliography:12)=', ng.word2id('bibliography'))
word4 = ng.id2word(4)
print('id2word(4)=', word4)
f = ng.find(5,6,7)
print('find(5,6,7)=', f)
ng.find(7,8,9)
"""
