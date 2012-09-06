#   (c) 2012 terual
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

import alsaaudio
import threading
import logging

class SlimAudio(threading.Thread):
    
    def __init__(self, slimbuffer, slimproto):
        
        threading.Thread.__init__(self)
        self.logger = logging.getLogger("SlimAudio")

        self.slimbuffer = slimbuffer
        self.slimproto = slimproto
        
        self.running    = True
        self.samplesize = None
        self.endian     = None
        self.rate       = None
        self.channels   = 2
        self.periodsize = 32
        self.playing    = True
        
        self.alsa = None
        self.init()       

        self.lock = threading.Lock()        
        self.lock.acquire()

    def init(self):
        if self.alsa:
            self.alsa.close()
            del self.alsa
        self.alsa = alsaaudio.PCM(alsaaudio.PCM_PLAYBACK, alsaaudio.PCM_NORMAL, card='plughw:CARD=PCH,DEV=0')

    def run(self):
        
        while self.running:
            self.lock.acquire()
            try:
                buf = self.slimbuffer.read(self.samplesize*8*self.channels*self.periodsize)
                if buf:
                    self.alsa.write(buf)
                else:
                    self.slimproto.stat_underrun(self.slimbuffer.size, self.slimbuffer.fillCount)
                    self.pause()
            except TypeError:
                pass
            finally:
                try:
                    self.lock.release()
                except threading.ThreadError:
                    pass

        
    def set_rate_format(self, rate, samplesize, endian):

        self.init()

        self.logger.info("Setting rate to %s Hz", rate)
        self.alsa.setrate(rate)
        self.rate = rate

        self.logger.info("Setting format to %s byte, %s endian", samplesize, endian)
        alsaformat = self.convert_format_to_alsa(samplesize, endian)
        self.alsa.setformat(alsaformat)
        self.samplesize = samplesize
        self.endian = endian
        
        print self.alsa.dumpinfo()
   
    def pause(self):
        self.lock.acquire()
        if self.playing:
            self.alsa.pause(1)
            self.playing = False
        
    def unpause(self):
        try:
            self.lock.release()
        except threading.ThreadError:
            pass
        if not self.playing:
            self.alsa.pause(0)
            self.playing = True
        
    def convert_samplesize(self, pcmsamplesize):
        #pcmsamplesize 	'0' = 8, '1' = 16, '2' = 24, '3' = 32
        try:
            pcmsamplesize = int(pcmsamplesize)
        except:
            return None
        return int(pcmsamplesize)+1
        
    def convert_endian(self, pcmendian):
        #pcmendian 	    '0' = big, '1' = little
        try:
            pcmendian = int(pcmendian)
        except:
            return None
        return int(pcmendian)
        
    def convert_rate(self, pcmsamplerate):
        # '0'=11kHz, '1'=22kHz, '2'=32kHz, '3'=44.1kHz, '4'=48kHz, '5'=8kHz, '6'=12kHz, 
        # '7'=16kHz, '8'=24kHz, '9'=96kHz, ':'=88200; usually 3, '?' for self-describing formats. 
        if pcmsamplerate == '0':
            return 11025
        elif pcmsamplerate == '1':
            return 22050
        elif pcmsamplerate == '2':
            return 32000
        elif pcmsamplerate == '3':
            return 44100
        elif pcmsamplerate == '4':
            return 48000
        elif pcmsamplerate == '5':
            return 8000
        elif pcmsamplerate == '6':
            return 12000
        elif pcmsamplerate == '7':
            return 16000
        elif pcmsamplerate == '8':
            return 24000
        elif pcmsamplerate == '9':
            return 96000
        elif pcmsamplerate == ':':
            return 88200
        elif pcmsamplerate == ';':
            return 192000
        elif pcmsamplerate == '<':
            return 176400
        return None

    def convert_format_to_alsa(self, pcmsamplesize, pcmendian):
        if pcmsamplesize == 1:
            return alsaaudio.PCM_FORMAT_S8
        if pcmendian == 1:
            if pcmsamplesize == 2:
                return alsaaudio.PCM_FORMAT_S16_LE
            elif pcmsamplesize == 3:
                return alsaaudio.PCM_FORMAT_S24_3LE
            elif pcmsamplesize == 4:
                return alsaaudio.PCM_FORMAT_S32_LE
        elif pcmendian == 0:
            if pcmsamplesize == 2:
                return alsaaudio.PCM_FORMAT_S16_BE
            elif pcmsamplesize == 3:
                return alsaaudio.PCM_FORMAT_S24_3BE
            elif pcmsamplesize == 4:
                return alsaaudio.PCM_FORMAT_S32_BE
        print "Error", pcmsamplesize, pcmendian
