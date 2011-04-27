#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
web-based spill-chick front-end
"""

import os, sys
import web
from web import form
import logging
logging.basicConfig(level=logging.CRITICAL, stream=sys.stderr)
logging.disable(level=logging.CRITICAL)

def abspath(localpath):
	return os.path.join(os.path.dirname(__file__), localpath)

sys.path.append(abspath('..'))

from chick import Chick

web.config.debug = True

urls = ( '/.*', 'check' )

app = web.application(urls, globals())
session = web.session.Session(app, web.session.DiskStore(abspath('session')),
		initializer={'target':None, 'skip':[]})
render = web.template.render(abspath('templates/'), base='base', globals=globals(), cache=False)
application = app.wsgifunc()

chick = Chick()

class check:
	def GET(self):
		return render.check('', [], [])
	def POST(self):
		text = web.input(text='')['text'].decode('utf8')
		lines = text.split('\n')

		"""
Session: &lt;Storage {&#39;skip&#39;: [], &#39;replacements&#39;: [[((u&#39;write&#39;, 0, 2, 6), u&#39;right&#39;)]], &#39;target&#39;: None, &#39;session_id&#39;: &#39;ed6666f204dbdaf78e7b4812f2c34b7bcb799cc7&#39;, &#39;ip&#39;: u&#39;127.0.0.1&#39;}&gt;
web.input: <Storage {'text': u'i was write', 'act': u'Replace', 'target': u'(foo)', 'replacement': u'1'}>
		"""
		act = ''
		if act == 'Replace':
			replacement = None
			if replacement:
				d = Doc(lines, chick.w)
				d.applyChanges(session['replacements'][replacement])
				text = str(d)
				lines = d.lines
		elif act == 'Skip to next...':
			pass

		suggestions = []
		suggestions = list(chick.suggest(lines))
		sugg2 = [(' '.join(x[1] for x in s), # string-ized for display
			s[0][0][3], # beginning index
			s[-1][0][3]+len(s[-1][0][0])) # ending index for selection
			for s in suggestions]
		session['replacements'] = suggestions
		return render.check(text, sugg2, lines)

if  __name__ == '__main__':
	app.run()

