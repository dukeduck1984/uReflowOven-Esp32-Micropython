class PID:
    def __init__(self, kp=2, ki=0.0001, kd=2):
        self.k_p = float(kp)
        self.k_i = float(ki)
        self.k_d = float(kd)
        self.k_p_backup = self.k_p
        self.k_i_backup = self.k_i
        self.k_d_backup = self.k_d
        self.last_error = 0
        self.integration = 0
        self.last_output = 0
        self.ki_is_enabled = False

    def update(self, temp, setpoint):
        """
        temp: float; real-time temperature measured by ds18 sensor
        setpoint: float; target temperature to achieve
        return: float; temperature correction
        """
        error = float(setpoint) - float(temp)
        if self.last_error == 0:
            self.last_error = error #catch first run error

        P_value = self.k_p * error
        # D_value = -(self.k_d * (error - self.last_error))
        D_value = self.k_d * (error - self.last_error)
        self.last_error = error
        # if -10 < self.last_output < 10:
        if self.ki_is_enabled:
            self.integration = self.integration + error

        I_value = self.integration * self.k_i

        # self.last_output = max(min(P_value + I_value + D_value, 15), -200)
        self.last_output = P_value + I_value + D_value
        return self.last_output

    def ki_enable(self, enabled):
        self.ki_is_enabled = enabled

    def reset(self, kp=0, ki=0, kd=0):
        if kp or ki or kd:
            self.k_p = float(kp)
            self.k_i = float(ki)
            self.k_d = float(kd)
        else:
            self.k_p = self.k_p_backup
            self.k_i = self.k_i_backup
            self.k_d = self.k_d_backup
