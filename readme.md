## μReflow Oven with MicroPython & LittlevGL

This project is modifided and rewritten on top of [Adafruit EZ Make Oven](https://learn.adafruit.com/ez-make-oven?view=all).
The original code of EZ Make Oven can be found [here](https://github.com/adafruit/Adafruit_Learning_System_Guides/tree/master/PyPortal_EZ_Make_Oven).


The purpose is to make a reflow soldering oven by modifying a kitchen oven with more affordable and widely available hardwares.

The GUI of this project is built with LittlevGL (lv_binding_micropython) which is a very powerful and easy to use GUI library.
LittlevGL already comes with drivers for ILI9341 TFT display and XPT2046 touch controller, this project takes the advantage
of both to ease the user operation. 

### Bill of Materials
* 1 x regular kitchen oven with 10-12L capacity.
* 1 x solid state relay rated 10A.
* 1 x passive piezo buzzer.
* 1 x ILI9341 TFT display with on-board XPT2046 touch controller.
* 1 x MAX31855 thermocouple amplifier with K-thermocouple.
* 1 x AC-DC5v power supply to power the ESP32 dev board.
* 1 x ESP32 dev board.

### Oven Modification and Wiring
* WARNING: The mains (220/110V) can be deadly.  Make sure the oven is unplugged from the wall plug before doing any modification
or wiring.
* Ovens are different one from another, but basically all you need to do is to bypass the original switch and timer, and
let the solid state relay control the heating element, hence the ESP32 board can turn the heating element
on and off via the solid state relay.

### The Firmware for ESP32
* Pls refer to [here](./FIRMWARE/readme.md).

### Installation
* All files are under ```MAIN``` folder.
* After flashing the firmware, you need to edit ```config.json``` to change the GPIO pin numbers according 
to how you wiring your TFT display and other components.
* Make sure ```"has_calibrated": ``` should be ```false```
* Transfer all the files and folder under ```MAIN``` to the ESP32 dev board and you are good to go.

### Usage Guide
* Upon powering on the first time, you will be guided through touch screen calibration and 
temperature calibration, throughout which the ESP32 board will reboot a couple of times.  Just
follow the guide.
* After calibration and reboot, the GUI will load, where you can select Solder Paste type from the
drop-down menu, just choose the type you'll use, and the reflow temperature profile will show down below.
* If your solder paste isn't there in the menu, you can build your own solder profile files.  Pls refer to: 
https://learn.adafruit.com/ez-make-oven?view=all#the-toaster-oven, under chapter "Solder Paste Profiles".
The new solder profile json file should be put under folder ```profiles```.
* All set and click "Start" button to start the reflow soldering procress.