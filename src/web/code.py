#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
web-based spill-chick front-end

setup:
	* ensure webserver user has
		* read access to ngram3.bin and word.bin files
		* write access to session/ directory
"""

def abspath(localpath):
	return os.path.join(os.path.dirname(__file__), localpath)

import os, sys
from itertools import dropwhile
from time import time
import web
from web import form
import logging

logger = logging.getLogger('spill-chick')

sys.path.append(abspath('..'))
from chick import Chick
from doc import Doc

web.config.debug = True

urls = ( '/.*', 'check' )

app = web.application(urls, globals())
session = web.session.Session(app, web.session.DiskStore(abspath('session')),
		initializer={'target':None, 'skip':[], 'replacements':[]})
render = web.template.render(abspath('templates/'), base='base', globals=globals(), cache=False)
application = app.wsgifunc()
chick = Chick()

class check:

	def GET(self):
		session.kill()
		return render.check('', [], [], 0, [])

	def POST(self):
		start_time = time()
		text = web.input().get('text', '').decode('utf8')
		lines = text.split('\r\n')

		act = web.input().get('act', '')
		if act == 'Replace':
			replacement_index = int(web.input().get('replacement_index', '0'))
			if replacement_index:
				d = Doc(lines, chick.w)
				replacements = session.get('replacements')
				if replacement_index <= len(replacements):
					replacement = replacements[replacement_index-1]
					d.applyChanges(replacement)
					text = str(d)
					lines = d.lines
					logger.debug('after replacement lines=%s' % (lines,))
		elif act == 'Skip to next...':
			session['skip'].append(session['target'])
		elif act == 'Done':
			# nuke target, replacements, skip, etc.
			session.kill()

		sugg2 = []
		suggs = []
		suggestions = []
		replacements = []

		if act and act != 'Done':
			logger.debug('suggest(lines=%s)' % (lines,))
			suggestions = list(chick.suggest(lines, 5, session['skip']))
			if not suggestions:
				target,suggs,sugg2 = None,[],[]
			else:
				off = [len(l)+1 for l in lines]
				lineoff = [0]+[sum(off[:i]) for i in range(1,len(off)+1)]
				for target,suggs in suggestions:
					replacements += suggs
					sugg2 += [
						(#' '.join(x[0][0] for x in s), # string being replaced
						' '.join(x[1] for x in s), # replacement
						s[0][0][3], # beginning index
						s[-1][0][3] + len(s[-1][0][0])) # length of replacement
							for s in suggs if s]

			session['target'] = target
			session['replacements'] = replacements

		elapsed = round(time() - start_time, 2)
		return render.check(text, sugg2, lines, elapsed, suggestions)

if  __name__ == '__main__':
	app.run()

