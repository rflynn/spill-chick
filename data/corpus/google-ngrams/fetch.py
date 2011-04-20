#!/usr/bin/env python

"""
fetch Google Books' 3-ary ngrams.
run me, then extract.py
enumerate, download, extract, filter and delete files
"""

import datetime

def log(what, msg):
	print('%s %s %s' % (datetime.datetime.now(), what, msg))

import urllib2

def download(url, dst):
	CHUNK = 2 * 1024 * 1024
	req = urllib2.urlopen(url)
	with open(dst, 'wb') as fp:
		while 1:
			chunk = req.read(CHUNK)
			if not chunk: break
			fp.write(chunk)
	return dst

import re, collections
import os

def extract(filename, gzfile):
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
		os.remove(filename)
	except:
		pass

def urls():
	for n in range(1, 200):
		yield 'http://commondatastorage.googleapis.com/books/ngrams/books/googlebooks-eng-all-3gram-20090715-%u.csv.zip' % n

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
						log(url, 'download')
						download(url, dst)
					log(dst, 'extract')
					extract(dst, dstgz)
					log(dst, 'delete')
			except urllib2.HTTPError, e:
				print(e.reason)
				print('continuing...')
			finally:
				delete(dst) # delete partial
