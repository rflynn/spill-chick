// ex: set ts=8 noet:

// Convert text-based CSV format "x,y,z,freq" to packed little-endian binary format
//
// Usage: gzip -dc *.ids.gz | ./import2bin-ngram > ngram3.bin.orig.c
//
// Port from import2bin.py; it was just too slow. We're >10x faster.

#include <locale.h>
#include <wchar.h>
#include <wctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <inttypes.h>
#include <assert.h>

typedef struct {
#pragma pack(push, 1)
	uint32_t id[3],
                 freq;
#pragma pack(pop)
} ngram3;

// "id0,id1,id2,freq" -> ngram3
int line2ng(const wchar_t *line, ngram3 *ng)
{
	return swscanf(line,
		L"%" SCNu32 ",%" SCNu32 ",%" SCNu32 ",%" SCNu32 "\n",
		ng->id+0, ng->id+1, ng->id+2, &ng->freq) == 4;
}

// stdin -> [ngram3(...),...]
int main(void)
{
	// we're going to be writing out 100s of MB in a batch; use a large buffer
#       define BUFLEN 32 * 1024 * 1024L
	static wchar_t line[1024];
	char *buf = malloc(BUFLEN);
	ngram3 ng;

	assert(sizeof ng == 16 && "ensure packing");

	if (!setlocale(LC_CTYPE, ""))
	{
		fprintf(stderr, "Can't set the specified locale! Check LANG, LC_CTYPE, LC_ALL.\n");
		return 1;
	}

	// fully buffer stdout
	setvbuf(stdout, buf, _IOFBF, BUFLEN);

	// parse lines from stdin, write packed binary ngram to stdout, errors to stderr
	while (fgetws(line, sizeof line / sizeof line[0], stdin))
	{
		if (line2ng(line, &ng))
		{
			fwrite(&ng, sizeof ng, 1, stdout);
		}
		else
		{
			fprintf(stderr, "invalid line '%ls'\n", line);
		}
	}

	free(buf);

	return 0;
}

