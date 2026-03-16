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
AUTO_REINIT_INTERVAL = 14400  # 自动重新初始化间隔（秒）= 4小时

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
        
        # 使用时间戳作为数据ID
        import time
        timestamp = str(int(time.time()))
        # 使用更简单的URL构建
        url = FIREBASE_URL + "/sensor-data/" + timestamp + ".json"
        headers = {"Content-Type": "application/json"}
        
        # 使用PUT请求保存历史数据，使用时间戳作为ID
        response = urequests.put(url, json=simple_data, headers=headers, timeout=5)
        response.close()
        
        # 保留成功日志，便于调试
        log("INFO", "Firebase推送成功")
        
        gc.collect()  # 推送后进行内存回收
        return True
    except Exception as e:
        # 保留失败日志，便于调试
        log("ERROR", "Firebase推送失败")
        return False

def log(level, message):
    """简单的日志函数"""
    global last_ntp_sync
    try:
        current_time = time.localtime()
        # 添加时区偏移量（东八区为 +8 小时）
        utc_hour = current_time[3]
        tz_hour = utc_hour + 8
        
        # 处理跨天情况
        if tz_hour >= 24:
            tz_hour -= 24
        
        time_str = "{:02d}:{:02d}:{:02d}".format(
            tz_hour, current_time[4], current_time[5]
        )
    except Exception as e:
        # 如果时间获取失败，使用简单格式
        time_str = "??:??:??"
    
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

def connect():
    global client
    while True:
        try:
            # 如果已有客户端连接，先断开并释放资源
            if client:
                try:
                    client.disconnect()
                except:
                    pass
                client = None
                
            ssl_context = create_ssl_context()
            client = MQTTClient(CLIENT_ID, SERVER, PORT, USERNAME, PASSWORD, ssl=ssl_context, keepalive=10)
            client.connect()
            print('Connected to MQTT Broker "{server}"'.format(server=SERVER))
            return client
        except Exception as e:
            print('MQTT连接失败:', e)
            print('5秒后尝试重新连接...')
            time.sleep(2)

def create_ssl_context():
    # Create an SSL context
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.load_verify_locations(CA_CERTS_PATH)
    return ssl_context

def read_sensor():
    """读取传感器数据，增加重试机制"""
    # 初始化变量
    temperature = None
    humidity = None
    time_str = ""
    
    # 读取温湿度数据，增加重试机制
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries and (temperature is None or humidity is None):
        try:
            dht.measure()  # 测量温湿度
            temperature = dht.temperature()  # 获取温度
            humidity = dht.humidity()  # 获取湿度
            if temperature is not None and humidity is not None:
                log("INFO", f'DHT11读取成功: 温度=%.1f°C, 湿度=%.1f%%' % (temperature, humidity))
        except Exception as e:
            retry_count += 1
            log("ERROR", f'读取温湿度失败 (尝试 {retry_count}/{max_retries}): {e}')
            if retry_count < max_retries:
                time.sleep(0.5)  # 短暂延迟后重试


    # 获取网络时间并格式化为字符串
    global last_ntp_sync
    try:
        current_epoch = time.time()
        # 每小时同步一次 NTP 时间（如果距离上次同步超过 1 小时）
        if current_epoch - last_ntp_sync > 3600:
            if sync_ntp_time():
                log("INFO", "NTP 时间同步成功（传感器读取时同步）")
            else:
                log("WARNING", "NTP 时间同步失败（传感器读取时同步）")
        
        # 获取当前时间并添加时区偏移
        current_time = time.localtime()
        utc_hour = current_time[3]
        tz_hour = utc_hour + 8
        
        # 处理跨天情况
        if tz_hour >= 24:
            tz_hour -= 24
        
        time_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
            current_time[0], current_time[1], current_time[2],
            tz_hour, current_time[4], current_time[5]
        )
    except Exception as e:
        log("ERROR", f'获取网络时间失败：{e}')
        # 获取当前时间并格式化为字符串（无 NTP 同步）
        current_time = time.localtime()
        utc_hour = current_time[3]
        tz_hour = utc_hour + 8
        
        # 处理跨天情况
        if tz_hour >= 24:
            tz_hour -= 24
        
        time_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
            current_time[0], current_time[1], current_time[2],
            tz_hour, current_time[4], current_time[5]
        )
    
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
            log("INFO", "收到更新指令，开始OTA更新...")
            try:
                # 下载更新脚本
                UPDATE_URL = "https://raw.githubusercontent.com/Johnnnyc/ESP32_MiDevice/main/updata.py"
                log("INFO", f"下载更新脚本: {UPDATE_URL}")
                resp = urequests.get(UPDATE_URL, timeout=30)
                data = resp.content
                resp.close()
                
                # 写入更新脚本
                with open("updata.py", "wb") as f:
                    f.write(data)
                log("INFO", "更新脚本下载完成")
                
                # 运行更新脚本
                log("INFO", "运行更新脚本...")
                import updata
                response = {"更新版本成功"}
                client.publish(update, json.dumps(response))
            except Exception as e:
                log("ERROR", f"OTA更新失败: {e}")
                response = {"更新版本失败"}
                client.publish(update, json.dumps(response))
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

def sync_ntp_time():
    """同步 NTP 时间，返回是否成功"""
    global last_ntp_sync
    try:
        # 使用国内可用的 NTP 服务器
        ntptime.host = 'ntp.aliyun.com'  # 阿里云 NTP 服务器
        ntptime.settime()  # 同步网络时间
        last_ntp_sync = time.time()  # 使用同步后的时间
        return True
    except Exception as e:
        print(f'NTP 同步失败 (阿里云): {e}')
        # 尝试使用其他 NTP 服务器
        try:
            ntptime.host = 'cn.pool.ntp.org'  # 中国 NTP 服务器池
            ntptime.settime()
            last_ntp_sync = time.time()  # 使用同步后的时间
            return True
        except Exception as e2:
            print(f'NTP 同步失败 (备用服务器): {e2}')
            return False

def main():
    global client, last_reinit_time, last_ntp_sync
    
    # 第一步：连接 WiFi
    if not connect_wifi():
        # WiFi 未连接时无法同步 NTP，使用系统时间
        log("ERROR", "WiFi 连接失败，系统无法启动")
        # WiFi 连接失败时，LED 快速闪烁
        for _ in range(10):
            led.value(1)
            time.sleep(0.1)
            led.value(0)
            time.sleep(0.1)
        return
    
    # 第二步：立即同步 NTP 时间（在任何日志记录之前）
    log("INFO", "正在同步 NTP 时间...")
    ntp_success = sync_ntp_time()
    if ntp_success:
        log("INFO", "NTP 时间同步成功")
    else:
        log("WARNING", "NTP 时间同步失败，使用系统时间")
    
    # 第三步：记录启动日志（此时已有准确时间）
    log("INFO", "启动 ESP32 温湿度监控系统")
    
    # 连接 MQTT
    try:
        client = connect()
        subscribe(client)
        log("INFO", "MQTT 连接和订阅成功")
        # MQTT 连接成功时，LED 短暂点亮
        led.value(1)
        time.sleep(1)
        led.value(0)
    except Exception as e:
        log("ERROR", f"MQTT 连接失败：{e}")
        # MQTT 连接失败时，LED 慢速闪烁
        for _ in range(5):
            led.value(1)
            time.sleep(1)
            led.value(0)
            time.sleep(1)
        return
    
    global last_firebase_push
    error_count = 0  # 错误计数器
    last_reinit_time = time.time()  # 初始化重新初始化时间
    last_ota_check = time.time()  # 初始化 OTA 检查时间
    last_firebase_push = time.time()  # 初始化 Firebase 推送时间
    # last_ntp_sync 已在 sync_ntp_time 中设置
    
    # 使用计数器来控制推送间隔，避免系统时间跳变的影响
    firebase_push_counter = 0
    push_interval_seconds = DATA_PUSH_INTERVAL / 1000
    
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
            
            # 每小时同步一次 NTP 时间（保持时间准确性）
            current_epoch = time.time()
            if current_epoch - last_ntp_sync > 3600:  # 3600 秒 = 1 小时
                if sync_ntp_time():
                    log("INFO", "NTP 时间同步成功（定时同步）")
                    # NTP 同步后更新 last_reinit_time，避免时间跳变触发初始化
                    last_reinit_time = time.time()
                else:
                    log("WARNING", "NTP 时间同步失败（定时同步）")
            
            # 检查是否需要定期重新初始化（4 小时）
            current_time = time.time()
            if current_time - last_reinit_time >= AUTO_REINIT_INTERVAL:  # 4 小时
                reinitialize()
                # 重新连接 WiFi 和 MQTT
                if not connect_wifi():
                    continue
                try:
                    client = connect()
                    subscribe(client)
                except:
                    continue
            
            # 使用计数器来控制推送间隔，避免系统时间跳变的影响
            firebase_push_counter += 1  # 每次循环增加计数器
            
            #log("DEBUG", f"推送计数器: {firebase_push_counter}, 推送间隔: {push_interval_seconds}")
            if firebase_push_counter >= push_interval_seconds:
                log("INFO", "定期推送数据到Firebase...")
                data = read_sensor()
                push_data_to_firebase(data)
                log("DEBUG", "重置推送计数器")
                firebase_push_counter = 0  # 重置计数器
            
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
            time.sleep(0.5)  # 0.5秒
            led.value(0)
            time.sleep(0.5)  # 0.5秒
            # 每次循环总时间约为1秒，确保计数器准确性
            
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

