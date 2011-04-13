#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

"""

from collections import defaultdict
import re
import sys
import traceback
import os
from gram import Grams
# NOTE: tried subprocess module but doesn't seem to be able to do per-line output...

def shell_escape(str):
	return str.replace(' ', '\\ ').replace("'", "\\'")

def cat_cmd(filename):
	l = filename.lower()
	if l.endswith('.bz2'):
		return 'bzcat %s' % (shell_escape(filename),)
	elif l.endswith('.tar.gz') or l.endswith('.tgz'):
		return 'zcat %s | tar xfO -' % (shell_escape(filename),)
	else:
		return 'cat %s' % (shell_escape(filename),)

def corpus(name='gutenberg'):
	dir = '../data/corpus/'+name+'/'
	for file in os.popen('ls ' + dir + '|head -n 3', 'r'):
		file = file.strip()
		print('%s...' % (file,))
		p = os.popen(cat_cmd(dir+file), 'r')
		yield p

# wikipedia markup filter generator
class wikipedia_lines:
	def __init__(self, p):
		self.p = p
	def __iter__(self):
		for line in self.p:
			# find article start
			for line in self.p:
				if '<text xml:space' in line:
					break
			if not '</text>' in line:
				# go until article end
				for line in self.p:
					if '</text>' in line:
						break
					# FIXME: this regex crap is 90% of our processing time
					line = re.sub('&lt;/?ref.*?&gt;?', '', line)		# ref crap
					line = re.sub('{{.*(?:}})?', '', line)			# citation crap
					line = re.sub('!--.*?--', '', line)			# comments
					line = re.sub('\[\[.*]]', '', line)			# interior link
					line = re.sub('&\S+;?', '', line)			# entity crap
					line = re.sub('&\w+;?|!--.*?--|.*}}', '', line) 			# &entity;
					line = re.sub("''wikt:(.*?)''", '\\1', line)		# wiktionary link
					line = re.sub('\[http.*?]', '', line)			# exterior link
					line = re.sub('(?:File|Image|Category):\S+', '', line)	# exterior link
					#line = re.sub('.*}}', '', line)				# multi-line citation
					if re.match('^[a-z]{2,3}:\S+', line):
						continue
					line = line.strip()
					if line == '' or line[0] == '|' or line[0] == '!' or line[0] == '{' or ']]' in line:
						continue
					#print(line)
					yield line

def corpus_wikipedia():
	p = os.popen('bzcat ../data/corpus/enwiki-latest-pages-articles.xml.bz2 2>/dev/null | head -n 500000', 'r')
	yield wikipedia_lines(p)

class email_lines:
	def __init__(self, p):
		self.p = p
	def __iter__(self):
		for line in self.p:
			if line.startswith('X-') or \
			   line.startswith('=09') or \
			   re.match('^(Content-Transfer-Encoding|Message-ID|Date|From|To|Subject|Cc|Mime-Version|Content-Type|Bcc):', line):
				continue
			yield line

def corpus_enron():
	p = os.popen('zcat ../data/corpus/enron_mail_20110402.tgz | tar xfO - 2>/dev/null', 'r')
	yield email_lines(p)

def parse_corpus(c):
	g = Grams()
	for p in c:
		g.add(p)
	return g

def ngram_match(tok, w2id, ngrams):
	if tok not in w2id:
		return []
	id = w2id[tok]
	print('%s -> %s' % (tok, id))
	return [n for n in ngrams.keys() if id in n]

import pickle

if __name__ == '__main__':
	f = ['a b c','d e f']
	g = Grams(f)
	print(g)

	w = parse_corpus(corpus_enron())
	pop = sorted(w.ngrams.items(), key=lambda x:x[1], reverse=True)[:200]
	popw = [(tuple(w.id2w[id] for id in n),cnt) for n,cnt in pop]
	print(popw)
	print('len(pickle(w2id))=%s' % (len(pickle.dumps(w.w2id)),))

	#print([tuple(id2w[id] for id in ng) for ng in ngram_match('the', w2id, ngrams)[:100]])

