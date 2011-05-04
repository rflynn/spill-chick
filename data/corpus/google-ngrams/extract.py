#!/usr/bin/env python

"""
once fetch.py has grabbed a set of ngrams, I parse out a subset and generate CSV.
given our lists of 'x y z\tcnt', extract, parse and dump
"""

import os, re, sys
from glob import glob
from time import time
import multiprocessing as mp
import Queue

"""
filter n-grams with a freq < MinFreq. range should be somewhere between 20 and 100.

we do this to substantially reduce the number of n-grams considered by our program,
and improve the quality of our results. by definition we are trying to reduce the
document entropy, and need only consider n-grams with a certain frequency.

the population of n-grams is ~inversely proportional to its frequency.
approximately 1/2 have freq <= 2, 1/4 have freq >2 and <=4 etc.

by filtering we eliminate ~90%

we must maintain a balance between accepting garbage typos that appear a few times
globally and glossing over legitimate but infrequent phrases.
"""
MinFreq = 20

# one megabyte, 4*MB more clear than 4*1024*1024 or 4000000
MB = 1024 ** 2

Ids = {}
Ids['UNKNOWN'] = 0
Ids['$PROPERNOUN'] = 1
Ids['$NUMBER'] = 2

# translate each unique token into a unique numeric id
# must be thread-safe on write
def tokid(key):
	global Ids
	if key not in Ids:
		# create a new id, must be unique per key and linear
		Ids[key] = len(Ids)
	return Ids[key]

# gunzip 'filename', translate string tokens into ids and gzip write to 'dst'
def extractfile(nth, total, filename, dst, ids):
	global Ids
	start = time()
	with os.popen('gunzip -dc ' + filename, 'r') as gunzip:
		contents = '\n' + gunzip.read().lower()
	with os.popen('gzip -c - > ' + dst, 'wb', 4*MB) as gz:
		#for x,y,z,cnt in re.findall('\n([^\d\W]+) ([^\d\W]+) ([^\d\W]+)\t(\d+)', contents):
		#for m in re.finditer('\n([^ ]+) ([^ ]+) ([^ ]+)\t(\d+)', contents):
		# regexes are more expensive than string splitting but allow us a finer control over
		# what we accept which means we can reasonably skip exception setup.
		# turns out not setting up an exception for each of 200M lines shaves ~2/3x of our time(!)
		# include periods and apostrophes
		for m in re.finditer('\n([\w\']+) ([\w\']+) ([\w\']+)\t(\d+)',contents):
			x,y,z,cnt = m.groups()
			cnt = int(cnt)
			if cnt >= MinFreq:
				gz.write('%u,%u,%u,%u\n' % \
					(tokid(x), tokid(y), tokid(z), cnt))
	print '%3u/%3u %s (%.1f sec) ids:%u' % (nth, total, dst, time() - start, len(Ids))

# pulls filenames out of the queue and hand parameters off
# when we run out of items to process we timeout and return
def worker(q, ids):
	while True:
		try:
			nth,total,filename,dst = q.get(timeout=1)
			extractfile(nth,total,filename,dst, ids)
		except Queue.Empty:
			break

Q = mp.Queue()

# build queue of files to process
filenames = sorted(glob('*-2008.list.gz'))
total = len(filenames)
for nth,filename in enumerate(filenames):
	dst = str.replace(filename,'list.gz','ids.gz')
	if os.path.exists(dst):
		continue
	Q.put((nth+1,total,filename,dst))

if Q.qsize():
	print 'Queued %u files.' % (Q.qsize(),)

	# multiprocessing is great, except with 2 CPUs the overhead from manager
	# overcomes the benefit of keeping both CPUs busy, bummer. with 4+ CPUs it
	# might be a different story, I don't know.
	# for now, single CPU with dict() is the fastest
	DoMP = False
	if DoMP:
		manager = mp.Manager()
		Ids = mp.dict()
		Ids['UNKNOWN'] = 0
		Ids['$PROPERNOUN'] = 1
		Ids['$NUMBER'] = 2

		# create workers, run, wait for completion
		W = [ mp.Process(target=worker, args=(Q, Ids))
			for _ in range(mp.cpu_count()) ]
		for w in W: w.start()
		for w in W: w.join()
	else:
		worker(Q, None)

	print 'len(Ids)=', len(Ids)
	assert len(Ids) > 3

	with os.popen('gzip -c - > word.csv.gz', 'wb') as gz:
		Ids = sorted(Ids.items(), key=lambda x:x[1])
		for word,wid in Ids:
			gz.write('%s,%s\n' % (wid, word))

