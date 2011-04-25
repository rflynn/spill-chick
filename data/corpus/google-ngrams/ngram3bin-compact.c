/* ex: set ts=8 noet: */
/*
 * Copyright 2011 Ryan Flynn <parseerror+github@gmail.com>
 *
 * google's data has duplicate ngrams(!)
 * sort our ngram.bin file's entries, then merge/sum
 *
 */

#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <limits.h>
#include <arpa/inet.h>
#include "ngram3bin.h"

static void sortfile(const struct ngram3map *m)
{
	size_t nmemb = m->size / sizeof(ngram3);
	printf("%s:%u qsort(%p, %zu, %zu, %p);\n",
		__func__, __LINE__, (void*)m->m, nmemb, sizeof(ngram3), (void*)ngram3cmp);
	qsort(m->m, nmemb, sizeof(ngram3), ngram3cmp);
}

/*
 * ngram3map.m is a big mmap array of ngram3
 * it's been sorted, we want to merge consecutive identical ids into a single one, summing the freq field
 */
static void mergefile(const struct ngram3map *m)
{
	char *buf = malloc(1024 * 1024);
	ngram3 *rd = ngram3map_start(m);
	const ngram3 *end = ngram3map_end(m);
	unsigned long uniqcnt = 1;
	FILE *f = fopen("ngram3.bin.sort", "w");
	ngram3 wr = *rd;
	perror("fopen");
	rd++;
	setvbuf(f, buf, _IOFBF, 1024 * 1024);
	perror("setvbuf");
	while (rd < end)
	{
		if (rd->id[0] == wr.id[0] &&
		    rd->id[1] == wr.id[1] &&
		    rd->id[2] == wr.id[2])
		{
			wr.freq += rd->freq;
		}
		else
		{
			fwrite(&wr, sizeof wr, 1, f);
			wr = *rd;
			uniqcnt++;
		}
		rd++;
	}
	printf("%s:%u\n", __func__, __LINE__);

	printf("merged into %lu ngram3s...\n", uniqcnt);
	printf("saving...\n");

	fclose(f);
	perror("fclose");
	free(buf);
}

int main(void)
{
	const char *path = "ngram3.bin";
	struct ngram3map m = ngram3bin_init(path);
	printf("map %llu bytes (%llu ngram3s)\n", m.size, m.size / sizeof(ngram3));
	printf("sorting...\n");
	sortfile(&m);
	printf("merging...\n");
	mergefile(&m);
	printf("done.\n");
	ngram3bin_fini(m);
	return 0;
}

