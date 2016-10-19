#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Yi Cao <ycao16@uw.edu>

# Distributed under terms of the GNU General Public License 3.0 license.

"""
Manage ADS references
"""

import os
import sqlite3


class ADSRefDatabaseError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class ADSRefDatabase(object):
    def __init__(self, db_file=None):
        if db_file is not None:
            self._db_file = db_file
        else:
            self._db_file = os.path.join(os.environ["HOME"], ".ads_ref.db")
        if not os.path.exists(self._db_file):
            self._conn = sqlite3.connect(self._db_file)
            self._create_database()
        else:
            self._conn = sqlite3.connect(self._db_file)

    def __del__(self):
        self._conn.close()

    def _create_database(self):
        c = self._conn.cursor()
        query = "CREATE TABLE ads_refs (bibcode TEXT UNIQUE, record TEXT)"
        c.execute(query)
        query = ("CREATE INDEX ads_refs_bibcode_index "
                 "ON ads_refs(bibcode)")
        c.execute(query)
        self._conn.commit()

    def _is_bibcode_valid(self, bibcode):
        if len(bibcode) != 19:
            raise ADSRefDatabaseError("Invalid bibcode")

    def search(self, bibcode):
        self._is_bibcode_valid(bibcode)
        c = self._conn.cursor()
        c.execute("SELECT record FROM ads_refs WHERE bibcode=?", (bibcode, ))
        record = c.fetchone()
        c.close()
        if record is not None:
            record = record[0]
        return record

    def add(self, bibcode):
        self._is_bibcode_valid(bibcode)
        if self.search(bibcode) is not None:
            return False
        record = self._retrieve_record(bibcode)
        c = self._conn.cursor()
        c.execute("INSERT INTO ads_refs VALUES(?, ?)", (bibcode, record))
        self._conn.commit()
        c.close()
        return True

    def remove(self, bibcode):
        self._is_bibcode_valid(bibcode)
        if self.search(bibcode) is None:
            return False
        c = self._conn.cursor()
        c.execute("DELETE FROM ads_refs WHERE bibcode=?", (bibcode, ))
        self._conn.commit()
        c.close()
        return True

    def output_to_file(self, file_name="ref.bib"):
        c = self._conn.cursor()
        c.execute("SELECT record FROM ads_refs")
        with open(file_name, "w") as fp:
            for record, in c.fetchall():
                fp.write(record)
        c.close()

    def _retrieve_record(self, bibcode):
        import urllib
        import urllib2
        url = "http://adsabs.harvard.edu/cgi-bin/nph-bib_query"
        data = {"bibcode": bibcode,
                "data_type": "BIBTEX",
                "db_key": "AST",
                "nocookieset": 1}
        request = urllib2.Request(url)
        request.add_data(urllib.urlencode(data))
        try:
            http = urllib2.urlopen(request)
        except urllib2.HTTPError:
            msg = ("Unable to retrieve the record %s, "
                   "possibly because of a wrong bibcode "
                   "or unavailability of the ADS server") % bibcode
            raise ADSRefDatabaseError(msg)
        string = http.read()
        idx = string.find("@")
        if idx < 0:
            raise ADSRefDatabaseError("Unrecognizable record\n%s" % string)
        record = string[idx:]
        return record


def main():
    import sys
    action = sys.argv[1]
    assert action in ["add", "remove", "search", "output", "help"]
    if action == "help":
        print """\
Usage:
    python ads_ref_manager.py action args
Examples:
    python ads_ref_manager.py help : show this message
    python ads_ref_manager.py [add/remove/search] bibcode :
        add/remove/search the record of this bibcode
    python ads_ref_manager.py output [file_name] :
        output all records to the file file_name (default: ref.bib)
"""
        return
    database = ADSRefDatabase()
    if action in ["add", "remove", "search"]:
        bibcode = sys.argv[2]
        if action == "add":
            flag = database.add(bibcode)
            if flag:
                print "Success"
            else:
                print "The record already exists"
            return
        if action == "remove":
            flag = database.remove(bibcode)
            if flag:
                print "Success"
            else:
                print "The record does not exist"
            return
        if action == "search":
            record = database.search(bibcode)
            if record is None:
                print "The record does not exist"
            else:
                print record
            return
    if action == "output":
        if len(sys.argv) == 3:
            output_file = sys.argv[2]
            database.output_to_file(output_file)
        else:
            database.output_to_file()
        return


if __name__ == "__main__":
    main()
