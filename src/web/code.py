#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
web-based spill-chick front-end

setup:
	* mkdir session/
		(I tried adding it to the project but git can't hold empty directories and session/.gitignore kludge got deleted by the webserver, apparently)
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
		initializer={'target':None, 'skip':[], 'replacements':[], 'suggestions':[]})
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
					d.applyChanges([replacement])
					text = str(d)
					lines = d.lines
					logger.debug('after replacement lines=%s' % (lines,))
		elif act == 'Skip to next...':
			session['skip'].append(session['target'])
			session['suggestions'].pop(0)
		elif act == 'Done':
			# nuke target, replacements, skip, etc.
			session.kill()

		sugg2 = []
		suggs = []
		suggestions = []
		replacements = []

		if act and act != 'Done':
			suggestions = session['suggestions']
			if not suggestions:
				logger.debug('suggest(lines=%s)' % (lines,))
				suggestions = list(chick.suggest(lines, 5, session['skip']))
			if not suggestions:
				target,suggs,sugg2 = None,[],[]
			else:
				# calculate offsets based on line length so we can highlight target substring in <texarea>
				off = [len(l)+1 for l in lines]
				lineoff = [0]+[sum(off[:i]) for i in range(1,len(off)+1)]
				changes = suggestions[0]
				target = changes[0].ngd.oldtoks()
				for ch in changes:
					ngd = ch.ngd
					replacements.append(ngd)
					o = ngd.old()
					r = ngd.new()
					linestart = o[0][1]
					lineend = o[-1][1]
					start = o[0][3]
					end = o[-1][3] + len(o[-1][0])
					sugg2.append((' '.join(ngd.newtoks()),
						      lineoff[linestart] + start,
						      lineoff[lineend] + end))
			session['target'] = target
			session['replacements'] = replacements
			session['suggestions'] = suggestions

		elapsed = round(time() - start_time, 2)
		return render.check(text, sugg2, lines, elapsed, suggestions)

if  __name__ == '__main__':
	app.run()

