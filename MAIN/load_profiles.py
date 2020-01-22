import uos
import ujson


class LoadProfiles:
    def __init__(self, default_alloy_name):
        self.profile_json_list = uos.listdir('profiles')
        self.profile_alloy_names = []
        self.profile_dict = {}
        for profile_path in self.profile_json_list:
            with open('profiles/' + profile_path, 'r') as f:
                detail = ujson.load(f)
                alloy_name = detail.get('alloy')
                self.profile_alloy_names.append(alloy_name)
                self.profile_dict[alloy_name] = detail
        self.profile_details = None
        self.default_alloy_index = self.profile_alloy_names.index(default_alloy_name)
        self.load_profile_details(default_alloy_name)

    def get_profile_alloy_names(self):
        return self.profile_alloy_names

    def load_profile_details(self, selected_alloy_name):
        self.profile_details = self.profile_dict.get(selected_alloy_name)
        return self.profile_details

    def get_default_alloy_index(self):
        return self.default_alloy_index

    def get_profile_title(self):
        if self.profile_details:
            return self.profile_details.get('title')
        else:
            raise Exception('Profile details must be loaded with load_profile_details(profile_name)')

    def get_chart_point_count(self):
        if self.profile_details:
            return self.profile_details.get('time_range')[-1]
        else:
            raise Exception('Profile details must be loaded with load_profile_details(profile_name)')

    def get_temp_range(self):
            if self.profile_details:
                return self.profile_details.get('temp_range')
            else:
                raise Exception('Profile details must be loaded with load_profile_details(profile_name)')

    def get_time_range(self):
            if self.profile_details:
                return self.profile_details.get('time_range')
            else:
                raise Exception('Profile details must be loaded with load_profile_details(profile_name)')

    def get_temp_profile(self):
            if self.profile_details:
                return self.profile_details.get('profile')
            else:
                raise Exception('Profile details must be loaded with load_profile_details(profile_name)')

    def get_profile_stages(self):
            if self.profile_details:
                return self.profile_details.get('stages')
            else:
                raise Exception('Profile details must be loaded with load_profile_details(profile_name)')

    def get_melting_temp(self):
            if self.profile_details:
                return self.profile_details.get('melting_point')
            else:
                raise Exception('Profile details must be loaded with load_profile_details(profile_name)')

    def _calc_chart_factor(self, chart_width, chart_height, chart_top_padding):
        temp_range = self.get_temp_range()
        temp_min = temp_range[0]
        temp_max = temp_range[-1]
        time_range = self.get_time_range()
        time_min = time_range[0]
        time_max = time_range[-1]
        x_factor = chart_width / time_max
        y_factor = chart_height / (temp_max - temp_min + chart_top_padding)
        temp_min_offset = temp_min * y_factor
        return x_factor, y_factor, temp_min_offset

    def get_profile_chart_points(self, chart_width, chart_height, chart_top_padding):
        """
        These points are for lv.line() to draw the ideal reflow temp profile to give the user a visual confirmation.
        The points are for lv.line(), make sure to set_y_invert(True)
        :param chart_width: width in pixel of the lv.chart
        :param chart_height: height in pixel of the lv.chart
        :param top_padding: empty space above the highest point
        :return: list of point x & y
        """
        x_factor, y_factor, temp_min_offset = self._calc_chart_factor(chart_width, chart_height, chart_top_padding)
        temp_profile_list = self.get_temp_profile()
        profile_chart_points = []
        for p in temp_profile_list:
            point = {
                'x': int(p[0] * x_factor),
                'y': int(p[-1] * y_factor - temp_min_offset),
            }
            profile_chart_points.append(point)
        return profile_chart_points

    def get_chart_melting_y_point(self, chart_width, chart_height, chart_top_padding):
        """
        For drawing a horizontal line marking the melting temp of the ideal reflow profile.
        """
        _, y_factor, temp_min_offset = self._calc_chart_factor(chart_width, chart_height, chart_top_padding)
        melting_temp = self.get_melting_temp()
        return int(melting_temp * y_factor - temp_min_offset)
