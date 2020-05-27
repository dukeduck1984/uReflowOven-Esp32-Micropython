import machine
import ujson
import uos
import utime

import lvgl as lv
import lvesp32


# TODO #1 adding settings for PID parameters and temp offset
# TODO #2 get rid of temp calibration button
class GUI:
    CHART_WIDTH = 240
    CHART_HEIGHT = 120
    CHART_TOP_PADDING = 10

    def __init__(self, profiles_obj, config_dict):
        self.profiles = profiles_obj
        self.config = config_dict
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
        self.cali_btn = self.cali_btn_init()
        self.temp_text = self.temp_init()
        self.led = self.led_init()
        self.line = None
        self.dashed_line = None
        self.null_chart_point_list = None
        self.profile_detail_init()
        self.profile_alloy_selector.move_foreground()
        self.show_cali_btn_hide_stage()
        self.reflow_process_start_cb = None
        self.reflow_process_stop_cb = None
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
        point_count = self.profiles.get_chart_point_count()
        self.chart.set_point_count(point_count)
        self.null_chart_point_list = [lv.CHART_POINT.DEF] * point_count

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
        self.chart.set_points(self.chart_series, self.null_chart_point_list)

    def chart_update(self, temp_list):
        """
        Update chart data, should be called every 1s
        :param temp_list: list of actual temp with increasing length - new point appended to the tail
        """
        list_length = len(temp_list)
        data_points = self.null_chart_point_list.copy()
        data_points[:list_length] = temp_list
        self.chart.set_points(self.chart_series, data_points)

    def draw_profile_line(self, points):
        """
        Draw ideal reflow temp profile over the chart per selection
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
            {'x': dash_width,'y':0}
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
        title_label.set_text('uReflow Oven')
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
        temp_label.set_text('Temp(C`):')
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
        self.temp_text.set_text('{:.1f}'.format(temp))

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

    def popup_calibration(self):
        modal_style = lv.style_t()
        lv.style_copy(modal_style, lv.style_plain_color)
        modal_style.body.main_color = modal_style.body.grad_color = lv.color_make(0, 0, 0)
        modal_style.body.opa = lv.OPA._50
        bg = lv.obj(self.main_scr)
        bg.set_style(modal_style)
        bg.set_pos(0, 0)
        bg.set_size(self.main_scr.get_width(), self.main_scr.get_height())
        bg.set_opa_scale_enable(True)

        popup_cali = lv.mbox(bg)
        popup_cali.set_text('What would you like to calibrate?')
        btns = ['Temp Sensor', '\n', 'Touch Screen', '\n', 'Cancel', '']
        popup_cali.add_btns(btns)

        lv.cont.set_fit(popup_cali, lv.FIT.NONE)
        mbox_style = popup_cali.get_style(popup_cali.STYLE.BTN_REL)
        popup_cali_style = lv.style_t()
        lv.style_copy(popup_cali_style, mbox_style)
        popup_cali_style.body.padding.bottom = 96
        popup_cali.set_style(popup_cali.STYLE.BTN_REL, popup_cali_style)

        popup_cali.set_height(186)

        this = self

        def event_handler(obj, event):
            if event == lv.EVENT.VALUE_CHANGED:
                active_btn_text = popup_cali.get_active_btn_text()
                tim = machine.Timer(-1)
                if active_btn_text == 'Temp Sensor':
                    this.config['has_calibrated'] = False
                    with open('config.json', 'w') as f:
                        ujson.dump(this.config, f)
                    tim.init(period=500, mode=machine.Timer.ONE_SHOT, callback=lambda t:machine.reset())
                elif active_btn_text == 'Touch Screen':
                    uos.remove(this.config.get('touch_cali_file'))
                    tim.init(period=500, mode=machine.Timer.ONE_SHOT, callback=lambda t:machine.reset())
                else:
                    tim.deinit()

                bg.del_async()
                popup_cali.start_auto_close(5)

        popup_cali.set_event_cb(event_handler)
        popup_cali.align(None, lv.ALIGN.CENTER, 0, 0)
        self.popup_cali = popup_cali
        return self.popup_cali

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

    def cali_btn_init(self):
        # Cali Button
        this = self

        def cali_btn_handler(obj, event):
            if event == lv.EVENT.CLICKED:
                # let user choose what to calibrate: touch screen or temp
                this.popup_calibration()

        cali_btn = lv.btn(self.main_scr)
        cali_btn.set_size(140, 38)
        cali_btn.align(self.start_btn, lv.ALIGN.OUT_BOTTOM_LEFT, 0, 5)
        cali_btn.set_event_cb(cali_btn_handler)
        cali_label = lv.label(cali_btn)
        cali_label.set_text(lv.SYMBOL.SETTINGS + ' Calibration')
        return cali_btn

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

    def show_stage_hide_cali_btn(self):
        """
        Hide the calibration button to show the stage info.
        """
        self.stage_cont.set_hidden(False)
        self.cali_btn.set_hidden(True)

    def show_cali_btn_hide_stage(self):
        """
        Hide the stage info to show the calibration button
        """
        self.stage_cont.set_hidden(True)
        self.cali_btn.set_hidden(False)

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
            self.show_stage_hide_cali_btn()
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
            self.show_cali_btn_hide_stage()
            if self.reflow_process_stop_cb:
                self.reflow_process_stop_cb()
