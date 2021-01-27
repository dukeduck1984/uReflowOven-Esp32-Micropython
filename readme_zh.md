## 迷你回流焊炉 (μReflow Oven with MicroPython & LittlevGL)

See [here](./readme.md) for English version.

更新了！现在迷你回流焊炉使用PID来进行温度控制

*重要提示：如果你想从非PID温控的老版本升级至最新版，请确保下载了最新版的`config.json`，并仔细确认其中的设置与你的实际硬件设置相符。
最为重要的是，确保包括加热器在内的所有接线均正确。*

![](./pic/pid.jpg)

老版本（非PID温控）存放于branch ```Adafruit-EZ-Make-Oven-alike```。

本项目是在[Adafruit EZ Make Oven](https://learn.adafruit.com/ez-make-oven?view=all)的基础上改良和重度重写而来，
EZ Make Oven的源代码[在此](https://github.com/adafruit/Adafruit_Learning_System_Guides/tree/master/PyPortal_EZ_Make_Oven)。

![](./pic/overview.jpg)

本项目的目的是利用一些常见且廉价的硬件对一个普通的家用小烤箱进行改装，最终得到一个实用的回流焊炉，从而方便DIY电子制作。
除了烤箱之外，也可以使用电炉。

![](./pic/internal.jpg)

本项目的用户界面通过LittlevGL ([lv_binding_micropython][lv]) 制作，这是一个功能强大又简单易用的图形界面库。
LittlevGL自带了ILI9341 TFT屏幕和XPT2046触控驱动，本项目正是利用了带触控的ILI9341屏来方便用户的使用。

![](./pic/screen.jpg)

### 物料清单
* 1 x 容积10-12升的家用小烤箱，例如[这个][oven]。或者电热炉，例如[这个][plate]
* 1 x 10安倍的固态继电器，例如[这个][ssr]；电热炉可能已经自带了继电器，请自行确认。
* 1 x 无源压电蜂鸣器，例如[这个][buzzer]；
* 1 x 带XPT2046触控芯片的ILI9341 TFT显示屏，例如[这个][tft]；
* 1 x K型热电偶控制板，以及K型热电偶，例如[MAX31855][max31855]，或者[MAX6675][max6675]；
* 1 x 交流转直流5v的电源，用来给ESP32供电， 例如[这个][acdc]；
* 1 x ESP32开发板，例如[这个][esp32]。

### 烤箱改装及接线
* 警告: 220V市电若操作不当可能会造成人身伤害，甚至可能致命，确保在改装前把烤箱插头拔掉，切勿带电操作。
* 不同型号的烤箱，其内部结构可能不同，但总体原理大同小异：你需要绕开原烤箱的温控及定时器，让固态继电器来
控制加热管，这样ESP32就可以通过通断固态继电器来控制烤箱的加热。

### 给ESP32刷入固件
* 请参考[这篇](./FIRMWARE/readme.md)。
* __注意：此版本只适用于LVGL v6，由于LVGL v7更改了部分API，目前无法兼容v7。__

### 配置文件
* 通过编辑 `config.json` 文件来进行配置。
* 硬件接线: 修改以`_pins`结尾的键值，使其与你实际的接线相符。
* TFT屏幕与触摸控制器共享 `Clock`， `Data In` 及 `Data Out` 接口，并联即可。
* 配置文件中的ACC pin是用来给TFT屏幕供电的。此为可选项。如果你的显示屏有电源出发控制接口（通常标识为ACC），你可以用相应的GPIO
进行连接。你也可以用三极管来控制屏幕的供电。个别型号的TFT屏幕也可以直接由ESP32的GPIO口供电，但需要注意的是ESP32 GPIO最大电流
为50mA，通常2.8寸屏所需电流为80-250mA，因此直接供电（从ESP32的3.3V引脚直接连到屏幕的电源引脚）可能会损毁ESP32，请知晓该风险。
* `active_low`选项用于低电平触发的用电器。
* `sampling_hz` 决定了温度传感器和PID算法的刷新率，及每秒刷新几次。默认值为`5`，即5Hz每秒5次。
* `temp_offset` 和 `pid` 的参数可以在图形界面中进行设置修改。
* `advanced_temp_tuning` 只能通过编辑 `config.json` 进行修改。
    * `preheat_until` (摄氏度) 用于设置一个温度，在炉子达到该温度前，炉子的加热会一直开启，并忽略PID温控。这有助于在
    刚开始时炉子快速升温。
    * `provisioning`  (秒) 用于PID算法预知将要到达的温度：由于回流焊的温度不是恒温，而是一个动态变化的温度曲线，设置这么
    一个参数有助于提高PID反应。
    * `overshoot_comp` (摄氏度) 用于降低温度过冲。

### FTP连接
* 上述`advanced_temp_tuning`选项找到合理的设置参数需要进行多次尝试，为了方便这个调试过程，ESP32会生成一个名为
`Reflower ftp://192.168.4.1`的WiFi热点。
* 接入上述WiFi热点，并使用任意FTP客户端，如`FileZiila`，登录至`ftp://192.168.4.1:21`便可对`config.json`进行修改。

### 安装程序
* 所需的文件均在 `MAIN` 目录下。
* 在刷完固件后，你需要先对`config.json`进行编辑，确保各个GPIO端口号与你实际接线相符。
* 根据实际使用的K型热电偶模块类型，设置`sensor_type`为`MAX31855`或`MAX6675`。
* 有些型号的固态继电器不能被ESP32 GPIO引脚的电压所触发，这种情况你可能需要通过一个三极管和另一个电源来进行触发。请根据实际情况
设置`active_low`选项。
* 再次检查确认接线和设置均正确无误。
* 将`MAIN`目录下所有文件及文件夹上传至ESP32开发板中。

### 使用说明
* 首次通电，程序会引导你进行屏幕校准，按照屏幕提示操作即可，结束后ESP32开发板
会重启。
* 在校准并重启后，用户界面会加载，通过下拉菜单，你可以选择不同的焊锡膏，确保你选择的焊锡膏类型与你实际
使用的型号相符。在选择焊锡膏后，屏幕下方会显示该焊锡膏的工作温度及整个回流焊的温度变化曲线。
* 如果你要使用的焊锡膏类型不在下拉菜单里，你也可以创建自己的焊锡膏类型文件，具体请参考：
https://learn.adafruit.com/ez-make-oven?view=all#the-toaster-oven，步骤在"Solder Paste Profiles"章节下。
新创建的焊锡膏文件需上传至ESP32中的`profiles`目录内。
* 全部准备就绪后，点击"Start"按钮就可以开始回流焊流程。
* 如果你想要再次校准屏幕，可以点击屏幕上的"Settings"按钮，然后在弹窗中选择屏幕校准选项。

### 关于PID参数设置的提示
* 首先在`config.json`中将`previsioning`和`overshoot_comp`均设置为`0`，以避免奇怪的温控行为。
* 将参数`kp`设置为一个很小的数值，比如`0.1`，将参数`kd`设置为一个很大的数值，比如`300`，这样有助于在加热初期最小化
温度过冲现象（多见于‘preheat’和‘soak’阶段）。通过实际加热测试，不停调低`kp`调高`kd`的数值，直到温度过冲现象基本消失。
* 由于`kp`很小而`kd`很大，在‘reflow’阶段温度可能很难达到理想的最高温度，这时就需要开始调试`ki`参数。缓慢增大`ki`的数值，
直到实际最高温度可以达到或非常接近理想的最高温度。
* 请知晓：PID算法的积分部分（`ki`参数作用的部分）只在‘reflow’阶段才会起效，这是硬编码在程序里的，无法通过设置更改。
这样做的目的是为了尽可能在加热早期阶段避免温度过冲，但仍旧可以在‘reflow’阶段达到理想的最高温度。

[lv]:https://github.com/littlevgl/lv_binding_micropython
[oven]:https://www.aliexpress.com/item/4000151934943.html
[plate]:https://www.aliexpress.com/item/32946772052.html
[ssr]:https://www.aliexpress.com/item/4000083560440.html
[buzzer]:https://www.aliexpress.com/item/32808743801.html
[tft]:https://www.aliexpress.com/item/32960934541.html
[max31855]:https://www.aliexpress.com/item/32878757344.html
[max6675]:https://www.aliexpress.com/item/4000465204314.html
[acdc]:https://www.aliexpress.com/item/32821770958.html
[esp32]:https://www.aliexpress.com/item/32855652152.html