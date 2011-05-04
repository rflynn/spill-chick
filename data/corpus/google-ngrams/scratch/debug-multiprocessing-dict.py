#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
a dict() must be shared between worker processes and whose contents,
written by the workers, must be accessible after they are done.

this is a contrived example exploring this.
"""

import multiprocessing as mp
import Queue
from time import sleep
manager = mp.Manager()
Ids = manager.dict()
Q = mp.Queue()

# build queue
for n in range(10):
	Q.put(n)

# mirror my getid() function
def setid(d, key, val): d[key] = val

def worker(my_id, q, ids):
	while True:
		try:
			k = q.get(timeout=1)
			setid(ids, k, my_id)
			sleep(0.01) # let other worker have a chance
		except Queue.Empty:
			return

W = [ mp.Process(target=worker, args=(i, Q, Ids))
	for i in range(2) ]
for w in W: w.start()
for w in W: w.join()

# figure out who did what
from operator import itemgetter as ig
from itertools import groupby
for k,g in groupby(sorted(Ids.items(), key=ig(1)), key=ig(1)):
	print 'worker', k, 'wrote keys', [x[0] for x in g]

