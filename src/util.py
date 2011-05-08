
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

class TokenDiff:
	"""
	represent the modification of zero or more 'old' (original) tokens and their
	'new' (proposed) replacement. solves the problem of tracking inter-token changes.
	change: TokenDiff([tok], [tok'])
	insert: TokenDiff([], [tok'])
	delete: TokenDiff([tok], [])
	split:  TokenDiff([tok], [tok',tok'])
	merge:  TokenDiff([tok,tok], [tok'])
	"""
	def __init__(self, old, new, damlev):
		self.old = list(old)
		self.new = list(new)
		self.damlev = damlev # Damerau-Levenshtein distance
	def oldtoks(self): return [t[0] for t in self.old]
	def newtoks(self): return [t[0] for t in self.new]
	def __str__(self):
		return 'TokenDiff((%s,%s))' % (self.old, self.new)
	def __repr__(self):
		return str(self)
	def __eq__(self, other):
		return self.old == other.old and \
		       self.new == other.new

class NGramDiff:
	"""
	represent a list of tokens that contain a single change, represented by a TokenDiff.
	alternative, think of it as an acyclic directed graph with a single branch and merge
	conceptually:
		  prefix   diff    suffix
		O---O---O---O---O---O---O
	                 \     /
		          `-O-'
	"""
	def __init__(self, prefix, diff, suffix, g, oldfreq=None, newfreq=None):
		self.prefix = list(prefix)
		self.diff = diff
		self.suffix = list(suffix)
		self.oldfreq = g.freq(self.oldtoks()) if oldfreq is None else oldfreq
		self.newfreq = g.freq(self.newtoks()) if newfreq is None else newfreq
	def old(self): return self.prefix + self.diff.old + self.suffix
	def new(self): return self.prefix + self.diff.new + self.suffix
	def oldtoks(self): return [t[0] for t in self.old()]
	def newtoks(self): return [t[0] for t in self.new()]
	def __repr__(self):
		return str(self)
	def __str__(self):
		return 'NGramDiff(%s,%s,%s)' % (self.prefix, self.diff, self.suffix)
	def __eq__(self, other):
		return self.diff == other.diff and \
		       self.prefix == other.prefix and \
		       self.suffix == other.suffix
	def __lt__(self, other):
		return other.newfreq < self.newfreq

class NGramDiffScore:
	# based on our logarithmic scoring below
	DECENT_SCORE = 5.0
	GOOD_SCORE = 10.0
	"""
	decorate an NGramDiff obj with scoring
	"""
	def __init__(self, ngd, p, score=None):
		self.ngd = ngd
		self.score = self.calc_score(ngd, p) if score is None else score
		if score:
			self.ediff = score
	def calc_score(self, ngd, p):
		ediff = self.similarity(ngd, p)
		self.ediff = ediff
		sl = int(ngd.diff.new and ngd.diff.old and ngd.diff.new[0][0] == ngd.diff.old[0][0])
		score = ((log(max(1, ngd.newfreq - ngd.oldfreq)) -
			  (2 + ediff + (sl if ediff else 0))) + (ngd.diff.damlev - ediff))
		return score
	def __str__(self):
		return 'NGramDiffScore(score=%4.1f ngd=%s)' % (self.score, self.ngd)
	def __repr__(self):
		return str(self)
	def __eq__(self, other):
		return other.score == self.score
	def __lt__(self, other):
		return other.score < self.score
	def __add__(self, other):
		return NGramDiffScore(self.ngd, None, self.score + other.score)
	@staticmethod
	def overlap(s1, s2):
		"""
		given a list of sound()s, count the number that do not match
		 	 1  2  3  4  5  6
			'T AH0 M AA1 R OW2'
			'T UW1 M'
                 	 =     =
			 6 - 2 = 4
		"""
		mlen = max(len(s1), len(s2))
		neq = sum(map(lambda x: x[0] != x[1], zip(s1, s2)))
		return mlen - neq
	def similarity(self, ngd, p):
		"""
		return tuple (effective difference, absolute distance)
		given a string x, calculate a similarity distance for y [0, +inf).
		smaller means more similar. the goal is to identify promising
		alternatives for a given token within a document; we need to consider
		the wide range of possible errors that may have been made
		"""
		x = ' '.join(ngd.diff.oldtoks())
		y = ' '.join(ngd.diff.newtoks())
		# tokens identical
		if x == y:
			return 0
		damlev = ngd.diff.damlev
		sx,sy = p.phraseSound([x]),p.phraseSound([y])
		if sx == sy and sx:
			# sound the same, e.g. there/their. consider these equal.
			return damlev
		# otherwise, calculate phonic/edit difference
		return max(damlev,
			   min(NGramDiffScore.overlap(sx, sy),
			       abs(len(x)-len(y))))

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

