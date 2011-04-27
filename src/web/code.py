#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
web-based spill-chick front-end
"""

def abspath(localpath):
	return os.path.join(os.path.dirname(__file__), localpath)

import os, sys
import web
from web import form
import logging

logger = logging.getLogger('spill-chick')
logger.setLevel(logging.DEBUG)

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
		#session['target'] = None
		#session['replacements'] = []
		#session['skip'] = []
		return render.check('', [], [])

	def POST(self):
		text = web.input().get('text', '').decode('utf8')
		lines = text.split('\r\n')
		sugg2 = []

		"""
Session: <Storage {'skip': [], 'replacements': [((u'yo', 0, 4, 20), u'you')], 'target': ((u'hell', 0, 0, 0), (u'their', 0, 1, 5), (u'how', 0, 2, 12)), 'session_id': 'cf92623f6f08ebdc1b4e383a02d48d33ad88b7a0', 'ip': u'127.0.0.1'}>
web.input: <Storage {'text': u'hell their. how are yo?', 'act': u'Check'}>
		"""

		act = web.input().get('act', '')
		if act == 'Replace':
			replacement_index = int(web.input().get('replacement_index', '0'))
			if replacement_index:
				d = Doc(lines, chick.w)
				replacements = session.get('replacements')
				if replacement_index <= len(replacements):
					replacement = [replacements[replacement_index-1]]
					d.applyChanges(replacement)
					text = str(d)
					lines = d.lines
					logger.debug('after replacement lines=%s' % (lines,))
		elif act == 'Skip to next...':
			session['skip'].append(session['target'])
		elif act == 'Done':
			session['target'] = None
			session['replacements'] = []
			session['skip'] = []

		sugg2 = []

		if act and act != 'Done':
			logger.debug('suggest(lines=%s)' % (lines,))
			suggestions = list(chick.suggest(lines, 5, session['skip']))
			if not suggestions:
				target,suggs,sugg2 = None,[],[]
			else:
				off = [len(l)+1 for l in lines]
				lineoff = [0]+[sum(off[:i]) for i in range(1,len(off)+1)]
				target,suggs = suggestions[0]
				sugg2 = [(s[1] if type(s[1]) == unicode else ' '.join(x[1] for x in s), # string-ized for display
					lineoff[s[0][1]] + s[0][3], # beginning index
					lineoff[s[0][1]] + s[0][3] + len(s[0][0])) # ending index for selection
					for s in suggs]
			session['target'] = target
			session['replacements'] = suggs

		return render.check(text, sugg2, lines)

if  __name__ == '__main__':
	app.run()

