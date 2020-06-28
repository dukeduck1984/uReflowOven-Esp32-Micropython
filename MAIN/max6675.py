import ustruct
import utime
from machine import Pin, SPI

class MAX6675:
    def __init__(self, hwspi=2, cs=None, sck=None, miso=None, offset=0.0, cache_time=0):
        baudrate = 10**5
        self._offset = offset
        self._cs = Pin(cs, Pin.OUT)
        self.cache_time = cache_time
        self.last_read = 0
        self.last_read_time = 0

        if hwspi == 1 or hwspi == 2:
            # Hardware SPI Bus
            self._spi = SPI(hwspi, baudrate=baudrate, sck=Pin(sck), miso=Pin(miso))
        else:
            # Software SPI Bus
            self._spi = SPI(baudrate=baudrate, sck=Pin(sck), miso=Pin(miso))

    def get_offset(self):
        return self._offset

    def set_offset(self, offset):
        self._offset = offset

    def read_temp(self, internal=False):
        data = bytearray(2)
        self._cs.value(0)
        try:
            self._spi.readinto(data)
        finally:
            self._cs.value(1)

        if data[1] & 0x04:
            raise RuntimeError("NC") # not connected

        self.last_read_time = utime.ticks_ms()
        self.last_read = ((data[0]<<8 | data[1]) >> 3) * 0.25 + self._offset
        return self.last_read

    def get_temp(self):
        if utime.ticks_diff(utime.ticks_ms(), self.last_read_time) < self.cache_time:
            return self.last_read
        return self.read_temp()
