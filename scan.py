#!/usr/bin/python3
from __future__ import print_function
import sys
from os import path, remove
from time import sleep, time
import argparse
ap = argparse.ArgumentParser(prog=sys.argv[0], description='Scans barcodes/qrcodes from PiCamera.')
g = ap.add_mutually_exclusive_group()
g.add_argument('--wait-for-enter', '-w', action='store_true', dest='wait_enter', help='Wait for Enter key to be pressed before scanning. Is the default.', default=True)
g.add_argument('--auto-scan', '-a', action='store_false', dest='wait_enter', help='Automatically scan all detected codes.')
ap.add_argument('-o', '--output', type=str, help='Output file to save the barcodes. If it is set to "DB:<file_path>", then see <file_path> as a SQLite 3 database name. The output will be saved in a table called "barcodes", with three columns: timestamp, type and payload. If not, then the file is CSV-style with the same columns. Default: "DB:barcodes.db"', default='DB:barcodes.db', required=False, dest='name')
args = ap.parse_args()

try:
	import picamera
except ImportError:
	print('This program can only be run on a RaspberryPi with PiCamera!')
	sys.exit(1)
try:
	import zbar
except ImportError:
	print('Zbar-py is required for this program!')
	sys.exit(1)
try:
	from PIL import Image
except ImportError:
	print('Pillow is required for this program!')
	sys.exit(1)
try:
	import numpy as np
except ImportError:
	print('Numpy is required for this program!')
	sys.exit(1)


#print(args)
if args.wait_enter:
	print('Waiting for Enter...')
else:
	print('Automatically scanning...')

if args.name.startswith('DB:'):
	name = args.name[3:]
	db = True
	import sqlite3
	conn = sqlite3.connect(name)
	cur = conn.cursor()
	cur.execute('CREATE TABLE IF NOT EXISTS barcodes ( "timestamp" REAL NOT NULL, "type" TEXT NOT NULL, "payload" TEXT NOT NULL )')
	conn.commit()
	cur.close()
else:
	name = args.name
	db = False
	if not path.isfile(name):
		with open(name, 'w') as f:
			f.write('timestamp,type,payload\n')

scan = zbar.Scanner()
cam = picamera.PiCamera()
olddata = []
while True:
	if args.wait_enter:
		input()
		print('\x1b[1A', end='')
	cam.capture('/dev/shm/tmp.jpg')
	im = Image.open('/dev/shm/tmp.jpg').convert('L')
	arr = np.asarray(im)
	data = list(scan.scan(arr))
	if [_.data for _ in olddata] == [_.data for _ in data] or not data:
		sleep(0.2)
		continue
	if db:
		cur = conn.cursor()
	for code in data:
		print('%s code: payload="%s"' % (code.type, code.data.decode()))
		if db:
			cur.execute('INSERT INTO barcodes VALUES (?, ?, ?)', (time(), code.type, code.data.decode()))
		else:
			with open(name, 'a') as f:
				f.write('%f,%s,%s\n' % (time(), code.type, code.data.decode()))
	if db:
		conn.commit()
		cur.close()
	olddata = data.copy()
	sleep(0.2)

conn.close()
#remove('/dev/shm/tmp.jpg')

