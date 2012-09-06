#!/usr/bin/env python
#
#   slimpy - Squeezebox Client
#   Copyright (C) 2012 terual
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

try:
    import alsaaudio
except ImportError:
    print "To install pyalsaaudio:"
    print "svn co https://pyalsaaudio.svn.sourceforge.net/svnroot/pyalsaaudio/trunk pyalsaaudio"
    print "cd pyalsaaudio"
    print "python setup.py build"
    print "sudo python setup.py install"

import logging
import threading
import time
import sys

from slimproto import SlimProto
from slimhttp import SlimHttp
from slimaudio import SlimAudio
from slimbuffer import SlimBuffer

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
console_sh = logging.StreamHandler()
console_sh.setLevel(logging.DEBUG)
console_sh.setFormatter(logging.Formatter('%(asctime)s %(name)-20s %(levelname)-8s %(message)s'))
logger.addHandler(console_sh)

if not len(sys.argv) == 2:
    print "Usage: %s [ip-address of LMS]" % sys.argv[0]
    sys.exit(0)

slimproto = SlimProto(sys.argv[1])
slimproto.connect()

slimhttp   = SlimHttp()
slimbuffer = SlimBuffer(1024*1024*15, slimhttp, slimproto)
slimaudio  = SlimAudio(slimbuffer, slimproto)

slimbuffer.start()
slimaudio.start()

try:
    while True:
        proto, httpheader = slimproto.recv_command()
        
        if not proto:
            continue
        
        if httpheader:
            slimhttp.connect(httpheader)
            slimproto.stat_HTTP_headers_received(slimbuffer.size, slimbuffer.fillCount)
            
        command = proto['command']

        # 's' start, 'p' pause, 'u' unpause, 'q' stop, 't' status, 'f' flush, 'a' skip-ahead 
        if command == "s":   # start
        
            if not slimaudio.samplesize == slimaudio.convert_samplesize(proto['pcmsamplesize']) or \
               not slimaudio.endian == slimaudio.convert_endian(proto['pcmendian']) or \
               not slimaudio.rate == slimaudio.convert_rate(proto['pcmsamplerate']):
                slimaudio.set_rate_format(slimaudio.convert_rate(proto['pcmsamplerate']), 
                                          slimaudio.convert_samplesize(proto['pcmsamplesize']),
                                          slimaudio.convert_endian(proto['pcmendian']))
        
            slimbuffer.unpause()
            slimproto.stat_stream_connection_established(slimbuffer.size, slimbuffer.fillCount)
            
            slimaudio.unpause()
            slimproto.stat_buffer_threshold_reached(slimbuffer.size, slimbuffer.fillCount)
            slimproto.stat_track_started(slimbuffer.size, slimbuffer.fillCount)
            
        elif command == "p": # pause
        
            slimaudio.pause()
            if proto['replay_gain'] == 0:
                self.stat_confirmation_of_pause()
            else:
                time.sleep(proto['replay_gain']/1000)
                slimaudio.unpause()
            
        elif command == "u": # unpause
        
            slimaudio.unpause()
            slimproto.stat_confirmation_of_resume(slimbuffer.size, slimbuffer.fillCount)
            
        elif command == "q": # stop
        
            slimbuffer.flush()
            slimproto.stat_connection_flushed(slimbuffer.size, slimbuffer.fillCount)
            
        elif command == "t": # status
        
            slimproto.stat_timer(slimbuffer.size, slimbuffer.fillCount)
            
        elif command == "f": # flush
        
            slimbuffer.flush()
            slimproto.stat_connection_flushed(slimbuffer.size, slimbuffer.fillCount)
            
        elif command == "a": # skip-ahead
        
            pass

except KeyboardInterrupt:
    slimbuffer.stop()
    slimaudio.stop()
    slimproto.goodbye()
