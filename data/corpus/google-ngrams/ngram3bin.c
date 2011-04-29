/* ex: set ts=8 noet: */
/*
 * Copyright 2011 Ryan Flynn <parseerror+github@gmail.com>
 *
 * our 3-ary ngrams are in binary format in ngram3.bin
 */

#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <arpa/inet.h>
#include "ngram3bin.h"

void ngram3bin_str(const struct ngram3map m, FILE *f)
{
	fprintf(f, "ngram3map(size=%llu)", m.size);
}

struct ngram3map ngram3bin_init(const char *path, int write)
{
	struct stat st;
	struct ngram3map m = { NULL, -1, 0 };
	if (!stat(path, &st))
	{
		//printf("stat(\"%s\") size=%llu\n", path, (unsigned long long)st.st_size);
		if (-1 != (m.fd = open(path, write ? O_RDWR : O_RDONLY)))
		{
			m.size = st.st_size;
			m.m = mmap(NULL, m.size, PROT_READ | (write ? PROT_WRITE : 0), MAP_SHARED, m.fd, 0);
			if (MAP_FAILED == m.m)
			{
				perror("mmap");
				m.m = NULL;
			}
		}
	}
	return m;
}

// ng is 'cnt' items long; we need to ensure at least 1 more ngram3 in it
ngram3 * ngram3_find_spacefor1more(ngram3 *ng, unsigned long cnt)
{
	// allocate space for results on every power of 2
	// 0->1, 1->2, 2->4, 4->8, etc.
	if ((cnt & (cnt - 1)) == 0)
	{
		unsigned long alloc = cnt ? cnt * 2 : 1;
		ngram3 *tmp = realloc(ng, alloc * sizeof *ng);
		if (tmp)
		{
			ng = tmp;
		}
		else
		{
			free(ng);
			ng = NULL;
		}
	}
	return ng;
}

/*
 * map contains the mmap'ed contents of a dictionary file
 * the dictionary file is a list of variable-length entries in the form
 * [uint32_t id][uint32_t len][utf-8 encoded string of bytes length 'len']
 */
struct ngramword ngramword_load(const struct ngram3map m)
{
	ngramwordcursor *cursor = m.m;
	ngramwordcursor *end = (void *)((char *)m.m + m.size);
	unsigned long maxpossible = m.size / 6 + 1;
	struct ngramword w;
	w.word = calloc(maxpossible, sizeof *w.word);
	w.cnt = 0;
	while (cursor < end)
	{
		const char *str = ngramwordcursor_str(cursor);
		w.word[w.cnt].len = cursor->len;
		w.word[w.cnt].str = str;
		w.cnt++;
		cursor = ngramwordcursor_next(cursor);
	}
	w.word = realloc(w.word, w.cnt * sizeof *w.word);
	return w;
}

/*
 * FIXME: O(n)
 * if i added a stage at the beginning of this whole process and sorted words then we could
 * reduce this to O(log n)
 * we can also reduce the impact of this by converting all tokens in a document to their ids
 * once for the duration of the process; currently we're being lazy and repeatedly translating
 */
const unsigned long ngramword_word2id(const char *word, unsigned len, const struct ngramword w)
{
	unsigned long id = 0;
	printf("ngramword_word2id(word=\"%s\", w={%lu,%p})\n", word, w.cnt, w.word);
	while (id < w.cnt)
	{
		if (w.word[id].len == len && 0 == memcmp(word, w.word[id].str, len))
			break;
		id++;
	}
	if (id == w.cnt)
		id = 0;
	return id;
}

const char * ngramword_id2word(unsigned long id, const struct ngramword w)
{
	if (id < w.cnt)
		return w.word[id].str;
	return NULL;
}

void ngramword_fini(struct ngramword w)
{
	free(w.word);
}

/*
 * ngram3 comparison callback
 * ascending order
 */
int ngram3cmp(const void *va, const void *vb)
{
	const ngram3 *a = va,
	             *b = vb;
	if (a->id[0] != b->id[0]) return (int)(a->id[0] - b->id[0]);
	if (a->id[1] != b->id[1]) return (int)(a->id[1] - b->id[1]);
	if (a->id[2] != b->id[2]) return (int)(a->id[2] - b->id[2]);
	return 0;
}

/*
 * 
 */
unsigned long ngram3bin_freq(ngram3 find, const struct ngram3map *m)
{
	ngram3 *base = m->m;
	size_t nmemb = m->size / sizeof *base;
	const ngram3 *res = bsearch(&find, base, nmemb, sizeof *base, ngram3cmp);
	return res ? res->freq : 0;
}

/*
 * given find (x,y) sum the occurences of (x,y,_) and (_,x,y)
 */
unsigned long ngram3bin_freq2(ngram3 find, const struct ngram3map *m)
{
	unsigned long freq = 0;
	ngram3 *cur = m->m;
	const ngram3 *end = (ngram3 *)((char *)cur + m->size);
	while (cur < end)
	{
		if (cur->id[0] == find.id[0] &&
		    cur->id[1] == find.id[1])
		{
			freq += cur->freq;
		}
		else
		if (cur->id[1] == find.id[0] &&
		    cur->id[2] == find.id[1])
		{
			freq += cur->freq;
		}
		cur++;
	}
	return freq;
}


/*
 * given an id 3-gram (x,y,z) and a list of ngram frequencies
 * return matches (_,y,z) or (x,_,z) or (x,y,_)
 */
ngram3 * ngram3bin_like(ngram3 find, const struct ngram3map *m)
{
	unsigned long ngcnt = 0;
	ngram3 *cur = m->m;
	const ngram3 *end = (ngram3*)((char*)cur + m->size);
	ngram3 *res = NULL;
	while (cur < end)
	{
		if (((cur->id[0] == find.id[0]) +
		     (cur->id[1] == find.id[1]) +
		     (cur->id[2] == find.id[2])) == 2)
		{
			res = ngram3_find_spacefor1more(res, ngcnt);
			if (!res)
				break;
			res[ngcnt] = *cur; /* copy result */
			ngcnt++;
		}
		cur++;
	}
	if (res)
	{
		if ((res = ngram3_find_spacefor1more(res, ngcnt)))
			res[ngcnt].freq = 0; // sentinel
	}
	return res;
}

static unsigned long ngram3bin_like_xy_(ngram3 find, const struct ngram3map *m, ngram3 **res, unsigned long rescnt);
static unsigned long ngram3bin_like_x_z(ngram3 find, const struct ngram3map *m, ngram3 **res, unsigned long rescnt);
static unsigned long ngram3bin_like__yz(ngram3 find, const struct ngram3map *m, ngram3 **res, unsigned long rescnt,
					ngram3bin_index *idx);

/*
 * given an id 3-gram (x,y,z) and a list of ngram frequencies
 * return matches (_,y,z) or (x,_,z) or (x,y,_)
 *
 * note: this is really the crux of the application: finding ngram-based context.
 * this function will be run thousands of times for every page of text our application checks.
 * 'm' represents 10s of millions of records totalling 100s of MBs.
 * efficiency is critical.
 *
 * note: upgrade of ngram3bin_like(), which performed a sequential scan of the entire 'm' every time.
 * this was simple and effective but just too inefficient.
 * so, we broke up the 3 types of matches performed into separate functions which incorporate binary
 * searches, which should reduce CPU-memory traffic considerably.
 * update: preliminary profiling suggests this is ~40x faster.
 */
ngram3 * ngram3bin_like_better(ngram3 find, const struct ngram3map *m, ngram3bin_index *idx)
{
	ngram3 *res = NULL;
	unsigned long rescnt = 0;
	rescnt = ngram3bin_like_xy_(find, m, &res, rescnt);
	rescnt = ngram3bin_like_x_z(find, m, &res, rescnt);
	rescnt = ngram3bin_like__yz(find, m, &res, rescnt, idx);
	if (res)
	{
		if ((res = ngram3_find_spacefor1more(res, rescnt)))
			res[rescnt].freq = 0; // sentinel
	}
	return res;
}

static int ngram3cmp_xy_(const void *va, const void *vb)
{
	const ngram3 *a = va,
	             *b = vb;
	if (a->id[0] != b->id[0]) return (int)(a->id[0] - b->id[0]);
	if (a->id[1] != b->id[1]) return (int)(a->id[1] - b->id[1]);
	return 0;
}

/*
 * find entries in m matching (x,y,_) from find
 * because m's contents are sorted we can use bsearch
 */
static unsigned long ngram3bin_like_xy_(ngram3 find, const struct ngram3map *m, ngram3 **res, unsigned long rescnt)
{
	const ngram3 *base = m->m;
	const size_t nmemb = m->size / sizeof *base;
	const ngram3 *bs = bsearch(&find, base, nmemb, sizeof *base, ngram3cmp_xy_);
	if (bs)
	{
		const ngram3 *end = (ngram3*)((char*)m->m + m->size);
		// at least one x,y_ exists, but many may exist and we can't be certain
		// where in that range we have landed
		// rewind to the beginning of the range...
		while (bs > base && (bs-1)->id[0] == find.id[0] && (bs-1)->id[1] == find.id[1])
			bs--;
		// ...and then seek forward, capturing all (contiguous) matches
		while (bs < end && bs->id[0] == find.id[0] && bs->id[1] == find.id[1])
		{
			*res = ngram3_find_spacefor1more(*res, rescnt);
			if (!*res)
				break;
			(*res)[rescnt] = *bs;
			rescnt++;
			bs++;
		}
	}
	return rescnt;
}

static int ngram3cmp_x__(const void *va, const void *vb)
{
	const ngram3 *a = va,
		     *b = vb;
	if (a->id[0] != b->id[0]) return (int)(a->id[0] - b->id[0]);
	return 0;
}

/*
 * find entries in m matching (x,_,z) from find
 * because m's contents are sorted we can use bsearch
 */
static unsigned long ngram3bin_like_x_z(ngram3 find, const struct ngram3map *m, ngram3 **res, unsigned long rescnt)
{
	const ngram3 *base = m->m;
	const size_t nmemb = m->size / sizeof *base;
	const ngram3 *bs = bsearch(&find, base, nmemb, sizeof *base, ngram3cmp_x__);
	if (bs)
	{
		const ngram3 *end = (ngram3*)((char*)m->m + m->size);
		// rewind to the beginning of (x,_,_) range...
		while (bs > base && (bs-1)->id[0] == find.id[0])
			bs--;
		// and then seek forward through all (x,_,_),
		// recording any (x,_,z) matches
		while (bs < end && bs->id[0] == find.id[0])
		{
			if (bs->id[2] == find.id[2])
			{
				*res = ngram3_find_spacefor1more(*res, rescnt);
				if (!*res)
					break;
				(*res)[rescnt] = *bs;
				rescnt++;
			}
			bs++;
		}
	}
	return rescnt;
}

/*
 * given find (x,y,z), search m for all matches of (_,y,z) with help of the index
 * m entries are sorted by (x,y,z)
 * idx is a length of the spans of entries with the same (x,_,_)
 * search through m by idx[] records at a time.
 * search sequential for small spans, bsearch large ones
 */
static unsigned long ngram3bin_like__yz(ngram3 find, const struct ngram3map *m,
					ngram3 **res, unsigned long rescnt,
					ngram3bin_index *idx)
{
#	define SPAN_LARGE 16 // arbitrary, somewhat-reasonable number
	uint32_t *span = idx->span;
	const ngram3 *mcur = m->m;
	while (*span)
	{
		if (*span < SPAN_LARGE)
		{
			// small span, search sequentially
			const ngram3 *mend = mcur + *span;
			while (mcur < mend)
			{
				if (mcur->id[1] == find.id[1] &&
				    mcur->id[2] == find.id[2])
				{
					if ((*res = ngram3_find_spacefor1more(*res, rescnt)))
						(*res)[rescnt++] = *mcur;
					mcur = mend;
					break;
				}
				mcur++;
			}
		}
		else
		{
			// large span, bsearch
			const ngram3 *bs;
			find.id[0] = mcur->id[0]; // first id must match(!)
			if ((bs = bsearch(&find, mcur, *span, sizeof *mcur, ngram3cmp)))
			{
				if ((*res = ngram3_find_spacefor1more(*res, rescnt)))
					(*res)[rescnt++] = *bs;
			}
			mcur += *span;
		}
		// mcur set to previous mcur + *span by this point
		span++;
	}
	return rescnt;
}

/*
 * sum ngram3 word frequencies in w.word[n].freq
 */
void ngramword_totalfreqs(struct ngramword w, const struct ngram3map *m)
{
	ngram3 *cur = m->m;
	const ngram3 *end = (ngram3*)((char*)cur + m->size);
	while (cur < end)
	{
		if (cur->id[0] < w.cnt) w.word[cur->id[0]].freq += cur->freq;
		if (cur->id[1] < w.cnt) w.word[cur->id[1]].freq += cur->freq;
		if (cur->id[2] < w.cnt) w.word[cur->id[2]].freq += cur->freq;
		cur++;
	}
	{
		unsigned long i, cnt = w.cnt;
		for (i = 0; i < cnt; i++)
			w.word[i].freq /= 2;
	}
}

/*
 * build an index that speeds out searches of (_,y,z) searches
 * count the spans of consecutive id[0]s in m
 * e.g. [(x,_,_),(x,_,_),(y,_,_),(z,_,_),(z,_,_),(z,_,_)]
 *        |_______|       |       |_______________|
 *            2           1               3
 */
int ngram3bin_index_init(ngram3bin_index *idx, const struct ngram3map *m, const struct ngramword *w)
{
	/*
         * allocate enough space to hold a counter for every existing unique word,
	 * even though not every word may necessarily be present in id[0]
         */
	idx->span = malloc((w->cnt + 1) * sizeof *idx->span);
	if (idx->span)
	{
		unsigned long spanidx = 0,
                              spancnt = 1;
		const ngram3 *cur = m->m;
		const ngram3 *end = (ngram3*)((char*)cur + m->size);
		const ngram3 *nxt = cur+1;
		while (nxt < end)
		{
			if (cur->id[0] == nxt->id[0])
			{
				spancnt++;
			}
			else
			{
				idx->span[spanidx] = spancnt;
				spanidx++;
				spancnt = 1;
			}
			cur = nxt;
			nxt++;
		}
		idx->span[spanidx] = spancnt;
		idx->span[spanidx+1] = 0; // sentinel
	}
	return !!idx->span;
}

void ngram3bin_index_fini(ngram3bin_index *idx)
{
	free(idx->span);
}

void ngram3bin_fini(struct ngram3map m)
{
	munmap(m.m, m.size);
	close(m.fd);
}

#ifdef TEST

int main(void)
{
	const char *path = "ngram3.bin";
	struct ngram3map m = ngram3bin_init(path, 0);
	const ngram3 find = { 5, 6, 7, 0 };
	printf("map %llu bytes (%llu ngram3s)\n", m.size, m.size / sizeof find);
	ngram3bin_find(find, m);
	ngram3bin_fini(m);
	return 0;
}

#endif

