from time import sleep
import machine
import ujson
import uos
import utime
import network
import usocket as socket
import gc
import select 

class GUI:
    def __init__(self, profiles_obj, config_dict, pid_obj, sensor_obj):
        # self.profiles = profiles_obj
        # self.config = config_dict
        # self.pid = pid_obj
        # self.sensor = sensor_obj
        # self.pid_params = self.config.get('pid')
        # self.temp_offset = self.config.get('sensor_offset')
        # self.alloy_list = self.profiles.get_profile_alloy_names()
        self.has_started = False
        self.profile_title_text = ""
        self.timer_text = ""
        self.timer = 0
        self.stage_text = ""
        self.temp_text = self.temp_init()
        self.temp = 0
        self.heating = False
        self.line = None
        self.dashed_line = None
        self.point_count = None
        self.chart_point_list = []
        self.reflow_process_start_cb = None
        self.reflow_process_stop_cb = None
        self.server = None

    def chart_clear(self):
        """
        Clear the chart with null points
        """
        pass
        # self.chart_point_list.clear()

    def chart_update(self, temp_list):
        """
        Update chart data, should be called every 1s
        :param temp_list: list of actual temp with increasing length - new point appended to the tail
        """
        pass

    def led_turn_on(self):
        """
        Turn on the LED to indicate heating
        Should be called externally
        """
        pass

    def led_turn_off(self):
        """
        Turn off the LED to indicate not heating
        Should be called externally
        """
        pass

    def set_profile_title_text(self, text):
        """
        Set the reflow profile title text
        It's called by another method.
        """
        pass

    def save_default_alloy(self):
        pass
        # alloy_name = self.alloy_list[0]
        # # with open('config.json', 'r') as f:
        # #     data = ujson.load(f)
        # # data['default_alloy'] = alloy_name
        # self.config['default_alloy'] = alloy_name
        # with open('config.json', 'w') as f:
        #     ujson.dump(self.config, f)

    def set_timer(self, time):
        """
        just for compatibility
        """
        pass

    def set_timer_text(self, time):
        """
        Update the timer with the elapsed time
        Should be called externally
        """
        pass

    def temp_init(self):
        """
        Initialize the temp display on the screen
        """
        pass

    def temp_update(self, temp):
        """
        Update the actual real-time temp
        Should be called externally
        """
        pass

    def set_pid_params(self, kp_input,ki_input, kd_input, temp_offset_input ):
        """
        The popup window of PID params settings
        """
        pass
        # kp_value = float(kp_input)
        # ki_value = float(ki_input)
        # kd_value = float(kd_input)
        # temp_offset_value = float(temp_offset_input)
        # self.config['pid'] = {
        #     'kp': kp_value,
        #     'ki': ki_value,
        #     'kd': kd_value
        # }
        # self.config['sensor_offset'] = temp_offset_value
        # self.pid_params = self.config.get('pid')
        # self.temp_offset = self.config.get('sensor_offset')
        # # Save settings to config.json
        # with open('config.json', 'w') as f:
        #     ujson.dump(self.config, f)
        # # Apply settings immediately
        # self.pid.reset(kp_value, ki_value, kd_value)
        # self.sensor.set_offset(temp_offset_value)

    def set_stage_text(self, text):
        """
        Update the stage info to let user know which stage of the reflow is going now.
        Should be called externally
        """
        pass
        # self.stage_text = text

    def add_reflow_process_start_cb(self, start_cb):
        # ✔
        pass
        # self.reflow_process_start_cb = start_cb

    def add_reflow_process_stop_cb(self, stop_cb):
        # ✔
        pass
        # self.reflow_process_stop_cb = stop_cb

    def set_reflow_process_on(self, is_on):
        pass
        # if is_on:
        #     self.has_started = is_on
        #     # disable the alloy selector
        #     # clear temp chart data
        #     self.chart_clear()
        #     # save selected alloy to config.json as default_alloy
        #     self.save_default_alloy()
        #     if self.reflow_process_start_cb:
        #         self.reflow_process_start_cb()
        # else:
        #     is_off = is_on
        #     self.has_started = is_off
        #     if self.reflow_process_stop_cb:
        #         self.reflow_process_stop_cb()