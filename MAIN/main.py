import machine
import gc
import ujson
import uos
import network
import usocket as socket
from microWebSrv import MicroWebSrv

machine.freq(240000000)

with open('config.json', 'r') as f:
    config = ujson.load(f)

if config['tft_gui']['enable']:
    import lvgl as lv
    import lvesp32

    from ili9341 import ili9341
    from xpt2046 import xpt2046

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
        with open(config.get('touch_cali_file'), 'r') as f:
            touch_args = ujson.load(f)
    touch_args['cs'] = config['touch_pins']['cs']
    touch_args['transpose'] = config['tft_pins']['is_portrait']
    touch = xpt2046(**touch_args)

if config['tft_gui']['enable']:
    if config.get('touch_cali_file') not in uos.listdir():
        from touch_cali import TouchCali
        touch_cali = TouchCali(touch, config)
        touch_cali.start()
else:
    import gc
    import utime
    import _thread
    from buzzer import Buzzer
    from load_profiles import LoadProfiles
    from oven_control import OvenControl
    from pid import PID
    if config['tft_gui']['enable']:
        from gui import GUI
    else:
        from web_gui_api import GUI
    if config.get('sensor_type') == 'MAX6675':
        from max6675 import MAX6675 as Sensor
    else:
        from max31855 import MAX31855 as Sensor

    reflow_profiles = LoadProfiles(config['default_alloy'])

    temp_sensor = Sensor(
        hwspi = config['sensor_pins']['hwspi'],
        cs = config['sensor_pins']['cs'],
        miso = config['sensor_pins']['miso'],
        sck = config['sensor_pins']['sck'],
        offset = config['sensor_offset'],
        cache_time = int(1000/config['sampling_hz'])
    )

    heater = machine.Signal(
        machine.Pin(config['heater_pins']['heater'], machine.Pin.OUT),
        invert=config['heater_pins']['heater_active_low']
    )
    heater.off()

    buzzer = Buzzer(config['buzzer_pin'])

    def measure_temp():
        global TEMP_GUI_LAST_UPDATE
        while True:
            try:
                t = temp_sensor.get_temp()
            except Exception as e:
                t = str(e)
            # gui.temp_update(t)
            # print("temperature: {0}".format(t))
            gc.collect()
            utime.sleep_ms(int(1000/config['display_refresh_hz']))

    def buzzer_activate():
        while True:
            if buzzer.song:
                buzzer.play_song(buzzer.song)
                gc.collect()

    # _thread.stack_size(7 * 1024)
    # temp_th = _thread.start_new_thread(measure_temp, ())
    buzzer_th = _thread.start_new_thread(buzzer_activate, ())

    pid = PID(config['pid']['kp'], config['pid']['ki'], config['pid']['kd'])

    gui = GUI(reflow_profiles, config, pid, temp_sensor)

    sta_if = network.WLAN(network.STA_IF)

    ap_if = network.WLAN(network.AP_IF)

    sta_if.active(True)

    sta_if.connect(config['wifi']['ssid'], config['wifi']['passwd'])

    while not sta_if.isconnected():
        utime.sleep_ms(200)
        print("sta_if not connected yet")

    print("sta_if connected")
    print(sta_if.ifconfig())

    # web_gui_th = _thread.start_new_thread(gui.server_run, ())
    oven_control = OvenControl(heater, temp_sensor, pid, reflow_profiles, gui, buzzer, machine.Timer(0), config)

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

# start web gui api
# _thread.start_new_thread(server_run, ())


def memcheck(full=False):
  F = gc.mem_free()
  A = gc.mem_alloc()
  T = F+A
  P = '{0:.2f}%'.format(F/T*100)
  print('Total:{0} Free:{1} ({2})'.format(T,F,P))

# from microWebSrv import MicroWebSrv

srvhandle = None

@MicroWebSrv.route('/test')
def _httpHandlerTestGet(httpClient, httpResponse) :
    content = """ %s """% httpClient.GetIPAddr()
    httpResponse.WriteResponseOk( headers = None, contentType = "text/html", contentCharset = "UTF-8",content = content )

@MicroWebSrv.route('/stop-webserver')
def _httpHandlerTestGet(httpClient, httpResponse) :
    # print(self.temp)
    try:
        srvhandle.Stop()
        content = "ok"
    except Exception as e:
        content = """ %s """% e
        print(content)
    # httpResponse.WriteResponseOk( headers = None, contentType = "text/html", contentCharset = "UTF-8",content = content )

@MicroWebSrv.route('/start')
def _httpHandlerTestGet(httpClient, httpResponse) :
    oven_control.reflow_process_start()
    gc.collect()
    httpResponse.WriteResponseJSONOk(obj = {"result":"ok", "processing": True},  headers = { 'Access-Control-Allow-Origin' : '*'});

@MicroWebSrv.route('/stop')
def _httpHandlerTestGet(httpClient, httpResponse) :
    oven_control.reflow_process_stop()
    gc.collect()
    httpResponse.WriteResponseJSONOk(obj = {"result":"ok", "processing": False}, headers = { 'Access-Control-Allow-Origin' : '*'});

@MicroWebSrv.route('/status')
def _httpHandlerTestGet(httpClient, httpResponse) :
    resp = {"processing": "self.has_started", 
            "time": oven_control.timer_timediff, 
            "temperature": oven_control.get_temp(), 
            "stage": oven_control.oven_state}
    memcheck()
    gc.collect()
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
    httpResponse.WriteResponseJSONOk(obj = resp, headers = { 'Access-Control-Allow-Origin' : '*'});

@MicroWebSrv.route('/setpid',  'POST')
def _httpHandlerTestGet(httpClient, httpResponse) :

    formData  = httpClient.ReadRequestPostedFormData()

    print(formData)
    
    kp = formData["kp"]
    ki = formData["ki"]
    kd = formData["kd"]

    kp_value = float(kp)
    ki_value = float(ki)
    kd_value = float(kd)
    print('kp:{0} ki:{1} kd:{2}'.format(kp,ki,kd))
    config['pid'] = {
        'kp': kp_value,
        'ki': ki_value,
        'kd': kd_value
    }
    # Save settings to config.json
    with open('config.json', 'w') as f:
        ujson.dump(config, f)
    # restart to take effect

    resp = {"processing": "self.has_started", 
            "time": oven_control.timer_timediff, 
            "temperature": oven_control.get_temp(), 
            "stage": oven_control.oven_state}
    memcheck()
    gc.collect()
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
    httpResponse.WriteResponseJSONOk(obj = resp, headers = { 'Access-Control-Allow-Origin' : '*'});

@MicroWebSrv.route('/getpid')
def _httpHandlerTestGet(httpClient, httpResponse) :
    resp = config['pid']
    memcheck()
    gc.collect()
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
    httpResponse.WriteResponseJSONOk(obj = resp, headers = { 'Access-Control-Allow-Origin' : '*'});


srv = MicroWebSrv(webPath='www/')
srvhandle = srv
