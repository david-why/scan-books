#!/usr/bin/python3
from __future__ import print_function
from os import path
import argparse
import sys

ap = argparse.ArgumentParser(prog=sys.argv[0], description='Reads a SQLite 3 table into a HTML table.')
ap.add_argument('-f', '--from-file', type=str, help='Filename of the SQLite 3 database.', required=True, dest='infile', metavar='DBFILE')
ap.add_argument('-t', '--from-table', type=str, help='Name of the table to convert.', required=True, dest='intable', metavar='TABLE')
ap.add_argument('-o', '--output', type=str, help='Output file name.', required=True, dest='outfile', metavar='FILE')
args = ap.parse_args()

if not path.isfile(args.infile):
	print('Input file does not exist!')
	sys.exit(1)

try:
	import sqlite3
except ImportError:
	print('Sqlite3 module required for this program!')
	sys.exit(1)
try:
	import pandas as pd
except ImportError:
	print('Pandas required for this program!')
	sys.exit(1)

pd.options.display.float_format = ' {:.2f}'.format
conn = sqlite3.connect(args.infile)
if (args.intable, ) not in conn.execute('SELECT tbl_name FROM sqlite_master WHERE type="table"').fetchall():
	print('Table %s not found!' % args.intable)
	sys.exit(1)

frame = pd.read_sql_query('SELECT name, author, isbn FROM %s' % args.intable, conn)
with open(args.outfile, 'w') as f:
	f.write(frame.to_html(index=False))

