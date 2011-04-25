#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Doc represents a document being checked against existing Grams
"""

import collections
import unittest
import math
import gram

"""
Tokenized contents of a single file
Tokens associated with positional data to faciliate changes
"""
class Doc:

	def __init__(self, f, w):
		self.words = w				# global tokens
		self.docwords = collections.Counter()	# local {token:freq}
		self.tokenize(f)

	def tokenize(self, f):
		self.lines = []
		self.tok = [[]]
		for lcnt,line in enumerate(f):
			self.lines.append(line)
			line = line.lower() # used for index below
			toks = gram.tokenize(line)
			if toks == ['\n'] or toks == []:
				if self.tok[-1] != []:
					self.tok.append([])
				continue
			if toks[-1] == '\n':
				toks.pop()
			self.docwords.update(toks) # add words to local dictionary
			tpos = 0
			ll = []
			for t in toks:
				tpos = line.index(t, tpos)
				ll.append((t, lcnt, len(ll), tpos))
				tpos += len(t)
			self.tok[-1] += ll

	def totalTokens(self):
		return sum(len(ts) for ts in self.tok)
		return sum(self.docwords.values())

	def unknownToks(self):
		for tok in self.tok:
			for t in tok:
				if self.words.freq(t[0]) == 0:
					yield t

	# given token t supply surrounding token ngram (x, tok, y)
	def surroundTok(self, t):
		line = self.tok[t[1]]
		idx = line.index(t)
		if idx > 0 and idx < len(line)-1:
			return tuple(line[idx-1:idx+2])
		return None

	def ngrams(self, size):
		for tok in self.tok:
			for i in range(0, len(tok)+1-size):
				yield tuple(tok[i:i+size])

	def ngramfreq(self, g, size):
		for ng in self.ngrams(size):
			ng2 = tuple(t[0] for t in ng)
			yield (ng, g.freq(ng2))


	def ngram_prev(self, ngpos):
		_,line,index,_ = ngpos
		if index == 0:
			if line == 0:
				return None
			line -= 1
			index = len(self.tok[line])-1
		else:
			index -= 1
		return self.tok[line][index]

	def ngram_next(self, ngpos):
		_,line,index,_ = ngpos
		if index == len(self.tok[line])-1:
			if line == len(self.tok)-1:
				return None
			line += 1
			index = 0
		else:
			index += 1
		return self.tok[line][index]

	def ngram_context(self, ngpos, size):
		"""
		given an ngram and a size, return a list of ngrams that contain
		one or more members of ngram
		    c d e
                a b c d e f g
		"""
		before, ng = [], ngpos[0]
		for i in range(size):
			ng = self.ngram_prev(ng)
			if not ng:
				break
			before.insert(0, ng)
		after, ng = [], ngpos[-1]
		for i in range(size):
			ng = self.ngram_next(ng)
			if not ng:
				break
			after.append(ng)
		return before + list(ngpos) + after


	@staticmethod
	def matchCap(x, y):
		"""
		Modify replacement word 'y' to match the capitalization of existing word 'x'
		(foo,bar) -> bar
		(Foo,bar) -> Bar
		(FOO,bar) -> BAR
		"""
		if x == x.lower():
			return y
		elif x == x.capitalize():
			return y.capitalize()
		elif x == x.upper():
			return y.upper()
		return y

	def applyChange(self, lines, ngpos, mod, off):
		"""
		given an ngram containing position data, replace corresponding data
		in lines with 'mod'
		"""
		o,l,idx,pos = ngpos
		pos += off[l]
		end = pos + len(o)
		ow = lines[l][pos:end]
		if not mod and pos > 0 and lines[l][pos-1] in (' ','\t','\r','\n'):
			# if we've removed a token and it was preceded by whitespace,
			# nuke that whitespace as well
			pos -= 1
		cap =  Doc.matchCap(ow, mod)
		lines[l] = lines[l][:pos] + cap + lines[l][end:]
		off[l] += len(cap) - len(o)
		# FIXME: over-simplified; consider multi-token change
		self.docwords[ow] -= 1
		if mod:
			self.docwords[mod] += 1
		return (lines, off)

	def demoChanges(self, changes):
		"""
		given a list of positional ngrams and a list of replacements,
		apply the changes and return a copy of the updated file
		"""
		lines = self.lines[:]
		off = [0] * len(lines)
		for change in changes:
			ngpos, mod = change
			lines, off = self.applyChange(lines, ngpos, mod, off)
		return lines

	def applyChanges(self, changes):
		self.tokenize(self.demoChanges(changes))

class DocTest(unittest.TestCase):
	def test_change(self):
		pass

if __name__ == '__main__':
	unittest.main()

