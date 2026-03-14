# update=1
# 上面这行控制是否要升级
ver = 2.0

from machine import Pin, I2C, Timer
import ssd1306
import time
import onewire, ds18x20

def init_oled():
    """
    初始化OLED显示屏
    """
    try:
        i2c = I2C(scl=Pin(14), sda=Pin(12))
        oled = ssd1306.SSD1306_I2C(128, 64, i2c)
        return oled
    except Exception as e:
        print(f"OLED初始化失败: {e}")
        return None

def init_ds18b20():
    """
    初始化DS18B20温度传感器
    """
    try:
        ow = onewire.OneWire(Pin(13))
        ds = ds18x20.DS18X20(ow)
        return ds
    except Exception as e:
        print(f"DS18B20初始化失败: {e}")
        return None

def read_temp(ds):
    """
    读取温度
    """
    try:
        roms = ds.scan()
        if roms:
            ds.convert_temp()
            time.sleep_ms(750)
            return ds.read_temp(roms[0])
        return 0
    except Exception as e:
        print(f"读取温度失败: {e}")
        return 0

def main_loop():
    """
    主循环
    """
    # 初始化硬件
    oled = init_oled()
    ds = init_ds18b20()
    relay = Pin(22, Pin.OUT, value=1)
    
    target = 38.0
    
    while True:
        # 读取温度
        temp = read_temp(ds)
        
        # 显示信息
        if oled:
            oled.fill(0)
            oled.text(f"Temp: {temp:.1f} C", 0, 0)
            oled.text(f"Target: {target:.1f} C", 0, 16)
            oled.text(f"Ver: {ver}", 0, 32)
            oled.show()
        
        # 温控逻辑
        if temp >= target:
            relay.value(1)  # 关闭加热
        else:
            relay.value(0)  # 开启加热
        
        time.sleep(2)

if __name__ == "__main__":
    main_loop()