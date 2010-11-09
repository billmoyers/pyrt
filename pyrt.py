#! /usr/bin/python

import gtk
import gobject
import sys
import webbrowser
import threading
import pango

from rt import RT, Query, Ticket

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
			('Quit', gtk.STOCK_QUIT, '_Quit', None, 'Quit', self.on_quit)
		]
		ag = gtk.ActionGroup('Actions')
		ag.add_actions(actions)
		self.manager = gtk.UIManager()
		self.manager.insert_action_group(ag, 0)
		self.manager.add_ui_from_string(menu)
		self.menu = self.manager.get_widget('/Menubar/Menu/About').props.parent
		self.set_tooltip('RequestTracker')
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
		self.poppedUp = False
		self.query = self.queries[0]
		self.getTickets()
		for t in self.tickets:
			t.seen = True
		self.set_blinking(False)

		self.lock = threading.Lock()			
		self.thread = threading.Thread(
			target = lambda : gobject.timeout_add(60*1000, self.refresh),
			group = None)
		self.thread.setDaemon(True)
		self.thread.start()
			
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
				
			mi = gtk.MenuItem(s)
			if not t.seen:
				mi.get_children()[0].modify_font(
					pango.FontDescription("bold"))
				
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
		self.poppedUp = True
		
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
	 	try:
			tickets = self.rt.getTickets(self.query)
		except Exception, ex:
		 	tickets = []
			self.set_tooltip(str(ex))
			self.set_blinking(True);
			return
		
		for t in tickets:
			for t2 in self.tickets:
				if t.id == t2.id:
					if t2.seen:
						t.seen = t2.LastUpdated == t.LastUpdated
					else:
						t.seen = False
					
		for t in tickets:
			if not t.seen:
				self.set_blinking(True)
				break
		
		if len(self.tickets) == 0 or not self.get_blinking():
			self.set_tooltip('%s ticket(s) in %s query.' % (len(tickets), self.query.name))
		else:
			self.set_tooltip('%s/%s updated ticket(s) in %s query.' % 
				(len([t for t in tickets if not t.seen]), len(tickets), self.query.name))

		self.tickets = tickets

	def refresh(self):
		self.lock.acquire()
		self.getTickets()
		self.lock.release()
		return True
		
	def close(self):
		pass

if __name__ == '__main__':
	icon = RTStatusIcon(*sys.argv[1:])
	gtk.main()
