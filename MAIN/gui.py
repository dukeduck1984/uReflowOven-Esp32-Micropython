import machine
import ujson
import uos
import utime

import lvgl as lv
import lvesp32


class GUI:
    CHART_WIDTH = 240
    CHART_HEIGHT = 120
    CHART_TOP_PADDING = 10

    def __init__(self, profiles_obj, config_dict, pid_obj, sensor_obj):
        self.profiles = profiles_obj
        self.config = config_dict
        self.pid = pid_obj
        self.sensor = sensor_obj
        self.pid_params = self.config.get('pid')
        self.temp_offset = self.config.get('sensor_offset')
        self.alloy_list = self.profiles.get_profile_alloy_names()
        self.has_started = False
        self.main_scr = lv.obj()
        self.oven_title = self.oven_title_init()
        self.chart, self.chart_series = self.chart_init()
        self.profile_title_label, self.profile_title_cont, self.profile_title_text = self.profile_title_init()
        self.timer_label, self.timer_cont, self.timer_text = self.timer_init()
        self.profile_alloy_selector = self.profile_selector_init()
        self.start_btn, self.start_label = self.start_btn_init()
        self.stage_cont, self.stage_label = self.stage_init()
        self.settings_btn = self.settings_btn_init()
        self.temp_text = self.temp_init()
        self.led = self.led_init()
        self.line = None
        self.dashed_line = None
        self.point_count = None
        self.chart_point_list = None
        self.profile_detail_init()
        self.profile_alloy_selector.move_foreground()
        self.show_set_btn_hide_stage()
        self.reflow_process_start_cb = None
        self.reflow_process_stop_cb = None
        self.current_input_placeholder = 'Set Kp'
        lv.scr_load(self.main_scr)

    def profile_detail_init(self):
        """
        This method is called every time a different alloy profile is selected.
        1. Set reflow profile title per selection
        2. Draw ideal reflow temp profile in solid line and melting temp in dashed line
        3. Update chart settings to receive data points
        """
        # Set title
        self.profile_title = self.profiles.get_profile_title()
        self.set_profile_title_text(self.profile_title)
        # Draw ideal reflow temp profile in solid line
        self.profile_chart_points = self.profiles.get_profile_chart_points(
            GUI.CHART_WIDTH,
            GUI.CHART_HEIGHT,
            GUI.CHART_TOP_PADDING,
        )
        if self.line:
            lv.obj.delete(self.line)
            self.line = None
        self.line = self.draw_profile_line(self.profile_chart_points)
        # Draw melting temp in dashed line
        chart_melting_y_point = self.profiles.get_chart_melting_y_point(
            GUI.CHART_WIDTH,
            GUI.CHART_HEIGHT,
            GUI.CHART_TOP_PADDING,
        )
        melting_temp = self.profiles.get_melting_temp()
        if self.dashed_line:
            lv.obj.delete(self.dashed_line)
            self.dashed_line = None
        self.dashed_line = self.draw_melting_dash_line(chart_melting_y_point, melting_temp)
        # Update chart settings
        temp_range = self.profiles.get_temp_range()
        self.chart.set_range(temp_range[0], temp_range[-1] + GUI.CHART_TOP_PADDING)  # min, max temp in the chart
        self.point_count = self.profiles.get_chart_point_count()
        self.chart.set_point_count(self.point_count)
        self.chart_point_list = self.create_null_chart_list()

    def create_null_chart_list(self):
        """
        Generate a null list for the chart
        :return: List
        """
        return [lv.CHART_POINT.DEF] * self.point_count

    def chart_init(self):
        """
        Initialize the temp chart on the screen
        """
        chart = lv.chart(self.main_scr)
        chart.set_size(GUI.CHART_WIDTH, GUI.CHART_HEIGHT)  # width, height pixel of the chart
        chart.align(lv.scr_act(), lv.ALIGN.IN_BOTTOM_MID, 0, 0)
        chart.set_type(lv.chart.TYPE.LINE)
        chart.set_style(lv.chart.STYLE.MAIN, lv.style_plain)
        chart.set_series_opa(lv.OPA.COVER)
        chart.set_series_width(3)
        chart_series = chart.add_series(lv.color_make(0xFF, 0, 0))
        return chart, chart_series

    def chart_clear(self):
        """
        Clear the chart with null points
        """
        self.chart_point_list = self.create_null_chart_list()
        self.chart.set_points(self.chart_series, self.chart_point_list)

    def chart_update(self, temp, temp_position):
        """
        Update chart data, should be called every 1s
        :param temp: temp reading to update the chart
        :param temp_position: the index for the current temp reading
        """
        if 0 <= int(temp_position) <= len(self.chart_point_list) - 1:
            self.chart_point_list[int(temp_position)] = int(temp)
            self.chart.set_points(self.chart_series, self.chart_point_list)

    def draw_profile_line(self, points):
        """
        Draw reflow temp profile over the chart per selection
        """
        style_line = lv.style_t()
        lv.style_copy(style_line, lv.style_transp)
        style_line.line.color = lv.color_make(0, 0x80, 0)
        style_line.line.width = 3
        style_line.line.rounded = 1
        style_line.line.opa = lv.OPA._40
        line = lv.line(self.chart)
        line.set_points(points, len(points))  # Set the points
        line.set_style(lv.line.STYLE.MAIN, style_line)
        line.align(self.chart, lv.ALIGN.IN_BOTTOM_MID, 0, 0)
        line.set_y_invert(True)
        return line

    def draw_melting_dash_line(self, y_point, melting_temp):
        """
        Draw melting temp with dashed line over the chart
        """
        # Container for dashed line
        style_cont = lv.style_t()
        lv.style_copy(style_cont, lv.style_transp)
        dashed_segments = 10
        dashed_cont = lv.cont(self.chart)
        dashed_cont.set_style(lv.line.STYLE.MAIN, style_cont)
        dashed_cont.set_width(GUI.CHART_WIDTH)
        # Draw dashed line
        style_dash_line = lv.style_t()
        lv.style_copy(style_dash_line, lv.style_transp)
        style_dash_line.line.color = lv.color_make(0xFF, 0x68, 0x33)
        style_dash_line.line.width = 3
        dash_width = int(GUI.CHART_WIDTH / (dashed_segments * 2 - 1))
        dashed_points = [
            {'x': 0, 'y': 0},
            {'x': dash_width, 'y': 0}
        ]
        dashed_line0 = lv.line(dashed_cont)
        dashed_line0.set_points(dashed_points, len(dashed_points))
        dashed_line0.set_style(lv.line.STYLE.MAIN, style_dash_line)
        dashed_line0.align(None, lv.ALIGN.IN_LEFT_MID, 0, 0)
        for i in range(dashed_segments - 1):
            dl_name = 'dashed_line' + str(i+1)
            parent_name = 'dashed_line' + str(i)
            locals()[dl_name] = lv.line(dashed_cont, dashed_line0)
            locals()[dl_name].align(None, lv.ALIGN.IN_LEFT_MID, dash_width * (i+1) * 2, 0)
        # Melting temp
        melt_label = lv.label(dashed_cont)
        melt_label.set_recolor(True)
        melt_label.set_text('#FF6833 ' + str(melting_temp) + '#')
        # Put above elements in place
        dashed_cont.align_origo(self.chart, lv.ALIGN.IN_BOTTOM_MID, 0, -y_point)
        melt_label.align(dashed_cont, lv.ALIGN.IN_TOP_LEFT, 8, 12)
        return dashed_cont

    def led_init(self):
        """
        Initialize the LED on the screen
        """
        style_led = lv.style_t()
        lv.style_copy(style_led, lv.style_pretty_color)
        style_led.body.radius = 800  # large enough to draw a circle
        style_led.body.main_color = lv.color_make(0xb5, 0x0f, 0x04)
        style_led.body.grad_color = lv.color_make(0x50, 0x07, 0x02)
        style_led.body.border.color = lv.color_make(0xfa, 0x0f, 0x00)
        style_led.body.border.width = 3
        style_led.body.border.opa = lv.OPA._30
        style_led.body.shadow.color = lv.color_make(0xb5, 0x0f, 0x04)
        style_led.body.shadow.width = 5
        led = lv.led(self.main_scr)
        led.set_style(lv.led.STYLE.MAIN, style_led)
        led.align(lv.scr_act(), lv.ALIGN.IN_TOP_RIGHT, -10, 5)
        led.off()
        return led

    def led_turn_on(self):
        """
        Turn on the LED to indicate heating
        Should be called externally
        """
        self.led.on()

    def led_turn_off(self):
        """
        Turn off the LED to indicate not heating
        Should be called externally
        """
        self.led.off()

    def oven_title_init(self):
        """
        Initialize the oven title on the screen.
        """
        style_title = lv.style_t()
        lv.style_copy(style_title, lv.style_transp_fit)
        style_title.text.font = lv.font_roboto_28
        title_label = lv.label(self.main_scr)
        title_label.set_style(lv.label.STYLE.MAIN, style_title)
        title_label.set_text(self.config.get('title'))
        title_label.align(lv.scr_act(), lv.ALIGN.IN_TOP_LEFT, 8, 3)
        return title_label

    def profile_title_init(self):
        """
        Initialize reflow profile title on the screen
        """
        # Profile Label
        profile_label = lv.label(self.main_scr)
        profile_label.set_text('Profile:')
        profile_label.align(self.oven_title, lv.ALIGN.OUT_BOTTOM_LEFT, -4, 3)
        # Profile Container
        profile_cont = lv.cont(self.main_scr)
        profile_cont.set_size(80, 28)
        # profile_cont.set_auto_realign(True)
        profile_cont.align(profile_label, lv.ALIGN.OUT_BOTTOM_LEFT, 2, 2)
        profile_cont.set_fit(lv.FIT.NONE)
        profile_cont.set_layout(lv.LAYOUT.COL_M)
        # Profile Text
        profile_text = lv.label(profile_cont)
        profile_text.set_text('N/A')
        return profile_label, profile_cont, profile_text

    def set_profile_title_text(self, text):
        """
        Set the reflow profile title text
        It's called by another method.
        """
        self.profile_title_text.set_text(text)

    def profile_selector_init(self):
        """
        Initialize alloy reflow profile drop-down selector on the screen
        """
        # Alloy Label
        alloy_label = lv.label(self.main_scr)
        alloy_label.set_text('Solder Paste:')
        alloy_label.align(self.profile_title_label, lv.ALIGN.OUT_RIGHT_MID, 38, 0)

        this = self

        # paste alloy selection drop-down
        def alloy_select_handler(obj, event):
            if event == lv.EVENT.VALUE_CHANGED:
                profile_alloy_name = this.alloy_list[alloy_select.get_selected()]
                this.profiles.load_profile_details(profile_alloy_name)
                this.profile_detail_init()

        # style_selector = lv.style_t()
        # lv.style_copy(style_selector, lv.style_pretty_color)
        alloy_select = lv.ddlist(self.main_scr)
        alloy_select.set_options('\n'.join(self.alloy_list))
        alloy_select.set_selected(self.profiles.get_default_alloy_index())
        alloy_select.set_event_cb(alloy_select_handler)
        alloy_select.set_fix_width(140)
        alloy_select.set_draw_arrow(True)
        alloy_select.align(alloy_label, lv.ALIGN.OUT_BOTTOM_LEFT, 2, 2)
        alloy_select.set_style(lv.ddlist.STYLE.BG, lv.style_pretty_color)
        alloy_select.set_style(lv.ddlist.STYLE.SEL, lv.style_pretty_color)
        return alloy_select

    def disable_alloy_selector(self, is_disabled):
        if is_disabled:
            # style_disabled = lv.style_t()
            # lv.style_copy(style_disabled, lv.style_btn_ina)
            self.profile_alloy_selector.set_style(lv.ddlist.STYLE.BG, lv.style_btn_ina)
            self.profile_alloy_selector.set_style(lv.ddlist.STYLE.SEL, lv.style_btn_ina)
            self.profile_alloy_selector.set_click(False)
        else:
            # style_enabled = lv.style_t()
            # lv.style_copy(style_enabled, lv.style_pretty_color)
            # self.profile_alloy_selector.set_style(lv.ddlist.STYLE.MAIN, style_enabled)
            self.profile_alloy_selector.set_style(lv.ddlist.STYLE.BG, lv.style_pretty_color)
            self.profile_alloy_selector.set_style(lv.ddlist.STYLE.SEL, lv.style_pretty_color)
            self.profile_alloy_selector.set_click(True)

    def save_default_alloy(self):
        alloy_name = self.alloy_list[self.profile_alloy_selector.get_selected()]
        # with open('config.json', 'r') as f:
        #     data = ujson.load(f)
        # data['default_alloy'] = alloy_name
        self.config['default_alloy'] = alloy_name
        with open('config.json', 'w') as f:
            ujson.dump(self.config, f)

    def timer_init(self):
        """
        Initialize the timer on the screen
        """
        # Time Label
        time_label = lv.label(self.main_scr)
        time_label.set_text('Time:')
        time_label.align(self.profile_title_cont, lv.ALIGN.OUT_BOTTOM_LEFT, -2, 5)
        # Time Container
        time_cont = lv.cont(self.main_scr, self.profile_title_cont)
        time_cont.align(time_label, lv.ALIGN.OUT_BOTTOM_LEFT, 2, 2)
        # Time Text
        time_text = lv.label(time_cont)
        time_text.set_text('00:00')
        return time_label, time_cont, time_text

    def set_timer_text(self, time):
        """
        Update the timer with the elapsed time
        Should be called externally
        """
        self.timer_text.set_text(str(time))

    def temp_init(self):
        """
        Initialize the temp display on the screen
        """
        # Temp Label
        temp_label = lv.label(self.main_scr)
        temp_label.set_text('Temp(`C):')
        temp_label.align(self.timer_cont, lv.ALIGN.OUT_BOTTOM_LEFT, -2, 5)
        # Temp Container
        temp_cont = lv.cont(self.main_scr, self.profile_title_cont)
        temp_cont.align(temp_label, lv.ALIGN.OUT_BOTTOM_LEFT, 2, 2)
        # Temp Text
        temp_text = lv.label(temp_cont)
        temp_text.set_text('- - -')
        return temp_text

    def temp_update(self, temp):
        """
        Update the actual real-time temp
        Should be called externally
        """
        try:
            float(temp)
            temp = '{:.1f}'.format(temp)
        except ValueError:
            pass
        finally:
            self.temp_text.set_text(temp)

    def popup_confirm_stop(self):
        modal_style = lv.style_t()
        lv.style_copy(modal_style, lv.style_plain_color)
        modal_style.body.main_color = modal_style.body.grad_color = lv.color_make(0, 0, 0)
        modal_style.body.opa = lv.OPA._50
        bg = lv.obj(self.main_scr)
        bg.set_style(modal_style)
        bg.set_pos(0, 0)
        bg.set_size(self.main_scr.get_width(), self.main_scr.get_height())
        bg.set_opa_scale_enable(True)

        popup_stop = lv.mbox(bg)
        popup_stop.set_text('Do you really want to stop the soldering process?')
        btns = ['OK', 'Cancel', '']
        popup_stop.add_btns(btns)
        this = self

        def event_handler(obj, event):
            if event == lv.EVENT.VALUE_CHANGED:
                if popup_stop.get_active_btn() == 0:
                    this.set_reflow_process_on(False)
                else:
                    pass

                bg.del_async()
                popup_stop.start_auto_close(5)

        popup_stop.set_event_cb(event_handler)
        popup_stop.align(None, lv.ALIGN.CENTER, 0, 0)

    def popup_settings(self):
        modal_style = lv.style_t()
        lv.style_copy(modal_style, lv.style_plain_color)
        modal_style.body.main_color = modal_style.body.grad_color = lv.color_make(0, 0, 0)
        modal_style.body.opa = lv.OPA._50
        bg = lv.obj(self.main_scr)
        bg.set_style(modal_style)
        bg.set_pos(0, 0)
        bg.set_size(self.main_scr.get_width(), self.main_scr.get_height())
        bg.set_opa_scale_enable(True)

        popup_settings = lv.mbox(bg)
        popup_settings.set_text('Settings')
        btns = ['Set PID Params', '\n', 'Calibrate Touch', '\n', 'Close', '']
        popup_settings.add_btns(btns)

        lv.cont.set_fit(popup_settings, lv.FIT.NONE)
        mbox_style = popup_settings.get_style(popup_settings.STYLE.BTN_REL)
        popup_cali_style = lv.style_t()
        lv.style_copy(popup_cali_style, mbox_style)
        popup_cali_style.body.padding.bottom = 115
        popup_settings.set_style(popup_settings.STYLE.BTN_REL, popup_cali_style)
        popup_settings.set_height(186)

        def event_handler(obj, event):
            if event == lv.EVENT.VALUE_CHANGED:
                active_btn_text = popup_settings.get_active_btn_text()
                tim = machine.Timer(-1)
                # Note: With PID, temp calibration no longer needed
                # if active_btn_text == 'Temp Sensor':
                #     this.config['has_calibrated'] = False
                #     with open('config.json', 'w') as f:
                #         ujson.dump(this.config, f)
                #     tim.init(period=500, mode=machine.Timer.ONE_SHOT, callback=lambda t:machine.reset())
                # elif active_btn_text == 'Touch Screen':
                if active_btn_text == 'Calibrate Touch':
                    uos.remove(self.config.get('touch_cali_file'))
                    tim.init(period=500, mode=machine.Timer.ONE_SHOT, callback=lambda t: machine.reset())
                elif active_btn_text == 'Set PID Params':
                    tim.init(period=50, mode=machine.Timer.ONE_SHOT, callback=lambda t: self.popup_pid_params())
                else:
                    tim.deinit()
                bg.del_async()
                popup_settings.start_auto_close(5)

        popup_settings.set_event_cb(event_handler)
        popup_settings.align(None, lv.ALIGN.CENTER, 0, 0)

    def popup_pid_params(self):
        """
        The popup window of PID params settings
        """
        modal_style = lv.style_t()
        lv.style_copy(modal_style, lv.style_plain_color)
        modal_style.body.main_color = modal_style.body.grad_color = lv.color_make(0, 0, 0)
        modal_style.body.opa = lv.OPA._50
        bg = lv.obj(self.main_scr)
        bg.set_style(modal_style)
        bg.set_pos(0, 0)
        bg.set_size(self.main_scr.get_width(), self.main_scr.get_height())
        bg.set_opa_scale_enable(True)

        # init mbox and title
        popup_pid = lv.mbox(bg)
        popup_pid.set_text('Set PID Params')
        popup_pid.set_size(220, 300)
        popup_pid.align(bg, lv.ALIGN.CENTER, 0, 0)

        input_cont = lv.cont(popup_pid)
        input_cont.set_size(210, 180)

        def input_event_cb(ta, event):
            if event == lv.EVENT.CLICKED:
                self.current_input_placeholder = ta.get_placeholder_text()
                if self.current_input_placeholder == 'Set Offset':
                    popup_pid.align(bg, lv.ALIGN.CENTER, 0, -55)
                else:
                    popup_pid.align(bg, lv.ALIGN.CENTER, 0, 0)
                if kb.get_hidden():
                    kb.set_hidden(False)
                # Focus on the clicked text area
                kb.set_ta(ta)

        def keyboard_event_cb(event_kb, event):
            event_kb.def_event_cb(event)
            if event == lv.EVENT.CANCEL or event == lv.EVENT.APPLY:
                kb.set_hidden(True)
                if self.current_input_placeholder == 'Set Offset':
                    popup_pid.align(bg, lv.ALIGN.CENTER, 0, 0)

        # init keyboard
        kb = lv.kb(bg)
        kb.set_cursor_manage(True)
        kb.set_event_cb(keyboard_event_cb)
        lv.kb.set_mode(kb, lv.kb.MODE.NUM)
        rel_style = lv.style_t()
        pr_style = lv.style_t()
        lv.style_copy(rel_style, lv.style_btn_rel)
        rel_style.body.radius = 0
        rel_style.body.border.width = 1
        lv.style_copy(pr_style, lv.style_btn_pr)
        pr_style.body.radius = 0
        pr_style.body.border.width = 1
        kb.set_style(lv.kb.STYLE.BG, lv.style_transp_tight)
        kb.set_style(lv.kb.STYLE.BTN_REL, rel_style)
        kb.set_style(lv.kb.STYLE.BTN_PR, pr_style)

        # init text areas
        kp_input = lv.ta(input_cont)
        kp_input.set_text(str(self.pid_params.get('kp')))
        kp_input.set_placeholder_text('Set Kp')
        kp_input.set_accepted_chars('0123456789.+-')
        kp_input.set_one_line(True)
        kp_input.set_width(120)
        kp_input.align(input_cont, lv.ALIGN.IN_TOP_MID, 30, 20)
        kp_input.set_event_cb(input_event_cb)
        kp_label = lv.label(input_cont)
        kp_label.set_text("Kp: ")
        kp_label.align(kp_input, lv.ALIGN.OUT_LEFT_MID, 0, 0)
        pid_title_label = lv.label(input_cont)
        pid_title_label.set_text("PID Params:")
        pid_title_label.align(kp_input, lv.ALIGN.OUT_TOP_LEFT, -65, 0)

        ki_input = lv.ta(input_cont)
        ki_input.set_text(str(self.pid_params.get('ki')))
        ki_input.set_placeholder_text('Set Ki')
        ki_input.set_accepted_chars('0123456789.+-')
        ki_input.set_one_line(True)
        ki_input.set_width(120)
        ki_input.align(input_cont, lv.ALIGN.IN_TOP_MID, 30, 55)
        ki_input.set_event_cb(input_event_cb)
        ki_input.set_cursor_type(lv.CURSOR.LINE | lv.CURSOR.HIDDEN)
        ki_label = lv.label(input_cont)
        ki_label.set_text("Ki: ")
        ki_label.align(ki_input, lv.ALIGN.OUT_LEFT_MID, 0, 0)

        kd_input = lv.ta(input_cont)
        kd_input.set_text(str(self.pid_params.get('kd')))
        kd_input.set_placeholder_text('Set Kd')
        kd_input.set_accepted_chars('0123456789.+-')
        kd_input.set_one_line(True)
        kd_input.set_width(120)
        kd_input.align(input_cont, lv.ALIGN.IN_TOP_MID, 30, 90)
        kd_input.set_event_cb(input_event_cb)
        kd_input.set_cursor_type(lv.CURSOR.LINE | lv.CURSOR.HIDDEN)
        kd_label = lv.label(input_cont)
        kd_label.set_text("Kd: ")
        kd_label.align(kd_input, lv.ALIGN.OUT_LEFT_MID, 0, 0)

        temp_offset_input = lv.ta(input_cont)
        temp_offset_input.set_text(str(self.temp_offset))
        temp_offset_input.set_placeholder_text('Set Offset')
        temp_offset_input.set_accepted_chars('0123456789.+-')
        temp_offset_input.set_one_line(True)
        temp_offset_input.set_width(120)
        temp_offset_input.align(input_cont, lv.ALIGN.IN_TOP_MID, 30, 145)
        temp_offset_input.set_event_cb(input_event_cb)
        temp_offset_input.set_cursor_type(lv.CURSOR.LINE | lv.CURSOR.HIDDEN)
        temp_offset_label = lv.label(input_cont)
        temp_offset_label.set_text("Offset: ")
        temp_offset_label.align(temp_offset_input, lv.ALIGN.OUT_LEFT_MID, 0, 0)
        offset_title_label = lv.label(input_cont)
        offset_title_label.set_text("Temp Correction:")
        offset_title_label.align(temp_offset_input, lv.ALIGN.OUT_TOP_LEFT, -65, 0)

        # set btns to mbox
        btns = ['Save', 'Cancel', '']
        popup_pid.add_btns(btns)

        lv.cont.set_fit(popup_pid, lv.FIT.NONE)
        mbox_style = popup_pid.get_style(popup_pid.STYLE.BTN_REL)
        popup_pid_style = lv.style_t()
        lv.style_copy(popup_pid_style, mbox_style)
        popup_pid_style.body.padding.bottom = 46
        popup_pid.set_style(popup_pid.STYLE.BTN_REL, popup_pid_style)
        popup_pid.set_size(220, 300)

        def event_handler(obj, event):
            if event == lv.EVENT.VALUE_CHANGED:
                active_btn_text = popup_pid.get_active_btn_text()
                if active_btn_text == 'Save':
                    kp_value = float(kp_input.get_text())
                    ki_value = float(ki_input.get_text())
                    kd_value = float(kd_input.get_text())
                    temp_offset_value = float(temp_offset_input.get_text())
                    self.config['pid'] = {
                        'kp': kp_value,
                        'ki': ki_value,
                        'kd': kd_value
                    }
                    self.config['sensor_offset'] = temp_offset_value
                    self.pid_params = self.config.get('pid')
                    self.temp_offset = self.config.get('sensor_offset')
                    # Save settings to config.json
                    with open('config.json', 'w') as f:
                        ujson.dump(self.config, f)
                    # Apply settings immediately
                    self.pid.reset(kp_value, ki_value, kd_value)
                    self.sensor.set_offset(temp_offset_value)
                bg.del_async()
                popup_pid.start_auto_close(5)

        popup_pid.set_event_cb(event_handler)
        popup_pid.align(bg, lv.ALIGN.CENTER, 0, 0)
        kb.set_ta(kp_input)
        kb.set_hidden(True)

    def start_btn_init(self):
        """
        Initialize the Start/Stop button on the screen
        """
        this = self

        def start_btn_hander(obj, event):
            if event == lv.EVENT.CLICKED:
                if this.has_started:  # Clicked to stop the process
                    # popup to let user confirm the stop action
                    this.popup_confirm_stop()
                else:  # Clicked to start the process
                    this.set_reflow_process_on(True)

        start_btn = lv.btn(self.main_scr)
        start_btn.set_size(140, 60)
        start_btn.set_event_cb(start_btn_hander)
        start_btn.align(self.timer_label, lv.ALIGN.IN_TOP_RIGHT, 190, 0)
        style_start = lv.style_t()
        lv.style_copy(style_start, lv.style_btn_rel)
        style_start.text.font = lv.font_roboto_28
        start_label = lv.label(start_btn)
        start_label.set_text(lv.SYMBOL.PLAY + ' Start')
        start_label.set_style(lv.label.STYLE.MAIN, style_start)
        return start_btn, start_label

    def set_start_btn_to_stop(self):
        """
        Set the Start/Stop button status to 'Stop'
        It indicates that the reflow process is on.
        """
        self.start_label.set_text(lv.SYMBOL.STOP + ' Stop')

    def reset_start_btn(self):
        """
        Set the Start/Stop button status back to 'Start'
        It indicates that the reflow process is off (has finished, or not started yet).
        """
        self.start_label.set_text(lv.SYMBOL.PLAY + ' Start')

    def settings_btn_init(self):
        # Cali Button
        def settings_btn_handler(obj, event):
            if event == lv.EVENT.CLICKED:
                # let user choose what to calibrate: touch screen or temp
                self.popup_settings()

        settings_btn = lv.btn(self.main_scr)
        settings_btn.set_size(140, 38)
        settings_btn.align(self.start_btn, lv.ALIGN.OUT_BOTTOM_LEFT, 0, 5)
        settings_btn.set_event_cb(settings_btn_handler)
        cali_label = lv.label(settings_btn)
        cali_label.set_text(lv.SYMBOL.SETTINGS + ' Settings')
        return settings_btn

    def stage_init(self):
        # Stage Container
        stage_cont = lv.cont(self.main_scr)
        stage_cont.set_size(140, 38)
        # stage_cont.set_auto_realign(True)
        stage_cont.align(self.start_btn, lv.ALIGN.OUT_BOTTOM_LEFT, 0, 5)
        stage_cont.set_fit(lv.FIT.NONE)
        stage_cont.set_layout(lv.LAYOUT.CENTER)
        style_stage = lv.style_t()
        lv.style_copy(style_stage, lv.style_plain)
        style_stage.text.font = lv.font_roboto_22
        stage_cont.set_style(lv.label.STYLE.MAIN, style_stage)
        stage_label = lv.label(stage_cont)
        stage_label.set_style(lv.label.STYLE.MAIN, style_stage)
        stage_label.set_recolor(True)
        stage_label.set_long_mode(lv.label.LONG.SROLL)
        stage_label.set_width(128)
        stage_label.set_text('')
        return stage_cont, stage_label

    def set_stage_text(self, text):
        """
        Update the stage info to let user know which stage of the reflow is going now.
        Should be called externally
        """
        self.stage_label.set_text(text)

    def show_stage_hide_set_btn(self):
        """
        Hide the calibration button to show the stage info.
        """
        self.stage_cont.set_hidden(False)
        self.settings_btn.set_hidden(True)

    def show_set_btn_hide_stage(self):
        """
        Hide the stage info to show the calibration button
        """
        self.stage_cont.set_hidden(True)
        self.settings_btn.set_hidden(False)

    def add_reflow_process_start_cb(self, start_cb):
        self.reflow_process_start_cb = start_cb

    def add_reflow_process_stop_cb(self, stop_cb):
        self.reflow_process_stop_cb = stop_cb

    def set_reflow_process_on(self, is_on):
        if is_on:
            self.has_started = is_on
            self.set_start_btn_to_stop()
            # disable the alloy selector
            self.disable_alloy_selector(is_on)
            self.show_stage_hide_set_btn()
            # clear temp chart data
            self.chart_clear()
            # save selected alloy to config.json as default_alloy
            self.save_default_alloy()
            if self.reflow_process_start_cb:
                self.reflow_process_start_cb()
        else:
            is_off = is_on
            self.has_started = is_off
            self.reset_start_btn()
            self.disable_alloy_selector(is_off)
            self.show_set_btn_hide_stage()
            if self.reflow_process_stop_cb:
                self.reflow_process_stop_cb()
