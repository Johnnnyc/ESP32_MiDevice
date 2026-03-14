# ESP32_MiDevice 项目说明

## 项目简介

ESP32_MiDevice 是一个基于 ESP32 开发板的温湿度监控系统，具有以下功能：

- **温湿度数据采集**：使用 DHT11 传感器采集环境温湿度
- **MQTT 通信**：支持通过 MQTT 协议接收和发送消息
- **Firebase 数据存储**：将采集的数据存储到 Firebase 实时数据库
- **OTA 自动更新**：支持从 GitHub 仓库自动更新固件
- **风扇控制**：可通过 MQTT 指令控制风扇开关

## 硬件要求

- ESP32 开发板
- DHT11 温湿度传感器
- 风扇（可选）
- LED 指示灯

## 引脚配置

| 组件 | GPIO 引脚 | 说明 |
|------|----------|------|
| DHT11 数据 | GPIO4 | 温湿度传感器数据引脚 |
| 风扇控制 | GPIO5 | 风扇控制引脚 |
| LED 指示灯 | GPIO2 | 状态指示 |

## 软件配置

### 1. 配置文件

- **secret.py**：包含敏感配置信息
  - MQTT 用户名和密码
  - Firebase URL 和 API Key

- **config.py**：包含设备配置信息
  - 设备名称和型号
  - MQTT 服务器配置
  - 其他设备参数

- **firebase_config.py**：包含 Firebase 相关配置
  - 数据推送间隔

### 2. OTA 配置

- **boot.py**：设备启动时自动检查 OTA 更新
- **updata.py**：OTA 更新脚本，从 GitHub 下载最新代码

## 功能说明

### 1. 温湿度数据采集

- 每 3 分钟采集一次温湿度数据
- 数据包含温度、湿度和时间戳
- 数据推送到 Firebase 实时数据库

### 2. MQTT 通信

支持的 MQTT 指令：
- `获取温湿度`：触发传感器数据采集并发送
- `打开风扇`：控制风扇开启
- `关闭风扇`：控制风扇关闭
- `update`：触发 OTA 更新检查

### 3. Firebase 数据存储

- 数据存储在 `sensor-data` 节点下
- 使用时间戳作为数据 ID
- 保留历史数据，便于查看数据趋势

### 4. OTA 自动更新

- 设备启动时自动检查更新
- 从 GitHub 仓库获取最新代码
- 支持自动备份和更新

## 使用方法

1. **配置网络**：在 `boot.py` 中配置 WiFi 信息
2. **配置 Firebase**：在 `secret.py` 中填写 Firebase 配置
3. **上传代码**：将代码上传到 ESP32 设备
4. **观察日志**：通过串口监视器观察设备运行状态
5. **查看数据**：登录 Firebase 控制台查看采集的数据

## 项目结构

```
ESP32_MiDevice/
├── OTA_Files/           # OTA 相关文件
│   ├── OTA使用说明.md    # OTA 使用说明
│   ├── boot.py           # OTA 启动脚本
│   ├── main.py           # OTA 主程序示例
│   └── updata.py         # OTA 更新脚本
├── boot.py               # 主启动脚本
├── config.py             # 设备配置
├── firebase_config.py     # Firebase 配置
├── firebase_show_data.py  # Firebase 数据查看工具
├── main.py               # 主程序
├── updata.py             # OTA 更新脚本
└── secret.py             # 敏感配置（需自行创建）
```

## 注意事项

1. **安全性**：
   - `secret.py` 文件包含敏感信息，已添加到 `.gitignore`
   - 请勿将敏感信息上传到 GitHub

2. **网络连接**：
   - 确保 ESP32 设备能够连接到互联网
   - 确保 Firebase 项目的安全规则允许写入操作

3. **数据存储**：
   - 数据每 3 分钟推送一次
   - 数据存储在 `sensor-data/{timestamp}` 路径下

4. **OTA 更新**：
   - 确保 GitHub 仓库存在 `updata.py` 文件
   - `updata.py` 文件的第 10 个字符为 "1" 时触发更新

## 故障排查

1. **WiFi 连接失败**：
   - 检查 WiFi 名称和密码是否正确
   - 确保 WiFi 信号强度足够

2. **Firebase 推送失败**：
   - 检查 Firebase URL 和 API Key 是否正确
   - 确保设备能够访问 Firebase 服务器

3. **OTA 更新失败**：
   - 检查 GitHub 仓库地址是否正确
   - 确保设备能够访问 GitHub

4. **传感器读取失败**：
   - 检查 DHT11 传感器连接是否正确
   - 确保传感器工作正常

## 示例数据

Firebase 数据库中的数据格式：

```json
{
  "sensor-data": {
    "1773480000": {
      "temp": 25.5,
      "humid": 60,
      "time": "2026-03-14 12:00:00"
    },
    "1773480180": {
      "temp": 26.0,
      "humid": 58,
      "time": "2026-03-14 12:03:00"
    }
  }
}
```

## 许可证

本项目采用 MIT 许可证。
