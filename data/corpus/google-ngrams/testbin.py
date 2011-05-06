
# Usage: python3 -i testbin.py

from ngram3bin import ngram3bin
#ng = ngram3bin('xxx') # too few parameters
ng = ngram3bin('word.bin','ngram3.bin')
ng.word2id('freq')
ng.word2id('FDWD#$#$@#@')
list(map(ng.word2id, ['activities','as','buddhist']))
[ng.id2freq(ng.word2id(w)) for w in ['activities','as','buddhist']][:30]
[ng.id2word(ng.word2id(w)) for w in ['activities','as','buddhist']][:30]
ng.freq(4,22,215)
ng.like(5,6,7)
# convert to ids, search, convert back to words
[(ng.id2word(x), ng.id2word(y), ng.id2word(z), freq)
	for x,y,z,freq in ng.like(*[ng.word2id(w) for w in ['activities','as','buddhist']])]
ng.freq(1,2)
#ng.like(3,4)
print('idknow')
idknow = ng.word2id('know')
print('word(idknow)')
ng.id2word(idknow)
assert 'know' == ng.id2word(ng.word2id('know'))
assert ng.id2freq(ng.word2id('know')) == ng.wordfreq('know')

# "bridge" missing made find a bug
print('id(bridge)=', ng.word2id('bridge'))
print('id2freq(bridge)=', ng.id2freq(ng.word2id('bridge')))
print('wordfreq(bridge)=', ng.wordfreq('bridge'))

# "didn" seems to be missing but shouldn't be...
print('wordfreq(didn)=', ng.wordfreq('didn'))

[(w,ng.word2id(w)) for w in ['didn','t','know']]
ng.freq(*[ng.word2id(w) for w in ['didn','t','know']])

# freq2
(('didn','t'), ng.freq(*[ng.word2id(w) for w in ['didn','t']]))
(('and','that'), ng.freq(*[ng.word2id(w) for w in ['and','that']]))
(('a','mistake'), ng.freq(*[ng.word2id(w) for w in ['a','mistake']]))

Test = [
	'am fond of',
	'am found of',
	'i now that',
	'i know that',
	'is now that',
	'future would undoubtedly',
	'it it did',
	'if it did',
	'and then it',
	'the united states',
	'cheese burger',
	'cheeseburger',
	'don t',
	"don ' t",
	'don',
	'dont',
	"don't",
	'i was alluding',
	'spill chick',
	'spell check',
	'spillchick',
	'spellcheck',
]
for s in Test:
	t = s.lower().split()
	ids = [ng.word2id(w) for w in t]
	frfunc = ng.freq if len(ids) > 1 else ng.id2freq
	print((t, 'freq:', frfunc(*ids), 'ids:', ids))
	assert all(ng.id2word(ng.word2id(w)) == w or ng.word2id(w) == 0 for w in t)

for foo in ['don','dont']:
	[(foo,ng.id2word(x), y) for x,y in ng.follows(ng.word2id(foo))[:100]]

