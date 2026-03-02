import time
import dht
import machine
from machine import Pin, Timer
from config import *
from mi_device import MiDevice

# 初始化DHT11传感器
dht_sensor = dht.DHT11(Pin(DHT_PIN))

# 初始化开关引脚
switch_pins = [Pin(pin, Pin.OUT, value=0) for pin in SWITCH_PINS]

# 初始化米家设备
mi_device = MiDevice()

# 读取传感器数据
def read_sensor_data():
    try:
        dht_sensor.measure()
        temperature = dht_sensor.temperature()
        humidity = dht_sensor.humidity()
        print(f"DHT11读取成功: 温度={temperature:.1f}°C, 湿度={humidity:.1f}%")
        return temperature, humidity
    except OSError as e:
        print(f"DHT11传感器读取失败: {e}")
        return None, None

# 更新GPIO开关状态
def update_gpio_states(switch_states):
    for i, state in enumerate(switch_states):
        switch_pins[i].value(1 if state else 0)

# 传感器数据更新计时器回调
def sensor_update_timer(timer):
    global mi_device
    temperature, humidity = read_sensor_data()
    if temperature is not None and humidity is not None:
        mi_device.temperature = temperature
        mi_device.humidity = humidity
        # 模拟电量消耗
        mi_device.battery = max(0, mi_device.battery - 0.1)
        # 更新GPIO状态
        update_gpio_states(mi_device.switch_states)
        # 更新设备数据
        mi_device.update_device_data()

# 主程序设置
def setup():
    print("========================================")
    print("ESP32 米家传感器开关设备 (MicroPython)")
    print("可被青萍盲网关发现并通过米家系统控制")
    print("支持DHT11温湿度传感器和多个IO开关")
    print("========================================")
    
    # 启动BLE广播
    mi_device.start_advertising()
    
    # 初始化传感器更新计时器
    timer = Timer(0)
    timer.init(period=STATUS_REPORT_INTERVAL, mode=Timer.PERIODIC, callback=sensor_update_timer)
    
    print("初始化完成，系统已启动")

# 主循环
def main():
    setup()
    while True:
        # 处理其他任务
        time.sleep(0.1)

# 启动程序
if __name__ == "__main__":
    main()