build: ngram3bin.h ngram3bin.c ngram3binpy.c build-py build-py3

build-py:
	python setup.py build
	sudo python setup.py install

build-py3:
	python3 setup.py build
	sudo python3 setup.py install

data: ngram3bin-compact
	./fetch.py
	./extract.py
	./import2bin.py
	./ngram3bin-compact
	$(CP) ngram.bin.sort ngram.bin

all: ngram3bin
ngram3bin: ngram3bin.o
ngram3bin-compact: ngram3bin-compact.o ngram3bin.o
