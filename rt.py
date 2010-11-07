import cookielib
import urllib
import urllib2
import re

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
		self.cj = cookielib.LWPCookieJar()
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))
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
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))
		urllib2.install_opener(opener)
		#data['user'] = self.username
		#data['pass'] = self.password
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
