#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Doc represents a document being checked against existing Grams
"""

import gram

"""
Tokenize document contents; each token is associated with positional data
"""
class Doc:
	def __init__(self, f, w):
		self.f = f
		self.words = w
		self.tok = [[]]
		for lcnt,line in enumerate(f):
			line = line.lower() # used for index below
			toks = gram.tokenize(line)
			if toks == []:
				if self.tok[-1] != []:
					self.tok.append([])
				continue
			tpos = 0
			ll = []
			for t in toks:
				tpos = line.index(t, tpos)
				ll.append((t, lcnt, tpos))
			self.tok[-1] += ll

	def unknownToks(self):
		for tok in self.tok:
			for t in tok:
				if self.words.id(t[0]) == 0:
					yield t

	def ngrams(self, size=2):
		for tok in self.tok:
			for i in range(0, len(tok)+1-size):
				yield tuple(tok[i:i+size])

	def checkNGrams(self, g, size=2):
		for ng in self.ngrams(size):
			ng2 = tuple(t[0] for t in ng)
			if g.freq(ng2) == 0:
				yield ng

	"""
	Modify replacement word 'y' to match the capitalization of existing word 'x'
	(foo,bar) -> bar
	(Foo,bar) -> Bar
	(FOO,bar) -> BAR
	"""
	@staticmethod
	def matchCap(x, y):
		if x == x.lower():
			return y
		elif x == x.capitalize():
			return y.capitalize()
		elif x == x.upper():
			return y.upper()
		return y

	"""
	given an ngram containing position data, replace corresponding data in lines with 'mod'
	"""
	def applyChange(self, lines, ngpos, mod, off):
		# FIXME: must keep track of offset changes produced by replacements of different lengths
		for (o,l,pos),rep in zip(ngpos, mod):
			pos += off[l]
			end = pos + len(o)
			ow = lines[l][pos:end]
			cap =  Doc.matchCap(ow, rep)
			lines[l] = lines[l][:pos] + cap + lines[l][end:]
			off[l] += len(cap) - len(o)
		return (lines, off)
	
	# alternative popularity... [((('their', 0, 0), ('it', 0, 6)), [(('there', 'it'), 17)]), ((('nope', 2, 0), ('i', 2, 6)), []), ((('was', 2, 8), ('write', 2, 12)), [(('was', 'right'), 24)]), ((('write', 2, 12), ('xxyz', 2, 19)), [])]
	def demoChanges(self, lines, changes):
		off = [0] * len(lines)
		for change in changes:
			ngpos, mods = change
			if mods == []:
				continue
			mod,score = mods[0]
			lines, off = self.applyChange(lines, ngpos, mod, off)
		return lines

if __name__ == '__main__':
	d = Doc(['a b c','d e f'])
	print(d.tok)

