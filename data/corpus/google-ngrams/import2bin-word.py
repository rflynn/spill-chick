#!/usr/bin/env python3

import os

"""
extract.py generated:
	word.csv.gz: master word file (word id,word)
	*-2008.ids.gz: files of 3-ary ngrams (id0,id1,id2,freq)

we take word.csv.gz, which is already in sorted order by id ascending,
and compact the words into binary format and write to word.bin
"""

from struct import pack,unpack
with os.popen('gzip -dc word.csv.gz', 'r') as gz:
	with open('word.bin', 'wb') as bin:
		for line in gz:
			wid,word = line.rstrip().split(',', 1)
			wid = int(wid)
			bword = bytes(word, 'utf-8')
			wlen = len(bword)
			# pad bword with enough \0 to make next string start with alignment=4
			bword += b'\0' * (1 + ((len(bword)+1) % 4))
			"""
			write [uint32_t len][word ... \0\0?\0?\0?]
			we use fields that are multiples of 4 bytes to keep the &word[0] 32-bit aligned
			which improves read performance
			"""
			bin.write(pack('<i', wlen) + bword)


