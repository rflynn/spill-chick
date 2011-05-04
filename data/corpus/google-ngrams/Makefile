CP = cp

build: ngram3bin.h ngram3bin.c ngram3binpy.c build-py build-py3

build-py:
	python setup.py build
	sudo python setup.py install

build-py3:
	python3 setup.py build
	sudo python3 setup.py install

# googlebooks-eng-all-3gram-20090715-#.csv.zip
#  -> fetch -> *-2008-list.gz (word,word,word,freq)
#                  -> extract -> *-2008.ids.gz (id,id,id,freq)
#                             -> word.csv.gz (wid,word)
#                                  -> import2bin-word.py -> word.bin (id,word utf8 binary padded)
#                                  -> import2bin-ngram  -> ngram3.bin (id,id,id,freq binary)
#                                                            -> ngram3bin-compact -> ngram3.bin.sort
data: import2bin-ngram ngram3bin-compact
	./fetch.py --run
	./extract.py
	./import2bin-word.py
	$(RM) ngram3.bin
	gzip -dc *.ids.gz | ./import2bin-ngram > ngram3.bin
	./ngram3bin-compact
	$(RM) ngram3.bin
	ln -s ngram3.bin.sort ngram3.bin

all: ngram3bin
ngram3bin: ngram3bin.o
import2bin-ngram: import2bin-ngram.o
ngram3bin-compact: ngram3bin-compact.o ngram3bin.o
