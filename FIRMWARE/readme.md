## Micropython 1.12 + LVGL v6

* This project is NOT compatible with LVGL v7 due to the breaking changes in v7.

* The firmwares are built from lv_micropython with ESP-IDF v3.x
* The file ```firmware_idf3_generic_spiram.bin``` is for the ESP32 dev boards with external SPIRAM, 
while ```firmware_idf3_generic.bin``` is for the ones without SPIRAM.

### Flashing the firmware

* Pls refer to http://micropython.org/download#esp32

### Build firmware by yourself

* If you would like to build firmware on your own, pls refer to [here](https://github.com/littlevgl/lv_micropython)
and [here](https://github.com/littlevgl/lv_binding_micropython).

---
## 中文说明

* 本项目使用LVGL v6，由于v7更改了部分API，目前无法在v7上正常使用。

* 本固件基于lv_micropython及ESP-IDF v3.x

* ```firmware_idf3_generic_spiram.bin```用于板载SPIRAM的ESP32开发板；
```firmware_idf3_generic.bin```用于不带外部SPIRAM的ESP32开发板。

### 刷入固件
* 具体步骤参考http://micropython.org/download#esp32
 
### 自制固件
* 具体步骤参考[这里](https://github.com/littlevgl/lv_micropython)
以及 [这里](https://github.com/littlevgl/lv_binding_micropython)。
