#! /usr/bin/python

import gtk
import gobject
import sys

import cookielib
import urllib
import urllib2

import re

import webbrowser

class Query:
	def __init__(self, name, desc, **query):
		self.name = name
		self.desc = desc
		self.query = query

class Ticket:
	parseRegex = re.compile(r'^(?P<key>[^:]+): (?P<value>.*)')
	
	def __init__(self):
		self.id = None
		self.title = ''
		self.seen = False
		
	@staticmethod
	def parse(text):
		tickets = []
		t = None
		for line in text.splitlines():
			if line == '--':
				if t != None:
					tickets.append(t)
				t = Ticket()
		
			else:
				m = re.search(Ticket.parseRegex, line)
				if m != None:
					if t == None: t = Ticket()
					gd = m.groupdict()
					k = gd['key']
					v = gd['value']
					if k == 'id':
						v = v.split('/')[1]
						t.__dict__[k] = v
					else:
						t.__dict__[k] = v
		
		if t != None:
			tickets.append(t)
			
		return tickets
		
class RT:
	def __init__(self, url, username, password):
		self.url = url
		self.username = username
		self.password = password
		
	def authenticate(self):
		cj = cookielib.LWPCookieJar()
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
		opener.addheaders = [('User-agent', 'Mozilla/5.0')]
		opener.addheaders = [('Content-type', 'form-data')]
		urllib2.install_opener(opener)
		data = {'user' : self.username, 'pass' : self.password}
		ldata = urllib.urlencode(data)
		login = urllib2.Request(self.url, ldata)
		try:
			response = urllib2.urlopen(login)
			return True
		except urllib2.URLError:
			return False
		
	def getTickets(self, query):
		url = self.url + '/REST/1.0/search/ticket/' 
		data = query.query.copy()
		data['user'] = self.username
		data['pass'] = self.password
		data['format'] = 'l'
		data = urllib.urlencode(data)
		login = urllib2.Request(url, data)
		tickets = []
		try:
			response = urllib2.urlopen(login)
			tickets = list(reversed(Ticket.parse(response.read())))
			if len(tickets) > query.query['limit']:
				tickets = tickets[:query.query['limit']]
		except urllib2.URLError:
			pass
		
		return tickets

class RTStatusIcon (gtk.StatusIcon):
	def __init__(self, url, username, password):
		gtk.StatusIcon.__init__(self)
		self.set_from_file('pyrt-icon.png')
		menu = '''
			<ui>
				<menubar name="Menubar">
					<menu action="Menu">
						<separator/>
						<menuitem action="Preferences"/>
						<menuitem action="About"/>
						<menuitem action="Quit"/>
					</menu>
				</menubar>
			</ui>
		'''
		actions = [
			('Menu',  gtk.STOCK_PREFERENCES, 'Menu'),
			('Preferences', gtk.STOCK_PREFERENCES, '_Preferences...', None, 'Change PyRT settings.', self.on_preferences),
			('About', gtk.STOCK_ABOUT, '_About...', None, 'About PyRT', self.on_about),
			('Quit', gtk.STOCK_QUIT, '_Quit', None, 'Quit.', self.on_quit)
		]
		ag = gtk.ActionGroup('Actions')
		ag.add_actions(actions)
		self.manager = gtk.UIManager()
		self.manager.insert_action_group(ag, 0)
		self.manager.add_ui_from_string(menu)
		self.menu = self.manager.get_widget('/Menubar/Menu/About').props.parent
		self.set_tooltip('Python RequestTracker App')
		self.set_visible(True)
		self.connect('popup-menu', self.on_popup_menu)
		self.rt = RT(url, username, password)
		self.menuItems = []
		self.tickets = []
		self.queries = [
			Query('Default', 'Top 20 Most Recently Updated Tickets I Own', 
				query = "Owner='__CurrentUser__' AND (Status='new' OR Status='open')",
				limit = 20,
				orderby = 'LastUpdated')]
		self.query = self.queries[0]
		self.getTickets()
		for t in self.tickets:
			t.seen = True
			
		gobject.timeout_add(60*1000, self.refresh)
			
	def on_quit(self, data):
		sys.exit(1)

	def on_popup_menu(self, status, button, time):
		for mi in self.menuItems:
			self.menu.remove(mi)
		self.menuItems = []
		
		i = 0
	
		for t in self.tickets:
			s = t.Subject
			if len(s) > 30:
				s = s[0:30]+'...'
				
			if not t.seen:
				mi = gtk.ImageMenuItem(s)
				img = gtk.Image()
				img.set_from_stock(gtk.STOCK_YES, gtk.ICON_SIZE_MENU)
				mi.set_image(img)
			else:
				mi = gtk.MenuItem(s)
				
			t.seen = True
			mi.set_tooltip_markup('''<b>Queue</b>: %s
<b>Status</b>: %s
<b>Last Updated</b>: %s''' % (t.Queue, t.Status, t.LastUpdated))
			mi.set_data('ticket', t)
			mi.connect('activate', self.on_activate)
			self.menu.insert(mi, i)
			self.menuItems.append(mi)
			i += 1

		mi = gtk.SeparatorMenuItem()
		self.menu.insert(mi, i)
		self.menuItems.append(mi)
		i += 1
		
		for v in self.queries:
			mi = gtk.CheckMenuItem(v.name)
			mi.set_draw_as_radio(True)
			mi.set_tooltip_text(v.desc)
			mi.set_data('query', v)
			if v == self.query:
				mi.set_active(True)
			self.menu.insert(mi, i)
			self.menuItems.append(mi)	
			i += 1
		
		mi = gtk.SeparatorMenuItem()
		self.menu.insert(mi, i)
		self.menuItems.append(mi)
		
		self.menu.show_all()
		self.menu.popup(None, None, None, button, time)
		self.set_blinking(False)
		
	def on_activate(self, menuitem):
		t = menuitem.get_data('ticket')
		if t != None:
			webbrowser.open(self.rt.url+'/Ticket/Display.html?id='+t.id)

		q = menuitem.get_data('query')
		if q != None:
			self.query = q
			self.getTickets()
		
	def on_preferences(self, data):
		print 'preferences'

	def on_about(self, data):
		dialog = gtk.AboutDialog()
		dialog.set_name('PyRT')
		dialog.set_version('0.1.0')
		dialog.set_comments('A Python RequestTracker tray app.')
		dialog.set_website('')
		dialog.run()
		dialog.destroy()
		
	def getTickets(self):
		tickets = self.rt.getTickets(self.query)
		
		for t in tickets:
			for t2 in self.tickets:
				if t.id == t2.id:
					if t2.seen:
						t.seen = t2.LastUpdated == t.LastUpdated
					else:
						t.seen = False
					
		self.tickets = tickets
		
		for t in tickets:
			if not t.seen:
				self.set_blinking(True)

	def refresh(self):
		self.getTickets()
		return True

if __name__ == '__main__':
		icon = RTStatusIcon(*sys.argv[1:])
		gtk.main()
