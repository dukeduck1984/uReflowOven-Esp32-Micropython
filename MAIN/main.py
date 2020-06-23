import machine
import network
import ujson
import uos

import lvgl as lv
import lvesp32

from ili9341 import ili9341
from xpt2046 import xpt2046

machine.freq(240000000)

with open('config.json', 'r') as f:
    config = ujson.load(f)

TOUCH_CALI_FILE = config.get('touch_cali_file')

disp = ili9341(
    miso = config['tft_pins']['miso'],
    mosi = config['tft_pins']['mosi'],
    clk = config['tft_pins']['sck'],
    cs = config['tft_pins']['cs'],
    dc = config['tft_pins']['dc'],
    rst = config['tft_pins']['rst'],
    power = config['tft_pins']['acc'],
    backlight = config['tft_pins']['led'],
    power_on = 0 if config['tft_pins']['acc_active_low'] else 1,
    backlight_on = 0 if config['tft_pins']['led_active_low'] else 1,
    width = 240 if config['tft_pins']['is_portrait'] else 320,
    height = 320 if config['tft_pins']['is_portrait'] else 240,
    rot = ili9341.PORTRAIT if config['tft_pins']['is_portrait'] else ili9341.LANDSCAPE
)

touch_setup = config.get('touch_pins')
TOUCH_CS = touch_setup.get('cs')
TOUCH_INTERRUPT = touch_setup.get('interrupt')

if TOUCH_CALI_FILE not in uos.listdir():
    touch = xpt2046(
        cs=TOUCH_CS,
        transpose=TFT_IS_PORTRAIT,
    )

    from touch_cali import TouchCali
    touch_cali = TouchCali(touch, config)
    touch_cali.start()

else:
    with open(TOUCH_CALI_FILE, 'r') as f:
        param = ujson.load(f)
        touch_x0 = param['cal_x0']
        touch_x1 = param['cal_x1']
        touch_y0 = param['cal_y0']
        touch_y1 = param['cal_y1']

    touch = xpt2046(
        cs=TOUCH_CS,
        transpose=TFT_IS_PORTRAIT,
        cal_x0=touch_x0,
        cal_x1=touch_x1,
        cal_y0=touch_y0,
        cal_y1=touch_y1,
    )

    import gc
    import utime
    import _thread
    from buzzer import Buzzer
    from gui import GUI
    from load_profiles import LoadProfiles
    from max31855 import MAX31855
    from oven_control import OvenControl
    from pid import PID

    reflow_profiles = LoadProfiles(config['default_alloy'])

    temp_sensor = MAX31855(
        hwspi = config['max31855_pins']['hwspi'],
        cs = config['max31855_pins']['cs'],
        miso = config['max31855_pins']['miso'],
        sck = config['max31855_pins']['sck'],
        offset = config['temp_offset'])

    heater = machine.Signal(machine.Pin(config['heater_pins']['heater'], machine.Pin.OUT), invert=config['heater_pins']['heater_active_low'])
    heater.off()

    buzzer = Buzzer(config['buzzer_pin'])

    timer = machine.Timer(0)

    TEMP_GUI_LAST_UPDATE = utime.ticks_ms()

    def measure_temp():
        global TEMP_GUI_LAST_UPDATE
        while True:
            try:
                temp_sensor.read_temp()
            except Exception:
                print('Error occurs when measuring temperature.')
            if utime.ticks_diff(utime.ticks_ms(), TEMP_GUI_LAST_UPDATE) >= 1000:
                gui.temp_update(temp_sensor.get_temp())
                TEMP_GUI_LAST_UPDATE = utime.ticks_ms()
            utime.sleep_ms(int(1000/config['sampling_hz']))


    def buzzer_activate():
        while True:
            if buzzer.song:
                buzzer.play_song(buzzer.song)
                gc.collect()
            else:
                pass


    _thread.stack_size(7 * 1024)
    temp_th = _thread.start_new_thread(measure_temp, ())
    buzzer_th = _thread.start_new_thread(buzzer_activate, ())

    pid = PID(config['pid']['kp'], config['pid']['ki'], config['pid']['kd'])

    gui = GUI(reflow_profiles, config, pid, temp_sensor)

    oven_control = OvenControl(heater, temp_sensor, pid, reflow_profiles, gui, buzzer, timer, config)

# Starting FTP service for future updates
ap = network.WLAN(network.AP_IF)
ap.config(essid='uReflowOven ftp://192.168.4.1')
ap.active(True)
while not ap.active():
    utime.sleep_ms(500)
else:
    import uftpd
