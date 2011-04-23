all: data

data: ngrams

ngrams:
	$(MAKE) -C data/corpus/google-ngrams
