# 开机自动联网 + OTA 更新
import network
import time
import urequests
import os
import machine

# WiFi 信息（改成你自己的）
WIFI_SSID = "你的WiFi名"
WIFI_PWD = "你的WiFi密码"

# 云端更新脚本
UPDATE_URL = "https://gitee.com/你的用户名/仓库/raw/master/updata.py"

def connect_wifi():
    """
    连接WiFi网络
    返回：连接成功返回True，失败返回False
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print("正在连接WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PWD)
        timeout = 0
        while not wlan.isconnected():
            time.sleep(0.5)
            timeout += 1
            if timeout > 40:
                print("WiFi 连接失败")
                return False
    print("WiFi 连接成功:", wlan.ifconfig())
    return True

def backup_file(file_path):
    """
    备份文件
    """
    try:
        if os.path.exists(file_path):
            timestamp = time.localtime()
            backup_name = f"backup_{timestamp[0]}{timestamp[1]:02d}{timestamp[2]:02d}{timestamp[3]:02d}{timestamp[4]:02d}{timestamp[5]:02d}_{os.path.basename(file_path)}"
            backup_path = os.path.join(os.path.dirname(file_path), backup_name)
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
                    timestamp_str = file.split('_')[1].split('.')[0]
                    if len(timestamp_str) == 14:
                        year = int(timestamp_str[:4])
                        month = int(timestamp_str[4:6])
                        day = int(timestamp_str[6:8])
                        hour = int(timestamp_str[8:10])
                        minute = int(timestamp_str[10:12])
                        second = int(timestamp_str[12:14])
                        file_time = time.mktime((year, month, day, hour, minute, second, 0, 0, 0))
                        # 如果超过3小时
                        if current_time - file_time > 3 * 60 * 60:
                            os.remove(file)
                            print(f"已删除旧备份: {file}")
                except:
                    pass
    except Exception as e:
        print(f"清理旧备份失败: {e}")

# 主逻辑
try:
    # 清理旧备份
    clean_old_backups()
    
    if connect_wifi():
        print("开始OTA检查...")
        resp = urequests.get(UPDATE_URL)
        data = resp.content
        
        # 判断是否更新（文章里的逻辑：第10个字符是1就更新）
        if len(data) > 9 and chr(data[9]) == "1":
            print("检测到新版本，开始更新...")
            # 备份现有文件
            backup_file("updata.py")
            backup_file("main.py")
            
            with open("updata.py", "wb") as f:
                f.write(data)
            
            # 运行更新脚本
            import updata
        else:
            print("无需更新")
except Exception as e:
    print("OTA 异常:", e)