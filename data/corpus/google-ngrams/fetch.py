#!/usr/bin/env python

"""
fetch Google Books' 3-ary ngrams.
run me, then extract.py
enumerate, download, extract, filter and delete files
"""

"""
Traceback (most recent call last):
  File "./fetch.py", line 70, in <module>
    download(url, dst)
  File "./fetch.py", line 22, in download
    chunk = req.read(CHUNK)
  File "/usr/lib/python2.6/socket.py", line 353, in read
    data = self._sock.recv(left)
  File "/usr/lib/python2.6/httplib.py", line 538, in read
    s = self.fp.read(amt)
  File "/usr/lib/python2.6/socket.py", line 353, in read
    data = self._sock.recv(left)
socket.error: [Errno 104] Connection reset by peer
make: *** [data] Error 1
"""

import datetime

def log(what, msg):
	print('%s %s %s' % (datetime.datetime.now(), what, msg))

import urllib2

def download(url, dst):
	log(dst, 'download')
	CHUNK = 2 * 1024 * 1024
	while True:
		try:
			req = urllib2.urlopen(url)
			with open(dst, 'wb') as fp:
				while 1:
					chunk = req.read(CHUNK)
					if not chunk: break
					fp.write(chunk)
			break
		except socket.error:
			log(dst, 'error, continuing...')
			continue
	return dst

import re, collections
import os

def extract(filename, gzfile):
	log(filename, 'extract')
	CHUNK = 8 * 1024 * 1024
	with os.popen('unzip -p ' + filename) as fd:
		d = {}
		while 1:
			txt = fd.read(CHUNK)
			if not txt: break
			# ! ! Along       2008    4
			d.update(re.findall('\n([^\t]+)\t2008\t(\d+)', txt))
		with os.popen('gzip -c - > ' + gzfile, 'wb') as out:
			for k in sorted(d.keys()):
				out.write('%s\t%s\n' % (k, d[k]))

def delete(filename):
	try:
		if os.path.exists(filename):
			log(filename, 'delete')
			os.remove(filename)
	except:
		pass

def urls():
	for n in range(0, 200):
		yield 'http://commondatastorage.googleapis.com/books/ngrams/books/googlebooks-eng-all-3gram-20090715-' + str(n) + '.csv.zip'

def url2filename(url):
	return url[url.rfind('/')+1:]

def filename2gz(filename):
	return filename + '-2008.list.gz'

if __name__ == '__main__':
	import sys
	if len(sys.argv) > 1 and sys.argv[1] == '--run':
		for url in urls():
			try:
				dst = url2filename(url)
				dstgz = filename2gz(dst)
				if not os.path.exists(dstgz):
					if not os.path.exists(dst):
						download(url, dst)
					extract(dst, dstgz)
			except urllib2.HTTPError, e:
				print(e.reason)
				print('continuing...')
			finally:
				delete(dst) # delete either partial and or complete

