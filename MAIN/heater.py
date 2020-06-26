import machine


class Heater:
    def __init__(self, pin, active_low=0):
        """
        Initialize heater pin
        """
        self.active_low = active_low
        if self.active_low:
            self.pin = machine.Pin(pin, machine.Pin.OUT, value=1)
        else:
            self.pin = machine.Pin(pin, machine.Pin.OUT, value=0)

    def on(self):
        if self.active_low:
            self.pin.off()
        else:
            self.pin.on()

    def off(self):
        if self.active_low:
            self.pin.on()
        else:
            self.pin.off()
