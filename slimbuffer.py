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

import threading
import time

class SlimBuffer(threading.Thread):
    
    def __init__(self, size, slimhttp, slimproto):
        
        threading.Thread.__init__(self)
        self.running   = True
                
        self.slimhttp  = slimhttp
        self.slimproto = slimproto
        
        self.size      = size
        self.readPtr   = 0
        self.writePtr  = 0
        self.fillCount = 0
        self.buffer    = bytearray(self.size)
        self.mv        = memoryview(self.buffer)
        
        self.lock      = threading.Lock()
        self.lock.acquire()
        self.buflock   = threading.Lock()
        
        self.flush()

    def flush(self):
        self.begin = 0
        self.end   = 0

    def stop(self):
        self.running = False
        try:
            self.lock.release()
        except threading.ThreadError:
            pass

    def run(self):
        while self.running:
            self.lock.acquire()
            try:
                if self.slimhttp.read and self.fillCount+4096 < self.size:
                    buf = self.slimhttp.read(4096)
                    if buf:
                        self.write(buf)
                    else:
                        print "EOF Stream"
                        self.slimproto.stat_decoder_ready(self.size, self.fillCount)
                        self.slimhttp.read = None
                else:
                    time.sleep(0.1)
            finally:
                try:
                    self.lock.release()
                except threading.ThreadError:
                    pass
    
    def is_full(self):
        return self.fillCount == self.size
        
    def is_empty(self):
        return (self.end == self.begin)
        
    def fullness(self):
        return self.fillCount
    
    def write(self, buf):
        with self.buflock:
            n = len(buf)
            if n > self.size - self.fillCount:
                return False
            if n + self.writePtr > self.size:
                chunk = self.size - self.writePtr
                self.mv[self.writePtr:self.writePtr+chunk] = buf[0:chunk]
                self.mv[0:n-chunk] = buf[chunk:n]
                self.writePtr = n - chunk
            else:
                self.mv[self.writePtr:self.writePtr+n] = buf[0:n]
                self.writePtr += n
            if self.writePtr == self.size:
                self.writePtr = 0
            self.fillCount += n
            return True

    def read(self, n):
        with self.buflock:
            if n > self.fillCount:
                return None
            if n + self.readPtr > self.size:
                chunk = self.size - self.readPtr
                buf  = self.mv[self.readPtr:self.readPtr+chunk].tobytes()
                buf += self.mv[0:n-chunk].tobytes()
                self.readPtr = n - chunk
            else:
                buf = self.mv[self.readPtr:self.readPtr+n].tobytes()
                self.readPtr += n
            if self.readPtr == self.size:
                self.readPtr = 0;
            self.fillCount -= n
            return buf
            
    def skip_bytes(self, n):
        with self.buflock:
            if n < 0:
                return False
            if n > self.fillCount:
                return False
            if n + self.readPtr > self.size:
                chunk = self.size - self.readPtr
                self.readPtr = n - chunk
            else:
                self.readPtr += n
            if self.readPtr == self.size:
                self.readPtr = 0
            self.fillCount -= n
            return True

    def pause(self):
        self.lock.acquire()
        
    def unpause(self):
        self.lock.release()
