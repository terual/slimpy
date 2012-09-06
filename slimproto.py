#   (c) 2011 Bart Lauret
#
#   This file is part of slimpy.
#
#   slimpy is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   slimpy is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with slimpy.  If not, see <http://www.gnu.org/licenses/>.

import socket
import struct
import sys
import logging

from time import sleep,time
from collections import namedtuple

class SlimProto():

    ''' SlimProto implementation '''

    def __init__(self, server_ip, server_port=3483, mac_addr="00:00:00:00:00:02", device_id=12, revision=255): 

        ''' Constructor '''
        
        self.logger = logging.getLogger("SlimProto")

        self.time_for_jiffies = time()

        self.server_ip = server_ip
        self.server_port = server_port
        self.mac_addr = self._HexToByte(mac_addr)

        # The Device ID of the player. '2' is squeezebox. '3' is softsqueeze, '4' is squeezebox2,
        # '5' is transporter, '6' is softsqueeze3, '7' is receiver, '8' is squeezeslave, 
        # '9' is controller, '10' is boom, '11' is softboom, '12' is squeezeplay 
        # Tested with squeezeplay
        self.device_id = device_id
        self.revision = revision #FIXME revision=255
        self.capabilities = 'model=squeezeplay,modelName=SlimPy,pcm,MaxSampleRate=192000'
        
        self.socket = None

    def connect(self):

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.socket.connect((self.server_ip, self.server_port))
        except socket.error, e:
            self.logger.error('Connection failed: %s' % e)

        self.socket.settimeout(5.0)

        # Set up connection to server
        self.hello(self.capabilities)

    def recv_command(self):

        ''' Receive message from socket '''
        
        try:
            data = self.socket.recv(2)
        except socket.timeout:
            return None, None
        
        if not data:
            # Connection closed on server?
            return None, None

        length = struct.unpack('!H', data)[0]
        data = self.socket.recv(length)
        cmd_header, cmd_data = struct.unpack('!4s%is' % (length-4), data)
        
        if cmd_header=='strm':

            strm = self.parse_strm(cmd_data[:24])

            if len(cmd_data) > 24:
                http_header = self.get_http_header(cmd_data[18:])
                return strm, http_header
            else:
                return strm, None
                
        return None, None
                

    def get_http_header(self, cmd_data):

        (server_port, server_ip, http_header) = struct.unpack('!HI%is' % (len(cmd_data)-6), cmd_data)
        #self.logger.debug("HTTP header received, server_port: %i, server_ip: %s" % (server_port, server_ip))
        
        if not server_ip:
            server_ip = self.server_ip
        
        return {'server_port': server_port,
                 'server_ip':   server_ip,
                 'http_header': http_header}

    def parse_strm(self, cmd_data):

        keys = ['command', 'autostart', 'formatbyte', 'pcmsamplesize', 
                'pcmsamplerate', 'pcmchannels', 'pcmendian', 'threshold',
                'spdif_enable', 'trans_period', 'trans_type', 'flags', 
                'output_threshold', 'reserved', 'replay_gain', 
                'server_port', 'server_ip']
        values = struct.unpack('!7c7BIHI', cmd_data)
        return dict(zip(keys, values))
        
    def hello(self, capabilities):

        length = 36 + len(capabilities)
        MESSAGE = struct.pack('!4sIBB6c28x%is' % len(capabilities), 
                              'HELO', 
                              length,
                              self.device_id, 
                              self.revision, 
                              self.mac_addr[0], 
                              self.mac_addr[1], 
                              self.mac_addr[2], 
                              self.mac_addr[3], 
                              self.mac_addr[4], 
                              self.mac_addr[5], 
                              capabilities)
        self.socket.send(MESSAGE)

    def goodbye(self):

        self.logger.debug('Sending BYE! message')
        self.socket.send(struct.pack('!4sIB', 'BYE!', 1, 0))

        # Wait for message to arrive
        sleep(1)
        self.socket.close()
        self.logger.debug('Closed SlimProto socket')


    def stat(self, event_code, output_buffer_size, output_buffer_fullness):

        rbytes = 0
        decoder_buffer_size = 1024
        decoder_buffer_fullness = 1024

        try:
            elapsed_seconds = int(self.parent.AudioStreamThread.elapsed_seconds())
            elapsed_milliseconds = int(1000*(self.parent.AudioStreamThread.elapsed_seconds()-elapsed_seconds))
        except:
            elapsed_seconds = 0
            elapsed_milliseconds = 0
            
        server_timestamp = 0

        jiffies = self.jiffies()

        self.socket.send(struct.pack('!4sI4s3BIIQH4IHIIH', 
            'STAT', 
            53, 
            event_code,
            0,
            0,
            0,
            decoder_buffer_size,
            decoder_buffer_fullness,
            rbytes,
            65534, # signal strength
            jiffies, # jiffies
            output_buffer_size,
            output_buffer_fullness,
            elapsed_seconds,
            0, # voltage
            elapsed_milliseconds,
            server_timestamp,
            0)) # error code

        self.logger.debug('Send STAT: event_code: %s, decoder_buffer_size: %i, decoder_buffer_fullness: %i, rbytes: %i, jiffies: %i, output_buffer_size: %i, output_buffer_fullness: %i, elapsed_seconds: %i, elapsed_milliseconds: %i, server_timestamp: %i' % (event_code, decoder_buffer_size, decoder_buffer_fullness, rbytes, jiffies, output_buffer_size, output_buffer_fullness, elapsed_seconds, elapsed_milliseconds, server_timestamp))


    def jiffies(self):
        # uint32 should last almost 50 days
        return int((time()-self.time_for_jiffies)*1000)

    def stat_decoder_ready(self, output_buffer_size, output_buffer_fullness):
        self.stat('STMd', output_buffer_size, output_buffer_fullness)

    def stat_confirmation_of_pause(self, output_buffer_size, output_buffer_fullness):
        self.stat('STMp', output_buffer_size, output_buffer_fullness)

    def stat_confirmation_of_resume(self, output_buffer_size, output_buffer_fullness):
        self.stat('STMr', output_buffer_size, output_buffer_fullness)

    def stat_track_started(self, output_buffer_size, output_buffer_fullness):
        self.stat('STMs', output_buffer_size, output_buffer_fullness)

    def stat_output_underrun(self, output_buffer_size, output_buffer_fullness):
        self.stat('STMo', output_buffer_size, output_buffer_fullness)

    def stat_HTTP_headers_received(self, output_buffer_size, output_buffer_fullness):
        self.stat('STMh', output_buffer_size, output_buffer_fullness)

    def stat_underrun(self, output_buffer_size, output_buffer_fullness):
        self.stat('STMu', output_buffer_size, output_buffer_fullness)

    def stat_connect(self, output_buffer_size, output_buffer_fullness):
        self.stat('STMc', output_buffer_size, output_buffer_fullness)

    def stat_stream_connection_established(self, output_buffer_size, output_buffer_fullness):
        self.stat('STMe', output_buffer_size, output_buffer_fullness)

    def stat_buffer_threshold_reached(self, output_buffer_size, output_buffer_fullness):
        self.stat('STMl', output_buffer_size, output_buffer_fullness)

    def stat_connection_flushed(self, output_buffer_size, output_buffer_fullness):
        self.stat('STMf', output_buffer_size, output_buffer_fullness)
        
    def stat_timer(self, output_buffer_size, output_buffer_fullness):
        self.stat('STMt', output_buffer_size, output_buffer_fullness)

    def _HexToByte(self, hexStr):

        """
        Convert a string hex byte values into a byte string. The Hex Byte values may
        or may not be colon separated.
        http://code.activestate.com/recipes/510399-byte-to-hex-and-hex-to-byte-string-conversion/
        """

        bytes = []

        hexStr = ''.join( hexStr.split(":") )

        for i in range(0, len(hexStr), 2):
            bytes.append( chr( int (hexStr[i:i+2], 16 ) ) )

        return bytes


