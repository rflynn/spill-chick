#!/usr/bin/env python3

"""
extract.py generated:
	word.csv.gz: master word file (word id,word)
	*-2008.list.gz: files of 3-ary ngrams (id0,id1,id2,cnt)

our goal:
	generate ngram.db: import csv data into sqlite database
		ngram.db.word <- master word file
			gunzip/gzip
			sqlite's .import
		ngram.db.ngram3 <- ngrams
			concatenate ngram lists into a single csv.gz file
				gunzip/gzip
				sqlite's .import

note: sqlite is very reliable, but it works against us performance-wise in large imports;
disable any notion of safety and don't create table indexes until they are built
"""

"""
yup, it turns out that sqlite just has too much per-row overhead.
the database, sans indexes, ended up being larger than ~4GB csv file
instead, use a custom binary format
"""

from struct import pack,unpack
with os.popen('gzip -dc word.csv.gz', 'r') as gz:
	with open('word.bin', 'wb') as bin:
		for line in gz:
			wid,word = line.rstrip().split(',')
			wid = int(wid)
			# FIXME: if our ids were perfectly contiguous we wouldn't need to explicitly include them
			bword = bytes(word, 'utf-8')
			wlen = len(bword)
			# pad bword with enough \0 to make next string start with alignment=4
			bword += b'\0' * (1 + ((len(bword)+1) % 4))
			"""
			write [uint32_t id][uint32_t len][word ... \0\0?\0?\0?]
			we use fields that are multiples of 4 bytes to keep the &word[0] 32-bit aligned
			which improves read performance
			"""
			bin.write(pack('<ii', wid, wlen) + bword)

# note: following takes ~35 minutes to process 4GB/~200M UTF-8 lines into ~100M binary on my machine
# note: port following the C

MinFreq = 100
ngcnt = 0
leftover = ''
with open('2008-ngram3-ids.csv', 'r') as gz:
	with open('ngram3.bin', 'wb') as bin:
		while 1:
			buf = gz.read(4 * 1024 * 1024)
			if not buf:
				break
			buf = leftover + buf
			lines = buf.split('\n')
			leftover = '' if buf.endswith('\n') else lines.pop()
			ngbytes = b''
			for line in lines:
				try:
					ng = tuple(map(int, line.split(',')))
					if ng[3] >= MinFreq:
						ngbytes += pack('<iiii', *ng)
						ngcnt += 1
				except ValueError as e:
					print('error on line "%s": %s' % (line, e))
			bin.write(ngbytes)
print('MinFreq=',MinFreq,'ngcnt=',ngcnt)

"""
import os
from glob import glob

def touch(fname):
	with open(fname, 'a') as x:
		pass

def makefaster(db):
	# ref: http://web.utk.edu/~jplyon/sqlite/SQLite_optimization_FAQ.html#pragmas
	db.write('pragma synchronous = OFF;\n')
	db.write('pragma count_changes = OFF;\n')
	db.write('pragma temp_store = MEMORY;\n')
	for n in range(11, 16+1):
		db.write('pragma page_size = %u;\n' % 2**n)

print('word.csv.gz -> word.csv')
os.system('gunzip word.csv.gz 2>/dev/null')
touch('ngram.db')

print('word.csv.gz -> ngram.db...')
with os.popen('sqlite3 :memory:', 'w') as db:
	makefaster(db)
	db.write('attach database "ngram.db" as ng;\n')
	db.write('create table ng.word (id int primary key, word text not null);\n')
	db.write('create table word (id int primary key, word text not null);\n')
	print('  word.csv.gz -> sqlite :memory:')
	db.write('.separator ","\n')
	db.write('.import word.csv word\n')
	print('  sqlite :memory: -> ngram.db')
	db.write('insert into ng.word select id,word from word;\n')
	print('  done.')

if not os.path.exists('2008-ngram3-ids.csv'):
	print('*-2008.ids.gz -> 2008-ngram3-ids.csv')
	os.system('gzip -dc *-2008.ids.gz > 2008-ngram3-ids.csv')
	print('  done.')

print('2008-ngram3-ids.csv -> ngram.db...')
with os.popen('sqlite3 ngram.db', 'w') as db:
	makefaster(db)
	db.write('create table ngram3 (id0 int, id1 int, id2 int, cnt int);\n')
	print('  importing...')
	db.write('.separator ","\n')
	db.write('.import 2008-ngram3-ids.csv ngram3\n')
	print('  done.')

exit(0)
"""
