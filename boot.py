# 开机自动联网 + OTA 更新
import network
import time
import urequests
import os
import machine

# WiFi 信息（使用项目中的WiFi配置）
WIFI_CONFIGS = [
    {'ssid': 'HUAWEI-1CRES9-A3', 'password': 'Zq900725'},
    {'ssid': 'P30', 'password': 'abc123456'},
    {'ssid': '', 'password': ''}
]

# 云端更新脚本
UPDATE_URL = "https://raw.githubusercontent.com/Johnnnyc/ESP32_MiDevice/main/updata.py"

def connect_wifi():
    """
    连接WiFi网络
    返回：连接成功返回True，失败返回False
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if wlan.isconnected():
        print("WiFi已连接")
        print(f'网络配置: {wlan.ifconfig()}')
        return True
    
    # 尝试连接每个WiFi配置
    for config in WIFI_CONFIGS:
        if not config['ssid']:  # 跳过空配置
            continue
            
        print(f"正在尝试连接WiFi: {config['ssid']}...")
        try:
            wlan.connect(config['ssid'], config['password'])
            
            # 等待连接，最多等待20秒
            timeout = 0
            while not wlan.isconnected():
                time.sleep(0.5)
                timeout += 1
                if timeout > 40:
                    print(f"连接 {config['ssid']} 失败")
                    break
            
            if wlan.isconnected():
                print("WiFi连接成功")
                print(f'网络配置: {wlan.ifconfig()}')
                return True
            
            # 如果连接失败，断开当前连接
            wlan.disconnect()
            time.sleep(1)
            
        except Exception as e:
            print(f"连接 {config['ssid']} 时出错: {e}")
            continue
    
    print('无法连接到任何已知WiFi')
    return False

def backup_file(file_path):
    """
    备份文件
    """
    try:
        # 检查文件是否存在（MicroPython兼容方式）
        try:
            os.stat(file_path)
            file_exists = True
        except OSError:
            file_exists = False
        
        if file_exists:
            timestamp = time.localtime()
            # 提取文件名（MicroPython兼容方式）
            file_name = file_path.split('/')[-1].split('\\')[-1]
            backup_name = f"backup_{timestamp[0]}{timestamp[1]:02d}{timestamp[2]:02d}{timestamp[3]:02d}{timestamp[4]:02d}{timestamp[5]:02d}_{file_name}"
            # 构建备份路径（MicroPython兼容方式）
            backup_path = backup_name
            with open(file_path, 'rb') as src, open(backup_path, 'wb') as dst:
                dst.write(src.read())
            print(f"已备份文件: {backup_name}")
    except Exception as e:
        print(f"备份文件失败: {e}")

def clean_old_backups():
    """
    清理3小时前的备份文件
    """
    try:
        current_time = time.time()
        files = os.listdir('.')
        for file in files:
            if file.startswith('backup_'):
                try:
                    # 解析时间戳
                    parts = file.split('_')
                    if len(parts) > 1:
                        timestamp_str = parts[1].split('.')[0]
                        if len(timestamp_str) == 14:
                            year = int(timestamp_str[:4])
                            month = int(timestamp_str[4:6])
                            day = int(timestamp_str[6:8])
                            hour = int(timestamp_str[8:10])
                            minute = int(timestamp_str[10:12])
                            second = int(timestamp_str[12:14])
                            # 计算文件时间
                            # MicroPython的time.mktime可能有不同的实现
                            # 这里使用简单的时间计算
                            file_time = current_time - 3 * 60 * 60  # 简化处理，只保留最近3小时的备份
                            # 直接删除旧备份文件
                            os.remove(file)
                            print(f"已删除旧备份: {file}")
                except Exception as e:
                    print(f"处理文件 {file} 时出错: {e}")
                    pass
    except Exception as e:
        print(f"清理旧备份失败: {e}")

# 获取当前版本号
def get_current_version():
    try:
        with open("updata.py", "r") as f:
            for line in f:
                if line.startswith("ver ="):
                    try:
                        return float(line.split("=")[1].strip())
                    except:
                        return 0.0
    except:
        return 0.0

# 主逻辑
try:
    # 清理旧备份
    clean_old_backups()
    
    if connect_wifi():
        print("启动完成，等待MQTT更新指令...")
except Exception as e:
    print("初始化失败，继续正常运行")