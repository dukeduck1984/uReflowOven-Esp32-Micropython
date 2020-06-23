import machine
import ujson
import uos
import lvgl as lv
import lvesp32

from ili9341 import ili9341
from xpt2046 import xpt2046

machine.freq(240000000)

config = ujson.load(open('config.json', 'r'))

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

touch_args = {}
if config.get('touch_cali_file') in uos.listdir():
    touch_args = ujson.load(open(config.get('touch_cali_file'), 'r'))
touch_args['cs'] = config['touch_pins']['cs']
touch_args['transpose'] = config['tft_pins']['is_portrait']
touch = xpt2046(**touch_args)

if config.get('touch_cali_file') not in uos.listdir():
    from touch_cali import TouchCali
    touch_cali = TouchCali(touch, config)
    touch_cali.start()

else:
    import gc
    import utime
    import _thread
    from buzzer import Buzzer
    from heater import Heater
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
        offset = config['temp_offset'],
        cache_time = int(1000/config['sampling_hz'])
    )

    oven = Heater(config['heater_pins']['heater'], config['heater_pins']['heater_active_low'])

    buzzer = Buzzer(config['buzzer_pin'])

    def measure_temp():
        global TEMP_GUI_LAST_UPDATE
        while True:
            try:
                t = temp_sensor.get_temp()
            except Exception as e:
                t = str(e)
            gui.temp_update(t)
            utime.sleep_ms(int(1000/config['display_refresh_hz']))

    def buzzer_activate():
        while True:
            if buzzer.song:
                buzzer.play_song(buzzer.song)
                gc.collect()

    _thread.stack_size(7 * 1024)
    temp_th = _thread.start_new_thread(measure_temp, ())
    buzzer_th = _thread.start_new_thread(buzzer_activate, ())

    pid = PID(config['pid']['kp'], config['pid']['ki'], config['pid']['kd'])

    gui = GUI(reflow_profiles, config, pid, temp_sensor)

    oven_control = OvenControl(oven, temp_sensor, pid, reflow_profiles, gui, buzzer, machine.Timer(0), config)

# Starting FTP service for future updates
if config['ftp']['enable']:
    import network
    ap = network.WLAN(network.AP_IF)
    ap.config(essid=config['ftp']['ssid'])
    ap.active(True)
    while not ap.active():
        utime.sleep_ms(500)
    else:
        import uftpd
