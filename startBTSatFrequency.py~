#!/usr/bin/env python

from gnuradio import gr, eng_notation
from gnuradio.eng_option import eng_option
from optparse import OptionParser
import sys
import math
import struct
import threading
import time
import sqlite3
import os
from datetime import datetime

def main_loop():
    usage = "usage: %prog [options] channel_freq"
    parser = OptionParser(option_class=eng_option, usage=usage)
 
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.print_help()
        sys.exit(1)

    center_freq = eng_notation.str_to_num(args[0])
    startOpenBTS(center_freq)

def startOpenBTS(frequency):            
    
    arfcn=int((frequency-935e6)/2e5)
    print 'ARFCN=', arfcn
    #DB modifications
    t=(arfcn,)
    conn=sqlite3.connect("/etc/OpenBTS/OpenBTS.db")
    cursor=conn.cursor()
    cursor.execute("update config set valuestring=? where keystring='GSM.Radio.C0'",t)
    conn.commit()
    #start the OpenBTS
    f=os.popen('~/ddp-stage-1-and-openbts/runOpenBTS.sh')
    f.close()

	          

if __name__ == '__main__':

    try:
        main_loop()

    except KeyboardInterrupt:
        pass
