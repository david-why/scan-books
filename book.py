#!/usr/bin/python3
from __future__ import print_function
from threading import Thread
from os import path
from time import sleep, time
import argparse
import sys
import json

if sys.version_info.major == 2:
	input = raw_input

ap = argparse.ArgumentParser(prog=sys.argv[0], description='Fetches book information from ISBNs.', epilog='The FILEs are CSV-files by default. Additionally, they can be prefixed with "DB:", which means that it is a SQLite 3 database. In this case, the table name is specified after the *last* forward slash (/).\n\nIf the input file is a database. then the input table should contain a column called "payload" or "isbn".\n\nIf the output file is a database, the output table would contain four columns: timestamp, isbn, name and author.')
g = ap.add_mutually_exclusive_group()
g.add_argument('--wait-for-enter', '-w', action='store_true', dest='wait_enter', help='Wait for Enter key to be pressed before fetching data from file. Is the default.', default=True)
g.add_argument('--auto-fetch', '-a', action='store_false', dest='wait_enter', help='Autumatically fetch book data when file is changed.')
ap.add_argument('--input', '-i', type=str, help='The file to read the ISBN data. Default: "DB:barcodes.db/barcodes"', default='DB:barcodes.db/barcodes', required=False, dest='infile', metavar='FILE')
ap.add_argument('--output', '-o', type=str, help='The file to save book data fetched. Default: "DB:books.db/books"', default='DB:books.db/books', required=False, dest='outfile', metavar='FILE')
args = ap.parse_args()

if args.infile.startswith('DB:'):
	parts = args.infile[3:].split('/')
	if len(parts) < 2:
		print('Please specify the input table name after the database name, seperated by a forward slash (/).')
		sys.exit(1)
	inname = '/'.join(parts[:-1])
	intable = parts[-1]
	indb = True
	del parts
else:
	inname = args.infile
	indb = False
if args.outfile.startswith('DB:'):
	parts = args.outfile[3:].split('/')
	if len(parts) < 2:
		print('Please specify the output table name after the database name, seperated by a forward slash (/).')
		sys.exit(1)
	outname = '/'.join(parts[:-1])
	outtable = parts[-1]
	outdb = True
	del parts
else:
	outname = args.outfile
	outdb = False

try:
	import requests
except ImportError:
	print('Requests module needed for this program!')
	sys.exit(1)
try:
	from bs4 import BeautifulSoup
except ImportError:
	print('BeautifulSoup4 needed for this program!')
	sys.exit(1)

if not path.isfile(inname):
	print('Input file does not exist or is not a regular file!')
	sys.exit(1)

if not path.isfile(outname) and not outdb:
	with open(outname, 'w') as f:
		f.write('timestamp,isbn,name,author\n')


def check_isbn(isbn):
	_ = {'0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'X': 10}
	return isinstance(isbn, str) and len(isbn) == 13 and isbn.startswith('978') and (int(isbn[3]) * 1 + int(isbn[4]) * 2 + int(isbn[5]) * 3 + int(isbn[6]) * 4 + int(isbn[7]) * 5 + int(isbn[8]) * 6 + int(isbn[9]) * 7 + int(isbn[10]) * 8 + int(isbn[11]) * 9 + _[isbn[12]] * 10) % 11 == 0 and (int(isbn[3]) * 10 + int(isbn[4]) * 9 + int(isbn[5]) * 8 + int(isbn[6]) * 7 + int(isbn[7]) * 6 + int(isbn[8]) * 5 + int(isbn[9]) * 4 + int(isbn[10]) * 3 + int(isbn[11]) * 2 + _[isbn[12]] * 1) % 11 == 0


def load_from_isbn(isbn, _):
	if outdb:
		outconn = sqlite3.connect(outname)
		cur = outconn.cursor()
	print('Finding: %s' % isbn, end='', flush=True)
	res = requests.get('https://book.douban.com/isbn/%s/' % isbn, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36'})
	#print(res.url, res.status_code)
	soup = BeautifulSoup(res.text, 'html.parser')
	data = soup.find('script', attrs={'type': 'application/ld+json'})
	if data is None:
		print('\rNot found: %s' % isbn)
		title = input('Title: ')
		if not title:
			cur.execute('INSERT INTO __notfound__ VALUES (?)', (isbn, ))
			outconn.commit()
			print('\r', end='')
			if outdb:
				cur.close()
				outconn.close()
			return None
		else:
			author = input('Author: ')
			d = {'name': title, 'author': [{'name': author}]}
	else:
		print('\rFound: %s  ' % isbn)
		d = json.loads(data.string.replace('\n', ''))
	if outdb:
		cur.close()
		outconn.close()
	fetched.add(isbn)
	return d


def bg():
	if outdb:
		outconn = sqlite3.connect(outname)
		cur = outconn.cursor()
	while True:
		isbn = input()
		d = load_from_isbn(isbn, cur if outdb else None)
		if outdb:
			cur.execute('INSERT INTO %s VALUES (?, ?, ?, ?)' % outtable, (time(), isbn, d['name'], ' '.join([x['name'] for x in d['author']])))
			outconn.commit()
		else:
			with open(outname, 'a') as f:
				f.write('%s,%s,%s%s%s,%s%s%s\n' % (time(), isbn, '"' if ',' in d['name'] else '', d['name'], '"' if ',' in d['name'] else '', '"' if ',' in ' '.join([x['name'] for x in d['author']]) else '', ' '.join([x['name'] for x in d['author']]), '"' if ',' in ' '.join([x['name'] for x in d['author']]) else ''))


fetched = set()
if indb or outdb:
	try:
		import sqlite3
	except ImportError:
		print('Sqlite3 needed for this program!')
		sys.exit(1)
if indb:
	inconn = sqlite3.connect(inname)
	cur = inconn.cursor()
	if (intable, ) not in cur.execute('SELECT tbl_name FROM sqlite_master WHERE type="table"').fetchall():
		print('The table %s not found in database' % intable)
		sys.exit(1)
	#cur.execute('SELECT name FROM PRAGMA_TABLE_INFO("%s") WHERE name="payload"' % intable)
	cur.execute('PRAGMA table_info(%s)' % intable)
	columns = [x[1] for x in cur.fetchall()]
	if 'payload' in columns:
		incol = 'payload'
	elif 'isbn' in columns:
		incol = 'isbn'
	else:
		print('No column called "payload" or "isbn" in the input database!')
		sys.exit(1)
	cur.close()
	del cur
else:
	with open(inname, 'r') as f:
		cols = f.readline().strip().split(',')
		data = [x.strip().split(',') for x in f.readlines()]
	if 'payload' in cols:
		incol = cols.index('payload')
	elif 'isbn' in cols:
		incol = cols.index('isbn')
	else:
		print('No column called "payload" or "isbn" in the input CSV-file!')
		sys.exit(1)
	del cols
if outdb:
	outconn = sqlite3.connect(outname)
	cur = outconn.cursor()
	cur.execute('CREATE TABLE IF NOT EXISTS %s ( timestamp REAL, isbn TEXT, name TEXT, author TEXT )' % outtable)
	cur.execute('CREATE TABLE IF NOT EXISTS __notfound__ ( isbn TEXT )')
	outconn.commit()
	cur.execute('SELECT isbn FROM %s' % outtable)
	fetched = set([x[0] for x in cur.fetchall()])
	cur.execute('SELECT isbn FROM __notfound__')
	fetched = fetched.union([x[0] for x in cur.fetchall()])
	cur.close()
	del cur
else:
	with open(outname) as f:
		data = f.readlines()[1:]
	for line in data:
		if len(line) <= incol:
			continue
		fetched.add(line[incol])
	del data
#print(fetched)

t = Thread(target=bg)
t.setDaemon(True)
t.start()
olddata = []
while True:
	if args.wait_enter:
		input()
		print('\x1b[1A', end='')
	if indb:
		cur = inconn.cursor()
		cur.execute('SELECT %s FROM %s' % (incol, intable))
		isbns = [x[0] for x in cur.fetchall()]
	else:
		isbns = []
		with open(inname, 'r') as f:
			data = [x.strip() for x in f.readlines()]
		n = 2
		for line in data[1:]:
			if len(line.split(',')) <= incol:
				print('Warning: CSV file line %i does not have enough items, passing' % n)
				n += 1
				continue
			isbns.append(line.split(',')[incol])
	isbns = [('978' + isbn) if len(isbn) == 10 else isbn for isbn in isbns]
	found = set()
	for isbn in isbns:
		if isbn not in fetched:
			if not check_isbn(isbn):
				print('NOT VALID: %s' % isbn)
				continue
			found.add(isbn)
	if outdb:
		cur = outconn.cursor()
	for isbn in found:
		d = load_from_isbn(isbn, cur if outdb else None)
		if not d:
			continue
		if outdb:
			cur.execute('INSERT INTO %s VALUES (?, ?, ?, ?)' % outtable, (time(), isbn, d['name'], ' '.join([x['name'] for x in d['author']])))
			outconn.commit()
		else:
			with open(outname, 'a') as f:
				f.write('%s,%s,%s%s%s,%s%s%s\n' % (time(), isbn, '"' if ',' in d['name'] else '', d['name'], '"' if ',' in d['name'] else '', '"' if ',' in ' '.join([x['name'] for x in d['author']]) else '', ' '.join([x['name'] for x in d['author']]), '"' if ',' in ' '.join([x['name'] for x in d['author']]) else ''))
	fetched = fetched.union(isbns)
	#if found:
	#	sleep(1)
	#else:
	#	sleep(0.5)


inconn.close()
outconn.close()
sys.exit(0)

