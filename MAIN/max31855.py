import ustruct
import utime
from machine import Pin, SPI


class MAX31855:
    def __init__(self, hwspi=2, cs=None, sck=None, miso=None, offset=0.0, cache_time=0):
        """
        :param hwspi: Hardware SPI bus id
            HSPI(id=1): sck=14, mosi=13, miso=12
            VSPI(id=2): sck=18, mosi=23, miso=19
        :param cs: chip select pin
        :param sck: serial clock pin
        :param mosi: mosi pin
        :param miso: miso pin

        FOR ADAFRUIT MAX31855 BREAKOUT BOARD WIRING
        ESP32 3V3 => Sensor VDD
        ESP32 GND => Sensor GND
        ESP32 SCK => Sensor CLK
        ESP32 MISO => Sensor DO
        ESP32 any digital IO pin => Sensor CS
        """
        baudrate = 10**5
        self._offset = offset
        self._cs = Pin(cs, Pin.OUT)
        self._data = bytearray(4)
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
        self._cs.value(0)
        try:
            self._spi.readinto(self._data)
        finally:
            self._cs.value(1)

        if self._data[3] & 0x01:
            raise RuntimeError("NC") # not connected
        if self._data[3] & 0x02:
            raise RuntimeError("X_GND") # shortcut to GND
        if self._data[3] & 0x04:
            raise RuntimeError("X_PWR") # shortcut to power
        if self._data[1] & 0x01:
            raise RuntimeError("ERR") # faulty reading

        temp, refer = ustruct.unpack('>hh', self._data)
        refer >>= 4
        temp >>= 2
        self.last_read_time = utime.ticks_ms()
        self.last_read = refer * 0.0625 + self._offset if internal else temp * 0.25 + self._offset
        return self.last_read

    def get_temp(self):
        if utime.ticks_diff(utime.ticks_ms(), self.last_read_time) < self.cache_time:
            return self.last_read
        return self.read_temp()
