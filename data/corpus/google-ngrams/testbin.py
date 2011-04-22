
from ngram3bin import ngram3bin
#ng = ngram3bin('xxx') # too few parameters
ng = ngram3bin('word.bin','ngram3.bin')
ng.word2id('freq')
ng.word2id('FDWD#$#$@#@')
list(map(ng.word2id, ['activities','as','buddhist']))
[ng.id2freq(ng.word2id(w)) for w in ['activities','as','buddhist']]
[ng.id2word(ng.word2id(w)) for w in ['activities','as','buddhist']]
ng.freq(4,22,215)
ng.like(5,6,7)
# convert to ids, search, convert back to words
[(ng.id2word(x), ng.id2word(y), ng.id2word(z), freq)
	for x,y,z,freq in ng.like(*[ng.word2id(w) for w in ['activities','as','buddhist']])]
ng.freq(1,2)
ng.like(3,4)
print('idknow')
idknow = ng.word2id('know')
print('word(idknow)')
ng.id2word(idknow)
assert 'know' == ng.id2word(ng.word2id('know'))
assert ng.id2freq(ng.word2id('know')) == ng.wordfreq('know')
print('id(bridge)=', ng.word2id('bridge'))
print('id2freq(bridge)=', ng.id2freq(ng.word2id('bridge')))
print('wordfreq(bridge)=', ng.wordfreq('bridge'))

