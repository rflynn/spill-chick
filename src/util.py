
"""
classes and utility functions that are used by everyone
"""

from operator import itemgetter
from math import sqrt,log

# convenience functions
def rsort(l, **kw): return sorted(l, reverse=True, **kw)
def rsort1(l): return rsort(l, key=itemgetter(1))
def rsort2(l): return rsort(l, key=itemgetter(2))
def sort1(l): return sorted(l, key=itemgetter(1))
def sort2(l): return sorted(l, key=itemgetter(2))
def flatten(ll): return chain.from_iterable(ll)
def zip_longest(x, y, pad=None):
	x, y = list(x), list(y)
	lx, ly = len(x), len(y)
	if lx < ly:
		x += [pad] * (ly-lx)
	elif ly < lx:
		y += [pad] * (lx-ly)
	return zip(x, y)

def damerau_levenshtein(seq1, seq2):
    """Calculate the Damerau-Levenshtein distance between sequences.
    
    This distance is the number of additions, deletions, substitutions,
    and transpositions needed to transform the first sequence into the
    second. Although generally used with strings, any sequences of
    comparable objects will work.
    
    Transpositions are exchanges of *consecutive* characters; all other
    operations are self-explanatory.
    
    This implementation is O(N*M) time and O(M) space, for N and M the
    lengths of the two sequences.
    
    >>> dameraulevenshtein('ba', 'abc')
    2
    >>> dameraulevenshtein('fee', 'deed')
    2
    
    It works with arbitrary sequences too:
    >>> dameraulevenshtein('abcd', ['b', 'a', 'c', 'd', 'e'])
    2
    """
    # codesnippet:D0DE4716-B6E6-4161-9219-2903BF8F547F
    # Conceptually, this is based on a len(seq1) + 1 * len(seq2) + 1 matrix.
    # However, only the current and two previous rows are needed at once,
    # so we only store those.
    oneago = None
    thisrow = range(1, len(seq2) + 1) + [0]
    for x in xrange(len(seq1)):
        # Python lists wrap around for negative indices, so put the
        # leftmost column at the *end* of the list. This matches with
        # the zero-indexed strings and saves extra calculation.
        twoago, oneago, thisrow = oneago, thisrow, [0] * len(seq2) + [x + 1]
        for y in xrange(len(seq2)):
            delcost = oneago[y] + 1
            addcost = thisrow[y - 1] + 1
            subcost = oneago[y - 1] + (seq1[x] != seq2[y])
            thisrow[y] = min(delcost, addcost, subcost)
            # This block deals with transpositions
            if (x > 0 and y > 0 and seq1[x] == seq2[y - 1] and seq1[x-1] == seq2[y] and seq1[x] != seq2[y]):
                thisrow[y] = min(thisrow[y], twoago[y - 2] + 1)
    return thisrow[len(seq2) - 1]

