#!/usr/bin/python3
# Copyright (C) 2013 - Remy van Elst

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Wesley Moore <wmoore@jlab.org> - 2017-05-24
# Changelog: - fixed UnicodeDecodeError when trying to read binary file
#            - removed invalid verbose option from usage()

# Mark Ruys <mark.ruys@peercode.nl> - 2015-8-27
# Changelog: - catch openssl parsing errors
#            - clean up temporary file on error
#            - add support for PEM CRL's
#            - fix message when CRL has been expired
#            - pretty print duration

# Jeroen Nijhof <jnijhof@digidentity.eu>
# Changelog: - fixed timezone bug by comparing GMT with GMT
#            - changed hours to minutes for even more precision

# Remy van Elst - raymii.org - 2012
# 05.11.2012
# Changelog: - check with hours instead of dates for more precision,
#            - URL errors are now also catched as nagios exit code.

# Michele Baldessari - Leitner Technologies - 2011
# 23.08.2011

import time
import datetime
import getopt
import os
import pprint
import subprocess
import sys
import tempfile
import urllib.request, urllib.parse, urllib.error

def check_crl(url, warn, crit):
    tmpcrl = tempfile.mktemp(".crl")
    #request = urllib.request.urlretrieve(url, tmpcrl)
    try:
        urllib.request.urlretrieve(url, tmpcrl)
    except:
        print ("CRITICAL: CRL could not be retrieved: %s" % url)
        os.remove(tmpcrl)
        sys.exit(2)

    try:
        inform = 'DER'
        ret = subprocess.check_output(["/usr/bin/file", "-b", tmpcrl], stderr=subprocess.STDOUT)
        ftype = ret.strip().decode('utf-8')
        if ftype != "data":
            # not binary, test for PEM
            crlfile = open(tmpcrl, 'r')
            for line in crlfile:
                if "BEGIN X509 CRL" in line:
                    inform = 'PEM'
                    break
            crlfile.close()

        ret = subprocess.check_output(["/usr/bin/openssl", "crl", "-inform", inform, "-noout", "-nextupdate", "-in", tmpcrl], stderr=subprocess.STDOUT)
    except:
        print ("UNKNOWN: CRL could not be parsed: %s %s" % url)
        os.remove(tmpcrl)
        sys.exit(3)

    nextupdate = ret.strip().decode('utf-8').split("=")
    os.remove(tmpcrl)
    eol = time.mktime(time.strptime(nextupdate[1],"%b %d %H:%M:%S %Y GMT"))
    today = time.mktime(datetime.datetime.utcnow().timetuple())
    minutes = (eol - today) / 60
    if abs(minutes) < 4 * 60:
        expires = minutes
        unit = "minutes"
    elif abs(minutes) < 2 * 24 * 60:
        expires = minutes / 60
        unit = "hours"
    else:
        expires = minutes / (24 * 60)
        unit = "days"
    gmtstr = time.asctime(time.localtime(eol))
    if minutes < 0:
        msg = "CRITICAL CRL expired %d %s ago (on %s GMT)" % (-expires, unit, gmtstr)
        exitcode = 2
    elif minutes <= crit:
        msg = "CRITICAL CRL expires in %d %s (on %s GMT)" % (expires, unit, gmtstr)
        exitcode = 2
    elif minutes <= warn:
        msg = "WARNING CRL expires in %d %s (on %s GMT)" % (expires, unit, gmtstr)
        exitcode = 1
    else:
        msg = "OK CRL expires in %d %s (on %s GMT)" % (expires, unit, gmtstr)
        exitcode = 0

    print (msg)
    sys.exit(exitcode)

def usage():
    print ("check_crl.py -h|--help -u|--url=<url> -w|--warning=<minutes> -c|--critical=<minutes>")
    print ("")
    print ("Example, if you want to get a warning if a CRL expires in 8 hours and a critical if it expires in 6 hours:")
    print ("./check_crl.py -u \"http://domain.tld/url/crl.crl\" -w 480 -c 360")

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hu:w:c:", ["help", "url=", "warning=", "critical="])
    except getopt.GetoptError as err:
        usage()
        sys.exit(2)
    url = None
    warning = None
    critical = None
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-u", "--url"):
            url = a
        elif o in ("-w", "--warning"):
            warning = a
        elif o in ("-c", "--critical"):
            critical = a
        else:
            assert False, "unhandled option"

    if url != None and warning != None and critical != None:
        check_crl(url, int(warning), int(critical))
    else:
        usage()
        sys.exit(2)


if __name__ == "__main__":
    main()
