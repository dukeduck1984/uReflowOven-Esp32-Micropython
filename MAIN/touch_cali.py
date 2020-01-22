import machine
import ujson
import utime

import lvgl as lv
import lvesp32


class TouchCali:
    def __init__(self, touch_obj, config):
        self.touch_obj = touch_obj
        self.config = config
        self.cali_counter = 0
        self.touch_cali_scr = lv.obj()
        self.touch_cali_scr.set_click(True)
        self.scr_width = self.touch_obj.screen_width
        self.scr_height = self.touch_obj.screen_height
        self.marker_pos = [
            (int(self.scr_width * 0.6), int(self.scr_height * 0.4)),
            (int(self.scr_width * 0.1), int(self.scr_height * 0.1)),
            (int(self.scr_width * 0.9), int(self.scr_height * 0.1)),
            (int(self.scr_width * 0.1), int(self.scr_height * 0.9)),
            (int(self.scr_width * 0.9), int(self.scr_height * 0.9)),
            (int(self.scr_width * 0.4), int(self.scr_height * 0.6)),
        ]
        self.marker_x, self.marker_y = self.marker_pos[self.cali_counter]
        self.marker_x_coords = []
        self.marker_y_coords = []
        self.raw_x_coords = []
        self.raw_y_coords = []

        self.marker_label = lv.label(self.touch_cali_scr)
        self.marker_label.set_recolor(True)
        self.marker_label.set_text('#FF0000 ' + lv.SYMBOL.PLUS + '#')
        self.marker_label.align_origo(self.touch_cali_scr, lv.ALIGN.IN_TOP_LEFT, self.marker_x, self.marker_y)

        text_style = lv.style_t()
        lv.style_copy(text_style, lv.style_transp_tight)
        text_style.text.font = lv.font_roboto_12
        self.text_label = lv.label(self.touch_cali_scr)
        self.text_label.set_style(lv.label.STYLE.MAIN, text_style)
        # text_label.align(cali_scr, lv.ALIGN.IN_TOP_LEFT, marker_x, marker_y)
        self.text_label.set_align(lv.label.ALIGN.CENTER)
        self.text_label.set_recolor(True)
        self.text_label.set_text('Click the marker\nto calibrate.')
        self.text_label.align_origo(self.touch_cali_scr, lv.ALIGN.CENTER, 0, 0)

    def start(self):
        self.touch_cali_scr.set_event_cb(self.touch_cali_handler)
        lv.scr_load(self.touch_cali_scr)

    def touch_cali_handler(self, obj, event):
        if event == lv.EVENT.PRESSED:
            if self.touch_obj.transpose:
                raw_y, raw_x = self.touch_obj.get_med_coords(3)
            else:
                raw_x, raw_y = self.touch_obj.get_med_coords(3)
            self.raw_x_coords.append(raw_x)
            self.raw_y_coords.append(raw_y)
            self.marker_x_coords.append(self.marker_x)
            self.marker_y_coords.append(self.marker_y)
            # globals()['coord_' + str(cali_counter)] = lv.label(cali_scr)
            # globals()['coord_' + str(cali_counter)].align(cali_scr, lv.ALIGN.IN_TOP_LEFT, marker_x, marker_y)
            # globals()['coord_' + str(cali_counter)].set_text('Raw_X: {}\nRaw_Y: {}'.format(raw_x, raw_y))
            if self.cali_counter < len(self.marker_pos) - 1:
                self.cali_counter += 1
                self.marker_x, self.marker_y = self.marker_pos[self.cali_counter]
                self.marker_label.align_origo(self.touch_cali_scr, lv.ALIGN.IN_TOP_LEFT, self.marker_x, self.marker_y)
                # text_label.align(cali_scr, lv.ALIGN.IN_TOP_LEFT, marker_x, marker_y)
            else:
                self.marker_label.set_hidden(True)
                self.text_label.set_text('#16A000 Calibration Done!#\n#16A000 Click the screen to reboot.#')
                self.text_label.align_origo(self.touch_cali_scr, lv.ALIGN.CENTER, 0, 0)
                print('calibration done.')
                self.touch_cali_result()
                utime.sleep_ms(300)
                self.touch_cali_scr.set_event_cb(
                    lambda obj, event: machine.reset() if event == lv.EVENT.PRESSED else None)

    def touch_cali_result(self):
        cal_x0_list = []
        cal_x1_list = []
        cal_y0_list = []
        cal_y1_list = []
        counter = len(self.raw_x_coords) // 2
        for i in range(counter * 2):
            if i % 2 == 0:
                x1 = (-self.scr_width * self.raw_x_coords[i] + self.raw_x_coords[i] * self.marker_x_coords[
                    i + 1] + self.scr_width *
                      self.raw_x_coords[i + 1] - self.raw_x_coords[i + 1] * self.marker_x_coords[i]) \
                     / \
                     (-self.marker_x_coords[i] + self.marker_x_coords[i + 1])
                x0 = (self.scr_width * self.raw_x_coords[i] - self.marker_x_coords[i] * x1) \
                     / \
                     (self.scr_width - self.marker_x_coords[i])
                y1 = (-self.scr_height * self.raw_y_coords[i] + self.raw_y_coords[i] * self.marker_y_coords[
                    i + 1] + self.scr_height *
                      self.raw_y_coords[
                          i + 1] - self.raw_y_coords[i + 1] * self.marker_y_coords[i]) \
                     / \
                     (-self.marker_y_coords[i] + self.marker_y_coords[i + 1])
                y0 = (self.scr_height * self.raw_y_coords[i] - self.marker_y_coords[i] * y1) \
                     / \
                     (self.scr_height - self.marker_y_coords[i])

                cal_x0_list.append(x0)
                cal_x1_list.append(x1)
                cal_y0_list.append(y0)
                cal_y1_list.append(y1)

        cal_x0 = int(sum(cal_x0_list) / len(cal_x0_list))
        cal_x1 = int(sum(cal_x1_list) / len(cal_x1_list))
        cal_y0 = int(sum(cal_y0_list) / len(cal_y0_list))
        cal_y1 = int(sum(cal_y1_list) / len(cal_y1_list))
        print('cal_x0 = {}; cal_x1 = {};'.format(cal_x0, cal_x1))
        print('cal_y0 = {}; cal_y1 = {};'.format(cal_y0, cal_y1))
        with open(self.config.get('touch_cali_file'), 'w') as f:
            data = {
                'cal_x0': cal_x0,
                'cal_x1': cal_x1,
                'cal_y0': cal_y0,
                'cal_y1': cal_y1,
            }
            try:
                ujson.dump(data, f)
            except:
                print('Error occurs when saving calibration results.')
            else:
                print('Calibration params saved.')
