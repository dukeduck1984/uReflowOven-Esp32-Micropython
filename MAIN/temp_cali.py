import utime
import machine
import ujson
from max31855 import MAX31855

import lvgl as lv
import lvesp32


class TempCali:
    def __init__(self, config):
        self.config = config
        self.sensor = MAX31855(hwspi=self.config['max31855_pins']['hwspi'],
                               cs=self.config['max31855_pins']['cs'],
                               miso=self.config['max31855_pins']['miso'],
                               sck=self.config['max31855_pins']['sck'],
                               offset=self.config['temp_offset'])
        self.oven = machine.Pin(self.config['oven_pin'], machine.Pin.OUT, value=0)
        self.temp_cali_scr = lv.obj()
        self.page = lv.page(self.temp_cali_scr)
        self.page.set_size(self.temp_cali_scr.get_width(), self.temp_cali_scr.get_height())
        self.page.align(None, lv.ALIGN.CENTER, 0, 0)
        self.label = lv.label(self.page)
        self.label.set_long_mode(lv.label.LONG.BREAK)
        self.label.set_width(self.page.get_fit_width())
        self.page_text = ''
        self.tim = machine.Timer(-1)
        self.start_time = None
        self.start_temp = None
        self.last_temp = None
        self.lag_temp = None
        self.lag_time = None
        self.cooling_counter = 0
        self.check_temp = 100

    def _update_text(self, text):
        self.page_text += text
        self.label.set_text(self.page_text)

    def _heating_cb_handler(self):
        timeout = 300
        if utime.time() - self.start_time >= timeout:
            self.tim.deinit()
            self._update_text("Oven not working or bad sensor!\n")
            raise Exception("Oven not working or bad sensor!")
        else:
            current_temp = self.sensor.read_temp()
            print(current_temp)
            if current_temp >= self.check_temp:
                self.oven.off()
                self._update_text('Done. Cool down now.\n')
                self.tim.deinit()
                self._init_cooling_test()

    def _init_cooling_test(self):
        self.start_time = utime.time()
        self.start_temp = self.sensor.read_temp()
        self.last_temp = self.start_temp
        self.tim.deinit()
        self.tim.init(period=1000, mode=machine.Timer.PERIODIC, callback=lambda t: self._cooling_cb_handler())

    def _cooling_cb_handler(self):
        current_temp = self.sensor.read_temp()
        print(current_temp)
        if current_temp < self.last_temp:
            self.cooling_counter += 1
            if self.cooling_counter >=3:
                self._update_text('All done.\n\n')
                self.tim.deinit()
                self._save_temp_cali_results()
        else:
            self.last_temp = current_temp

    def _save_temp_cali_results(self):
        self.lag_time = int(utime.time() - self.start_time)
        self.lag_temp = self.last_temp - self.check_temp

        self._update_text("** Calibration Results Saved ** \n")
        self._update_text("calibrate_temp: " + str(round(self.lag_temp, 2)) + '\n')
        self._update_text("calibrate_seconds: " + str(self.lag_time))
        self._update_text('\n\n')

        self.config['calibrate_temp'] = self.lag_temp
        self.config['calibrate_seconds'] = self.lag_time
        self.config['has_calibrated'] = True

        with open('config.json', 'w') as f:
            ujson.dump(self.config, f)

        self._update_text('The oven controller will reboot in 3 seconds...')
        self.tim.deinit()
        self.tim.init(period=3000, mode=machine.Timer.ONE_SHOT, callback=lambda t: machine.reset())

    def start(self):
        lv.scr_load(self.temp_cali_scr)
        self._update_text("Calibration will start in 5sec...\n\n")
        utime.sleep(5)
        self._update_text("Starting...\n")
        self._update_text("Calibrating oven temperature to " + str(self.check_temp) + ' C`... \n')
        self.oven.on()
        self.tim.deinit()
        self.start_time = utime.time()
        self.tim.init(period=1000, mode=machine.Timer.PERIODIC, callback=lambda t: self._heating_cb_handler())
