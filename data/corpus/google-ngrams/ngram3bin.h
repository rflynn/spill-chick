/* ex: set ts=8 noet: */
/*
 * Copyright 2011 Ryan Flynn <parseerror+github@gmail.com>
 */

//#ifndef NGRAM3BIN_H
//#define NGRAM3BIN_H

#include <stdio.h>
#include <stdint.h>

struct ngram3map
{
	void *m;
	int fd;
	unsigned long long size;
};

struct ngramword
{
	unsigned long cnt;
	struct wordlen {
		unsigned len;
		const char *str;
	} *word;
};

#pragma pack(push, 1)
typedef struct
{
	uint32_t id[3],
		 freq;
} ngram3;
#pragma pack(pop)

struct ngram3map ngram3bin_init(const char *path);
struct ngramword ngramword_load(const struct ngram3map m);
const unsigned long	ngramword_word2id(const char *word, unsigned len, const struct ngramword w);
const char * ngramword_id2word(unsigned long id, const struct ngramword w);
ngram3 *	 ngram3bin_find(ngram3 find, const struct ngram3map);
void		 ngram3bin_str (const struct ngram3map, FILE *);
void		 ngram3bin_fini(struct ngram3map m);
void		 ngramword_fini(struct ngramword);

//#endif /* NGRAM3BIN_H */

