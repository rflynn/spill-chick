#!/usr/bin/env python

"""
sqlite - Importing Files
CSV Files
For simple CSV files, you can use the SQLite shell to import the file into your SQLite database. First create the table, then designate the separator, and finally import the file.

  sqlite> create table test (id integer, datatype_id integer, level integer, meaning text);
  sqlite> .separator ","
  sqlite> .import no_yes.csv test
Unfortunately, not all CSV files are simple. For instance, the CSV line

  "Last, First", 1234
means two columns in Excel (a name and an integer), but three columns with embedded quote marks in SQLite. Be wary when trying to import CSV files.

Some problems you would encounter importing CSV files using the SQLite shell:

Fields with commas in them. The SQLite shell will always split fields on the separator character, no matter what comes before or after it. Quotes or backslashes won't escape them.
Quoted fields. The SQLite shell will interpret quotes literally, so the imported database will have embedded quote marks in them.
Fields with carriage returns or newlines. The SQLite shell inteprets them as ending the row.
There is no standard as to what a CSV file should look like, and the SQLite shell does not even attempt to handle all the intricacies of interpreting a CSV file. If you need to import a complex CSV file and the SQLite shell doesn't handle it, you may want to try a different front end, such as SQLite Database Browser.
"""

import os

# TODO: extract word.csv.gz -> word.csv

with os.popen('sqlite3 :memory:') as db:
	db.write('pragma synchronous = OFF\n')
	db.write('pragma page_size = 4096;\n')
	db.write('pragma page_size = 8192;\n')
	db.write('pragma page_size = 65536;\n')
	db.write('attach database ngram.db as ng;\n')
	db.write('create table ng.word (id int primary key, word text not null);\n')
	db.write('create table word (id int primary key, word text not null);\n')
	db.write('.separator ","\n')
	print('importing...')
	db.write('.import word.csv word\n')
	print('copying to disk...')
	db.write('insert into ng.word select id,word from word;\n')

