# ESP32 米家设备 MicroPython 上传和测试说明

## 一、准备工作

### 1. 安装MicroPython固件到ESP32

1. **下载固件**
   - 访问 [MicroPython官方下载页面](https://micropython.org/download/esp32/)
   - 下载最新的ESP32固件（推荐使用支持BLE的版本）
   - 保存为 `esp32-firmware.bin`

2. **安装esptool工具**
   ```bash
   pip install esptool
   ```

3. **擦除ESP32闪存**
   ```bash
   esptool.py --chip esp32 --port COMx erase_flash
   ```
   （将COMx替换为ESP32连接的实际串口）

4. **烧录MicroPython固件**
   ```bash
   esptool.py --chip esp32 --port COMx --baud 460800 write_flash -z 0x1000 esp32-firmware.bin
   ```

### 2. 安装文件传输工具

选择以下任一工具上传文件：

#### 选项A：使用Thonny IDE（推荐初学者）
- 下载并安装 [Thonny IDE](https://thonny.org/)
- 打开Thonny，点击底部状态栏选择解释器
- 选择"MicroPython (ESP32)"和正确的串口

#### 选项B：使用ampy工具
```bash
pip install adafruit-ampy
```

## 二、上传代码文件

### 使用Thonny IDE上传
1. 在Thonny中打开`config.py`文件
2. 点击"File" -> "Save to MicroPython Device"
3. 重复此操作上传`mi_device.py`和`main.py`

### 使用ampy上传
```bash
ampy --port COMx put config.py
ampy --port COMx put mi_device.py
ampy --port COMx put main.py
```

## 三、测试设备

### 1. 基本功能测试

1. **重启ESP32**
   - 可以通过物理按键重启或使用以下命令
   ```bash
   ampy --port COMx reset
   ```

2. **查看串口输出**
   - 使用Thonny的串口监视器
   - 或使用其他串口工具（波特率115200）

3. **检查初始化**
   确认看到以下输出：
   ```
   ========================================
   ESP32 米家传感器开关设备 (MicroPython)
   可被青萍盲网关发现并通过米家系统控制
   支持DHT11温湿度传感器和多个IO开关
   ========================================
   BLE广播已启动
   设备名称: ESP32_MiDevice
   设备型号: esp32.sensor_switch.v1
   设备ID: [设备MAC地址]
   MAC地址: [设备MAC地址]
   初始化完成，系统已启动
   ```

4. **检查传感器读数**
   每5秒应该看到一次传感器读数更新：
   ```
   DHT11读取成功: 温度=XX.X°C, 湿度=XX.X%
   ```

### 2. 米家设备测试

1. **添加设备到米家APP**
   - 打开米家APP
   - 点击"+"添加设备
   - 搜索附近的设备，应该能找到"ESP32_MiDevice"
   - 按照提示完成添加

2. **测试开关控制**
   - 在米家APP中点击开关控制按钮
   - 观察ESP32上对应的GPIO输出状态变化
   - 检查串口输出中的开关状态更新

3. **查看传感器数据**
   - 在设备详情页面查看温度和湿度数据
   - 确认数据与ESP32读取的一致

## 四、常见问题排查

### 1. BLE连接问题
- 确认ESP32的BLE功能正常启用
- 检查固件是否支持BLE功能
- 尝试重启ESP32和米家APP

### 2. 传感器读取失败
- 检查DHT11传感器接线是否正确
- 确认DHT_PIN配置与实际接线一致
- 传感器可能需要1-2秒预热时间

### 3. 开关控制无反应
- 检查GPIO引脚配置是否正确
- 确认开关引脚已正确设置为输出模式
- 检查外接电路连接是否正确

## 五、注意事项

1. **电源要求**
   - 确保ESP32有足够稳定的电源供应
   - BLE功能需要足够的电流供应

2. **程序调试**
   - 可以在代码中添加更多的打印语句进行调试
   - 使用try/except捕获可能的异常

3. **OTA更新**
   - 当前版本不支持OTA更新，需要通过物理连接更新代码
   - 后续可以考虑添加OTA功能

4. **内存管理**
   - MicroPython内存有限，避免创建过大的数据结构
   - 长时间运行可能需要添加内存回收代码

## 六、扩展功能建议

1. 添加更多类型的传感器支持
2. 实现更复杂的米家协议功能
3. 添加数据记录和历史查询功能
4. 实现OTA远程更新功能

---

上传前请确保ESP32开发板已正确连接并在上传模式！