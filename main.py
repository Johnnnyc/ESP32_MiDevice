from machine import Pin
import network
from umqtt.simple import MQTTClient
import json
from dht import DHT11  # 添加DHT11库
import random
import time
import ssl
import ntptime
import machine
import urequests
from config import *
from firebase_config import *

# 配置参数 - 直接在代码中定义
WIFI_TIMEOUT = 15  # WiFi连接超时时间（秒）
MQTT_KEEPALIVE = 90  # MQTT保活时间
MQTT_MAX_RETRIES = 3  # MQTT最大重试次数
MAX_ERRORS = 5  # 主循环最大错误次数
ERROR_SLEEP_TIME = 5  # 错误后等待时间（秒）
WIFI_RETRY_TIME = 30  # WiFi重连等待时间（秒）
LED_BLINK_INTERVAL = 0.5  # LED闪烁间隔（秒）
AUTO_REINIT_INTERVAL = 3600  # 自动重新初始化间隔（秒）= 1小时

 # 风扇控制引脚配置，假设连接在GPIO5
fan_pin = Pin(5, Pin.OUT)

# WiFi配置
WIFI_CONFIGS = [
    {'ssid': 'HUAWEI-1CRES9-A3', 'password': 'Zq900725'},
    {'ssid': 'P30', 'password': 'abc123456'}, 
    {'ssid': '', 'password': ''}
]

# 初始化LED引脚，假设LED连接在GPIO2上
led = Pin(2, Pin.OUT)

# DHT11配置
DHT_PIN = 4  # 使用GPIO4作为DHT11的数据引脚
dht = DHT11(Pin(DHT_PIN))

# 定义全局变量client
client = None  # 初始化为None，后续可根据实际需求赋值
last_ntp_sync = 0  # 上次NTP同步时间戳
last_reinit_time = 0  # 上次重新初始化时间戳
last_ota_check = 0  # 上次OTA检查时间戳
last_firebase_push = 0  # 上次Firebase推送时间戳

# 版本比较函数
def compare_versions(version1, version2):
    """比较两个版本号，返回1如果version1>version2，0如果相等，-1如果version1<version2"""
    v1_parts = list(map(int, version1.split('.')))
    v2_parts = list(map(int, version2.split('.')))
    
    for i in range(max(len(v1_parts), len(v2_parts))):
        v1 = v1_parts[i] if i < len(v1_parts) else 0
        v2 = v2_parts[i] if i < len(v2_parts) else 0
        
        if v1 > v2:
            return 1
        elif v1 < v2:
            return -1
    return 0

# 获取GitHub最新版本
def get_latest_version():
    """从GitHub获取最新版本信息"""
    try:
        # 最小化HTTP请求，减少内存使用
        headers = {"User-Agent": "ESP32-MiDevice"}
        # 使用更短的超时
        response = urequests.get(GITHUB_API_URL, headers=headers, timeout=3)
        
        if response.status_code == 200:
            # 简化JSON解析，减少内存使用
            response_text = response.text
            response.close()
            
            # 手动解析tag_name，避免完整JSON解析
            tag_start = response_text.find('"tag_name":"')
            if tag_start != -1:
                tag_start += 10
                tag_end = response_text.find('"', tag_start)
                if tag_end > tag_start:
                    latest_version = response_text[tag_start:tag_end]
                    # 移除可能的"v"前缀
                    if latest_version.startswith("v"):
                        latest_version = latest_version[1:]
                    return latest_version
        elif response.status_code == 404:
            # 404错误表示仓库没有发布版本，这是正常情况
            response.close()
            return FIRMWARE_VERSION
        
        response.close()
        return None
    except Exception as e:
        # 减少日志输出，节省内存
        return None

# 检查版本更新
def check_for_updates():
    """检查是否有版本更新"""
    if not ENABLE_GITHUB_CHECK:
        return None
    
    current_version = FIRMWARE_VERSION
    latest_version = get_latest_version()
    
    if latest_version and latest_version != current_version:
        comparison = compare_versions(latest_version, current_version)
        if comparison > 0:
            return latest_version
    
    return None

# 下载固件
def download_firmware(version):
    """下载最新固件"""
    try:
        log("INFO", f"正在下载版本 {version} 的固件...")
        # 构建固件下载URL
        firmware_url = f"https://github.com/{GITHUB_REPO}/releases/download/v{version}/firmware.bin"
        
        # 添加User-Agent头
        headers = {
            "User-Agent": "ESP32-MiDevice"
        }
        
        # 下载固件，设置超时为30秒
        response = urequests.get(firmware_url, headers=headers, timeout=30)
        if response.status_code == 200:
            # 保存固件到本地
            with open(FIRMWARE_PATH, 'wb') as f:
                f.write(response.content)
            log("INFO", f"固件下载成功，大小: {len(response.content)} 字节")
            response.close()
            return True
        else:
            log("ERROR", f"固件下载失败: {response.status_code}")
            response_text = response.text
            log("ERROR", f"下载响应: {response_text}")
            response.close()
            return False
    except Exception as e:
        log("ERROR", f"固件下载异常: {e}")
        return False

# 执行OTA更新
def perform_ota_update():
    """执行OTA更新"""
    if not ENABLE_GITHUB_CHECK:
        log("INFO", "GitHub版本检查已禁用，跳过OTA更新")
        return
    
    latest_version = check_for_updates()
    if latest_version:
        if download_firmware(latest_version):
            log("INFO", "准备重启设备进行更新...")
            # 重启设备
            machine.reset()
        else:
            log("ERROR", "固件下载失败，无法更新")
    else:
        log("INFO", "没有可用的更新")

# 推送数据到Firebase
def push_data_to_firebase(data):
    """推送数据到Firebase"""
    try:
        # 进一步简化，减少内存使用
        import gc
        gc.collect()  # 推送前进行内存回收
        
        # 简化数据结构，只推送必要字段
        simple_data = {
            'temp': data.get('temperature'),
            'humid': data.get('humidity'),
            'time': data.get('datetime')
        }
        
        # 使用更简单的URL构建
        url = FIREBASE_URL + "/data.json"
        headers = {"Content-Type": "application/json"}
        
        # 使用更轻量的请求方式
        response = urequests.put(url, json=simple_data, headers=headers, timeout=5)
        response.close()
        
        gc.collect()  # 推送后进行内存回收
        return True
    except Exception:
        # 静默失败，减少内存使用
        return False

def log(level, message):
    """简单的日志函数"""
    timestamp = time.localtime()
    time_str = "{:02d}:{:02d}:{:02d}".format(
        timestamp[3], timestamp[4], timestamp[5]
    )
    print(f"[{time_str}] [{level}] {message}")

def connect_wifi():
    """连接到WiFi网络，自动尝试多个配置"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    # 如果已经连接，直接返回
    if wlan.isconnected():
        log("INFO", 'WiFi已连接')
        log("INFO", f'网络配置: {wlan.ifconfig()}')
        return True
    
    # 尝试连接每个WiFi配置
    for config in WIFI_CONFIGS:
        if not config['ssid']:  # 跳过空配置
            continue
            
        log("INFO", f"正在尝试连接WiFi: {config['ssid']}...")
        try:
            wlan.connect(config['ssid'], config['password'])
            
            # 等待连接，最多等待15秒
            for attempt in range(WIFI_TIMEOUT):
                if wlan.isconnected():
                    log("INFO", 'WiFi连接成功')
                    log("INFO", f'网络配置: {wlan.ifconfig()}')
                    return True
                time.sleep(1)
                
            # 如果连接失败，断开当前连接
            wlan.disconnect()
            time.sleep(1)
            
        except Exception as e:
            log("ERROR", f"连接 {config['ssid']} 时出错: {e}")
            continue
    
    log("ERROR", '无法连接到任何已知WiFi')
    return False

# MQTT配置
SERVER = "z6fc98e1.ala.cn-hangzhou.emqxsl.cn"
PORT = 8883
CLIENT_ID = 'micropython-client-{id}'.format(id=random.getrandbits(8))
USERNAME = 'Johnney'
PASSWORD = 'Zq??900725'
TOPIC = "esp32/topic"
CA_CERTS_PATH = "./ca.crt"  # use the public broker CA

def create_ssl_context():
    # Create an SSL context
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.load_verify_locations(CA_CERTS_PATH)
    return ssl_context


def connect():
    global client
    retry_count = 0
    
    while retry_count < MQTT_MAX_RETRIES:
        try:
            # 如果已有客户端连接，先断开并释放资源
            if client:
                try:
                    client.disconnect()
                except Exception as e:
                    log("WARNING", f"断开连接时发生错误: {e}")
                client = None

            # 创建SSL上下文
            try:
                ssl_context = create_ssl_context()
            except Exception as e:
                log("ERROR", f"创建SSL上下文失败: {e}")
                retry_count += 1
                time.sleep(5)
                continue

            # 创建MQTT客户端并连接
            client = MQTTClient(CLIENT_ID, SERVER, PORT, USERNAME, PASSWORD, ssl=ssl_context, keepalive=MQTT_KEEPALIVE)
            client.connect()
            log("INFO", f'Connected to MQTT Broker "{SERVER}"')
            return client

        except Exception as e:
            retry_count += 1
            log("ERROR", f'MQTT连接失败 (尝试 {retry_count}/{MQTT_MAX_RETRIES}): {e}')
            if retry_count < MQTT_MAX_RETRIES:
                log("INFO", '5秒后尝试重新连接...')
                time.sleep(5)
            else:
                log("ERROR", f'MQTT连接失败，已达到最大重试次数 {MQTT_MAX_RETRIES}')
                raise e


def read_sensor():
    """读取传感器数据"""
    # 初始化变量
    temperature = None
    humidity = None
    time_str = ""
    
    # 读取温湿度数据
    try:
        dht.measure()  # 测量温湿度
        temperature = dht.temperature()  # 获取温度
        humidity = dht.humidity()  # 获取湿度
    except Exception as e:
        log("ERROR", f'读取温湿度失败: {e}')

    # 获取网络时间并格式化为字符串
    global last_ntp_sync
    try:
        current_epoch = time.time()
        # 每小时同步一次NTP时间
        if last_ntp_sync == 0 or current_epoch - last_ntp_sync > 3600:
            # 减少NTP同步频率，节省内存和网络资源
            try:
                ntptime.settime()  # 同步网络时间
                last_ntp_sync = current_epoch
                log("INFO", "NTP时间同步成功")
            except Exception as e:
                log("ERROR", f'NTP同步失败: {e}')
        
        # 格式化时间 - 直接使用系统时间，ntptime.settime()会自动处理时区
        current_time = time.localtime()
        # 简化时间格式化，减少内存使用
        year, month, day, hour, minute, second = current_time[0], current_time[1], current_time[2], current_time[3], current_time[4], current_time[5]
        # 直接格式化字符串，减少中间变量
        time_str = f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
    except Exception as e:
        log("ERROR", f'获取网络时间失败: {e}')
        # 获取当前时间并格式化为字符串
        current_time = time.localtime()
        year, month, day, hour, minute, second = current_time[0], current_time[1], current_time[2], current_time[3], current_time[4], current_time[5]
        time_str = f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
    
    # 构建数据字典
    data = {
        'temperature': temperature,
        'humidity': humidity,
        'datetime': time_str
    }
    
    # 尝试进行内存回收
    try:
        import gc
        gc.collect()
    except:
        pass
    
    return data


        
def on_message(topic, msg):
    global client
    """收到MQTT消息时的回调函数"""
    try:
        log("INFO", "\n收到新消息:")
        log("INFO", f"主题: {topic.decode()}")
        log("INFO", f"内容: {msg.decode()}")
        
        # 检查是否是更新指令
        if topic.decode() == MQTT_UPDATE_TOPIC and msg.decode() == "update":
            log("INFO", "收到更新指令，开始检查更新...")
            perform_ota_update()
        elif msg.decode() == "获取温湿度":
            led.value(1)  # 点亮LED
            read_sent(client)  # 读取传感器数据并发送
            led.value(0)  # 熄灭LED
        elif msg.decode() == "打开风扇":
            fan_pin.value(1)  # 打开风扇
            response = {"Opened"}
            client.publish(TOPIC, json.dumps(response))
            log("INFO", "已打开风扇")
        elif msg.decode() == "关闭风扇":
            fan_pin.value(0)  # 关闭风扇
            response = {"Closed"}
            client.publish(TOPIC, json.dumps(response))
            log("INFO", "已关闭风扇")
        log("INFO", "-" * 40)
    except Exception as e:
        log("ERROR", f"处理消息时出错: {e}")


def subscribe(client): 
    """订阅主题并设置回调"""
    client.set_callback(on_message)
    client.subscribe(TOPIC)
    client.subscribe(MQTT_UPDATE_TOPIC)
    log("INFO", f"已成功订阅主题: {TOPIC}")
    log("INFO", f"已成功订阅更新主题: {MQTT_UPDATE_TOPIC}")

def read_sent(client):
    max_retries = 3
    retry_count = 0
    data_sent = False
    
    while retry_count < max_retries and not data_sent:
        try:
            # 读取传感器数据
            data = read_sensor()
            
            # 将数据转换为JSON字符串
            message = json.dumps(data)
            
            # 发送数据到MQTT
            client.publish(TOPIC, message)
            log("INFO", f'数据已发送: {message}')
            data_sent = True
            
        except Exception as e:
            retry_count += 1
            log("ERROR", f'获取数据失败(尝试 {retry_count}/{max_retries}): {e}')
            if retry_count < max_retries:
                time.sleep(1)
            else:
                # 3次尝试都失败后发送异常报告
                error_data = {
                    "error": "获取数据失败",
                    "retries": max_retries,
                    "last_error": str(e)
                }
                client.publish(TOPIC, json.dumps(error_data))
                log("ERROR", f'发送异常报告: {error_data}')

def reinitialize():
    """重新初始化系统"""
    global client, last_reinit_time
    log("INFO", "开始重新初始化系统...")
    
    # 断开MQTT连接
    if client:
        try:
            client.disconnect()
            log("INFO", "MQTT连接已断开")
        except:
            pass
        client = None
    
    # 重置WiFi连接
    wlan = network.WLAN(network.STA_IF)
    wlan.disconnect()
    time.sleep(2)
    wlan.active(False)
    time.sleep(2)
    wlan.active(True)
    
    # 更新重新初始化时间
    last_reinit_time = time.time()
    log("INFO", "系统重新初始化完成")

def main():
    global client, last_reinit_time
    
    log("INFO", "启动ESP32温湿度监控系统")
    
    # 连接WiFi
    if not connect_wifi():
        log("ERROR", "WiFi连接失败，系统无法启动")
        # WiFi连接失败时，LED快速闪烁
        for _ in range(10):
            led.value(1)
            time.sleep(0.1)
            led.value(0)
            time.sleep(0.1)
        return
    
    # 连接MQTT
    try:
        client = connect()
        subscribe(client)
        log("INFO", "MQTT连接和订阅成功")
        # MQTT连接成功时，LED短暂点亮
        led.value(1)
        time.sleep(1)
        led.value(0)
    except Exception as e:
        log("ERROR", f"MQTT连接失败: {e}")
        # MQTT连接失败时，LED慢速闪烁
        for _ in range(5):
            led.value(1)
            time.sleep(1)
            led.value(0)
            time.sleep(1)
        return
    
    error_count = 0  # 错误计数器
    last_reinit_time = time.time()  # 初始化重新初始化时间
    last_ota_check = time.time()  # 初始化OTA检查时间
    last_firebase_push = time.time()  # 初始化Firebase推送时间
    
    # 系统启动时检查版本更新
    log("INFO", "系统启动，检查版本更新...")
    check_for_updates()
    
    log("INFO", "进入主循环")
    
    while True:
        try:
            # 检查WiFi连接状态
            wlan = network.WLAN(network.STA_IF)
            if not wlan.isconnected():
                log("WARNING", "WiFi连接断开，尝试重新连接...")
                # WiFi断开时，LED快速闪烁
                for _ in range(3):
                    led.value(1)
                    time.sleep(0.2)
                    led.value(0)
                    time.sleep(0.2)
                    
                if not connect_wifi():
                    log("ERROR", "WiFi重连失败，等待30秒后重试...")
                    # WiFi重连失败时，LED持续快速闪烁
                    start_time = time.time()
                    while time.time() - start_time < WIFI_RETRY_TIME:
                        led.value(1)
                        time.sleep(0.1)
                        led.value(0)
                        time.sleep(0.1)
                    continue
                else:
                    # WiFi重连成功，LED短暂点亮
                    led.value(1)
                    time.sleep(0.5)
                    led.value(0)
            
            # 检查MQTT连接状态
            mqtt_connected = False
            try:
                # 尝试发送ping包检查连接状态
                client.ping()
                mqtt_connected = True
            except:
                mqtt_connected = False
            
            if not mqtt_connected:
                log("WARNING", "MQTT连接断开，尝试重新连接...")
                # MQTT断开时，LED慢速闪烁
                for _ in range(2):
                    led.value(1)
                    time.sleep(1)
                    led.value(0)
                    time.sleep(1)
                    
                try:
                    client = connect()
                    subscribe(client)
                    error_count = 0  # 重置错误计数器
                    log("INFO", "MQTT重连成功")
                    # MQTT重连成功时，LED短暂点亮
                    led.value(1)
                    time.sleep(0.5)
                    led.value(0)
                except Exception as e:
                    log("ERROR", f"MQTT重连失败: {e}")
                    error_count += 1
                    if error_count >= MAX_ERRORS:
                        log("ERROR", f"连续{MAX_ERRORS}次连接失败，重启设备...")
                        machine.reset()
                    time.sleep(ERROR_SLEEP_TIME)
                    continue
            
            # 检查是否需要定期重新初始化
            current_time = time.time()
            if current_time - last_reinit_time >= AUTO_REINIT_INTERVAL:
                reinitialize()
                # 重新连接WiFi和MQTT
                if not connect_wifi():
                    continue
                try:
                    client = connect()
                    subscribe(client)
                except:
                    continue
            
            # 检查是否需要定期OTA版本检查
            if current_time - last_ota_check >= OTA_UPDATE_INTERVAL:
                log("INFO", "定期检查版本更新...")
                check_for_updates()
                last_ota_check = current_time
            
            # 检查是否需要推送数据到Firebase（每3分钟）
            # 已在外层定义为全局变量，此处无需再次声明
            if current_time - last_firebase_push >= DATA_PUSH_INTERVAL / 1000:  # 转换为秒
                log("INFO", "定期推送数据到Firebase...")
                data = read_sensor()
                push_data_to_firebase(data)
                last_firebase_push = current_time
            
            # 实时检查消息
            try:
                client.check_msg()
            except:
                # 如果check_msg失败，说明连接可能断开
                log("WARNING", "MQTT连接断开，尝试重新连接...")
                # MQTT断开时，LED慢速闪烁
                for _ in range(2):
                    led.value(1)
                    time.sleep(1)
                    led.value(0)
                    time.sleep(1)
                    
                try:
                    client = connect()
                    subscribe(client)
                    error_count = 0  # 重置错误计数器
                    log("INFO", "MQTT重连成功")
                    # MQTT重连成功时，LED短暂点亮
                    led.value(1)
                    time.sleep(0.5)
                    led.value(0)
                except Exception as e:
                    log("ERROR", f"MQTT重连失败: {e}")
                    error_count += 1
                    if error_count >= MAX_ERRORS:
                        log("ERROR", f"连续{MAX_ERRORS}次连接失败，重启设备...")
                        machine.reset()
                    time.sleep(ERROR_SLEEP_TIME)
                    continue
            
            # MQTT连接正常时，LED缓慢闪烁
            led.value(1)
            time.sleep(LED_BLINK_INTERVAL)
            led.value(0)
            time.sleep(LED_BLINK_INTERVAL)
            
            # 重置错误计数器（如果成功运行）
            error_count = 0
            
        except OSError as e:
            error_count += 1
            log("ERROR", f'网络错误 (尝试 {error_count}/{MAX_ERRORS}): {e}')
            # 出现网络错误时，LED快速闪烁
            for _ in range(3):
                led.value(1)
                time.sleep(0.1)
                led.value(0)
                time.sleep(0.1)
                
            if error_count >= MAX_ERRORS:
                log("ERROR", f"连续{MAX_ERRORS}次网络错误，重启设备...")
                machine.reset()
            time.sleep(ERROR_SLEEP_TIME)
            
        except Exception as e:
            error_count += 1
            log("ERROR", f'未知错误 (尝试 {error_count}/{MAX_ERRORS}): {e}')
            # 出现未知错误时，LED快速双闪
            for _ in range(2):
                for _ in range(2):
                    led.value(1)
                    time.sleep(0.1)
                    led.value(0)
                    time.sleep(0.1)
                time.sleep(0.3)
                
            if error_count >= MAX_ERRORS:
                log("ERROR", f"连续{MAX_ERRORS}次未知错误，重启设备...")
                machine.reset()
            time.sleep(ERROR_SLEEP_TIME)

if __name__ == '__main__':
    main()  # 运行主程序
