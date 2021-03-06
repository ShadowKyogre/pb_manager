#!/usr/bin/env python3
import requests
#import dateutil.parser as dtparser
#eventually we'll need this for informing user of date expiry?

from collections import OrderedDict
from configparser import ConfigParser
import csv
import atexit
import sys
import argparse
import os
from datetime import datetime


if os.name == 'nt':
	CONFIG_PATH = os.path.join(os.environ['APPDATA'], 'ShadowKyogre', 'pb_manager.ini')
else:
	CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.config', 
                           'ShadowKyogre', 'pb_manager.ini')
CFG = ConfigParser()
CFG.read(CONFIG_PATH)

TSH_URL=CFG.get('DEFAULT', 'TSH_URL', fallback="https://transfer.sh")
FMT_URL=CFG.get('DEFAULT', 'FMT_URL', fallback="https://ptpb.pw/{}")
ALIAS_URL=FMT_URL.format("u")
PASTE_URL=FMT_URL.format("")
DB=OrderedDict()
TDB=OrderedDict()
PTPB_DB_STORE=CFG.get('DEFAULT', 'PTPB_DB_STORE', fallback='ptpb.tsv')
TSH_DB_STORE=CFG.get('DEFAULT', 'TSH_DB_STORE', fallback='tsh.tsv')

def tsh_paste(*args, same_link=False):
	mfiles = []
	for f in args:
		if same_link:
			mfiles.append(('filedata', (os.path.basename(f), open(f, 'rb'))))
		else:
			fpayload = {'filedata': open(f, 'rb')}
			r = requests.post(TSH_URL, files=fpayload)
			url = r.content.decode('utf-8').strip()
			dt = datetime.now().isoformat()
			TDB[f]=[url, dt]
			print("{}\t{}".format(f, url))
	if len(mfiles) > 0:
		r = requests.post(TSH_URL, files=mfiles)
		data = r.content.decode('utf-8').splitlines()
		dt = datetime.now().isoformat()
		for i in range(len(data)):
			url = data[i].strip()
			TDB[args[i]]=[url, dt]
			print("{}\t{}".format(args[i], url))

def pb_paste(*args, alias=False, private=False):
	for f in args:
		if f in DB.keys():
			print("Skipping", f, "to avoid redacting UUID")
			continue
		if alias:
			payload = {'c':f}
			r = requests.post(ALIAS_URL, data=payload, allow_redirects=False)
		else:
			fpayload = {'c':open(f, 'rb')}
			if private:
				payload = {'p': '1'}
			else:
				payload={}
			r = requests.post(PASTE_URL, data=payload, files=fpayload, allow_redirects=False)
		data = r.content.decode('utf-8').splitlines()
		url = data[0].replace('url: ','').strip()
		if alias:
			uuid = "<redacted>"
		else:
			uuid = data[1].replace('uuid: ', '').strip()
		DB[f]=[url, uuid, int(private)]
		print('{}\t{}'.format(f, url))

def pb_update(*args):
	for f in args:
		if f not in DB.keys():
			print("Huh, we don't have one...")
			continue
		if DB[f][1] != 'redacted':
			fpayload = {'c':open(f, 'rb')}
			r = requests.put(FMT_URL.format(DB[f][1]), files=fpayload)
			if DB[f][2] == 1:
				data = r.content.decode('utf-8').splitlines()
				url = data[0].replace(' updated.','').strip()
				print('{} updated, new url: {}'.format(DB[f][0], url))
				DB[f][0] = url
			else:
				print('{} updated'.format(DB[f][0]))

def pb_delete(*args):
	for f in args:
		if f not in DB.keys():
			print("Huh, we don't have one...")
			continue
		if DB[f][1] != '<redacted>':
			requests.delete(FMT_URL.format(DB[f][1]))
			print('{} deleted, removing obsolete data'.format(DB[f][0]))
			del DB[f]

def pb_db_write():
	with open(PTPB_DB_STORE, 'w') as tsvfile:
		writer = csv.writer(tsvfile, delimiter='\t')
		for k,v in DB.items():
			writer.writerow([k, v[0], v[1], v[2]])

def tsh_db_write():
	with open(TSH_DB_STORE, 'w') as tsvfile:
		writer = csv.writer(tsvfile, delimiter='\t')
		for k,v in TDB.items():
			writer.writerow([k, v[0], v[1]])

if os.path.exists(PTPB_DB_STORE):
	with open(PTPB_DB_STORE) as tsvfile:
		reader = csv.reader(tsvfile, delimiter='\t')
		for row in reader:
			if len(row) == 0: continue
			DB[row[0]]=[row[1], row[2], int(row[3])]

if os.path.exists(TSH_DB_STORE):
	with open(TSH_DB_STORE) as tsvfile:
		reader = csv.reader(tsvfile, delimiter='\t')
		for row in reader:
			if len(row) == 0: continue
			TDB[row[0]]=[row[1], row[2]]

if __name__ == "__main__":
	def upload(args):
		pb_paste(*args.fnames, alias=args.alias, private=args.private)

	def tupload(args):
		tsh_paste(*args.fnames, same_link=args.same_link)

	def update(args):
		pb_update(*args.fnames)

	def delete(args):
		pb_delete(*args.fnames)

	def urls(args):
		if len(args.fnames) == 0:
			for k in DB.keys():
				print(DB[k][0])
			for k in TDB.keys():
				print(TDB[k][0])
			return

		for f in args.fnames:
			have_it = False
			if f in DB.keys():
				print(DB[f][0])
				have_it = True

			if f in TDB.keys():
				print(TDB[f][0])
				have_it = True

			if not have_it:
				print("Huh, we don't have one...")

	parser = argparse.ArgumentParser(description='Manage your ptpb.pw and transfer.sh pastes')
	sparsers = parser.add_subparsers()

	parser_upload = sparsers.add_parser('upload')
	parser_upload.add_argument('--alias', action='store_true')
	parser_upload.add_argument('--private', action='store_true')
	parser_upload.add_argument('fnames', metavar='N', type=str, nargs='+',
	                           help='Files to put on ptpb.pw')
	parser_upload.set_defaults(func=upload)

	parser_tupload = sparsers.add_parser('tupload')
	parser_tupload.add_argument('--same-link', action='store_true')
	parser_tupload.add_argument('fnames', metavar='N', type=str, nargs='+',
	                            help='Files to put on ptpb.pw')
	parser_tupload.set_defaults(func=tupload)

	parser_update = sparsers.add_parser('update')
	parser_update.add_argument('fnames', metavar='N', type=str, nargs='+',
	                           help='Files to put on ptpb.pw')
	parser_update.set_defaults(func=update)

	parser_delete = sparsers.add_parser('delete')
	parser_delete.add_argument('fnames', metavar='N', type=str, nargs='+',
	                           help='Files to put on ptpb.pw')
	parser_delete.set_defaults(func=delete)

	parser_urls = sparsers.add_parser('urls')
	parser_urls.add_argument('fnames', metavar='N', type=str, nargs='*',
	                         help='Files to put on ptpb.pw')
	parser_urls.set_defaults(func=urls)

	atexit.register(pb_db_write)
	atexit.register(tsh_db_write)
	args = parser.parse_args(sys.argv[1:])

	args.func(args)
