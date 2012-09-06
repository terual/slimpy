#!/usr/bin/env python

import logging
import threading
import time
import alsaaudio

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

slimproto = SlimProto('192.168.1.53')
slimproto.connect()

slimhttp   = SlimHttp()
slimbuffer = SlimBuffer(1024*1024*15, slimhttp, slimproto)
slimaudio  = SlimAudio(slimbuffer, slimproto)

slimbuffer.start()
slimaudio.start()

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


else:
    slimproto.goodbye()
