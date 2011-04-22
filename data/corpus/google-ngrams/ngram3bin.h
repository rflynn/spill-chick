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
		unsigned freq;
		const char *str;
	} *word;
};

#pragma pack(push, 1)
struct ngramwordcursor {
	uint32_t id;
	uint32_t len;
};
#pragma pack(pop)
typedef struct ngramwordcursor ngramwordcursor;

#define ngramwordcursor_str(cur)  ((char *)(cur) + sizeof *(cur))
#define ngramwordcursor_next(cur) (void *)((char *)(ngramwordcursor_str(cur) + ((cur)->len + (1 + ((cur)->len+1) % 4))))

#pragma pack(push, 1)
typedef struct
{
	uint32_t id[3],
		 freq;
} ngram3;
#pragma pack(pop)

struct ngramword    ngramword_load(const struct ngram3map);
const unsigned long ngramword_word2id(const char *word, unsigned len, const struct ngramword);
const char *	    ngramword_id2word(unsigned long id, const struct ngramword);
void		    ngramword_totalfreqs(struct ngramword, const struct ngram3map *);
void		    ngramword_fini(struct ngramword);

struct ngram3map    ngram3bin_init(const char *path);
unsigned long	    ngram3bin_freq(ngram3 find, const struct ngram3map *);
ngram3 *	    ngram3bin_like(ngram3 find, const struct ngram3map *);
void		    ngram3bin_str (const struct ngram3map, FILE *);
void		    ngram3bin_fini(struct ngram3map);

//#endif /* NGRAM3BIN_H */

