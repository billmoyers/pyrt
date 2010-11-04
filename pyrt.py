#! /usr/bin/python

import gtk
import sys

import cookielib
import urllib
import urllib2

import re

class Ticket:
	parseRegex = re.compile(r'^(?P<id>\d+): (?P<title>.*)$')
	
	def __init__(self):
		self.id = None
		self.title = ''
		
	@staticmethod
	def parse(text):
		t = Ticket()
		m = re.search(Ticket.parseRegex, text)
		if m != None:
			gd = m.groupdict()
			
			t.id = gd['id']
			t.title = gd['title']
			return t
			
		else:
			return None

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
		self.url = url 
		self.username = username
		self.password = password
		self.ticketItems = {}
		
	def on_quit(self, data):
		sys.exit(1)

	def on_popup_menu(self, status, button, time):
		for t, mi in self.ticketItems.items():
			self.menu.remove(mi)
	
		tickets = self.getTickets()
		for t in reversed(tickets):
			mi = self.ticketItems[t] = gtk.MenuItem(t.title)
			self.menu.add(mi)
			self.menu.reorder_child(mi, 0)
		
		self.menu.popup(None, None, None, button, time)
		self.menu.show_all()
		
	def on_preferences(self, data):
		print 'preferences'

	def on_about(self, data):
		dialog = gtk.AboutDialog()
		dialog.set_name('PyRT')
		dialog.set_version('0.0.1')
		dialog.set_comments('A Python RequestTracker tray app.')
		dialog.set_website('')
		dialog.run()
		dialog.destroy()
		
	def getTickets(self):
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
		except urllib2.URLError:
			pass
		
		url = self.url + '/REST/1.0/search/ticket/' 
		data = urllib.urlencode({
			'user' : self.username,
			'pass' : self.password,
			'query' : "Owner='__CurrentUser__' AND (Status='new' OR Status='open')",
			'orderby' : 'Priority'
		})
		login = urllib2.Request(url, data)
		tickets = []
		try:
			response = urllib2.urlopen(login)
			tickets = [t for t in [Ticket.parse(line) for line in response.read().splitlines()] if t != None]
		except urllib2.URLError:
			pass
		
		return tickets

if __name__ == '__main__':
		icon = RTStatusIcon(*sys.argv[1:])
		gtk.main()
