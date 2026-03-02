#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <DHT.h>
#include <DHT_U.h>

// 设备配置
#define DEVICE_NAME "ESP32_MiDevice"
#define DEVICE_MODEL "esp32.sensor_switch.v1"  // 自定义设备型号

// DHT11传感器配置
#define DHT_PIN 4       // DHT11连接到GPIO4
#define DHT_TYPE DHT11  // DHT传感器类型

// IO口开关配置
#define SWITCH_COUNT 4  // 支持的开关数量
#define SWITCH_PINS {5, 18, 19, 21}  // 开关连接的GPIO口

// 米家BLE设备标准UUID
#define MI_SERVICE_UUID "0000fe95-0000-1000-8000-00805f9b34fb"  // 米家设备服务UUID
#define MI_CHARACTERISTIC_UUID "00000001-0000-1000-8000-00805f9b34fb"  // 米家设备特征UUID

// 米家设备类型定义
#define MI_DEVICE_TYPE_SWITCH 0x01  // 开关类型
#define MI_DEVICE_TYPE_SENSOR 0x02  // 传感器类型

// 米家设备属性定义
#define MI_PROP_SWITCH_STATE 0x01  // 开关状态
#define MI_PROP_TEMPERATURE 0x02    // 温度
#define MI_PROP_HUMIDITY 0x03       // 湿度
#define MI_PROP_BATTERY 0x04        // 电池电量

BLEServer* pServer = NULL;
bool deviceConnected = false;
bool oldDeviceConnected = false;

// 设备状态
bool switchStates[SWITCH_COUNT] = {false, false, false, false};  // 多个开关状态
float temperature = 0.0;   // 真实温度
float humidity = 0.0;      // 真实湿度
int battery = 100;         // 模拟电量

// DHT传感器实例
DHT dht(DHT_PIN, DHT_TYPE);

// 开关引脚数组
const int switchPins[SWITCH_COUNT] = SWITCH_PINS;

// 设备信息
String macAddress = "";
String deviceId = "";

// 米家设备加密信息
uint8_t deviceKey[16] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                         0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};

// 米家设备状态报告间隔
#define STATUS_REPORT_INTERVAL 5000  // 5秒

// 米家设备帧类型
#define MI_FRAME_TYPE_ADVERTISE 0x01  // 广播帧
#define MI_FRAME_TYPE_CONTROL 0x02     // 控制帧
#define MI_FRAME_TYPE_RESPONSE 0x03    // 响应帧
#define MI_FRAME_TYPE_STATUS 0x04      // 状态报告帧

// 接收控制命令的回调
class ControlCharacteristicCallbacks : public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
        std::string value = pCharacteristic->getValue();
        
        if (value.length() > 0) {
            // 解析米家控制命令
            parseMiControlCommand(value);
        }
    }
    
    void onRead(BLECharacteristic *pCharacteristic) {
        // 读取设备信息时返回设备状态
        std::string statusReport = buildMiStatusReport();
        pCharacteristic->setValue(statusReport);
        Serial.println("响应设备状态读取请求");
    }
};

// 解析米家设备控制命令
void parseMiControlCommand(const std::string &command) {
    if (command.length() < 4) return;
    
    Serial.print("收到米家控制命令: ");
    for (int i = 0; i < command.length(); i++) {
        Serial.printf("%02X ", (uint8_t)command[i]);
    }
    Serial.println();
    
    // 米家命令格式解析
    uint8_t frameType = command[0];
    uint8_t cmd = command[1];
    uint8_t paramLen = command[2];
    
    switch(cmd) {
        case 0x01:  // 设备信息请求
            Serial.println("收到设备信息请求命令");
            break;
            
        case 0x02:  // 开关控制命令
            if (command.length() >= 4) {
                uint8_t switchIndex = command[3] - 1;  // 米家索引从1开始
                uint8_t state = command[4];
                
                if (switchIndex < SWITCH_COUNT) {
                    switchStates[switchIndex] = (state == 0x01);
                    digitalWrite(switchPins[switchIndex], switchStates[switchIndex] ? HIGH : LOW);
                    Serial.printf("开关 %d 状态更新为: %s\n", switchIndex + 1, switchStates[switchIndex] ? "开启" : "关闭");
                    updateDeviceData();
                }
            }
            break;
            
        case 0x03:  // 传感器数据请求
            Serial.println("收到传感器数据请求命令");
            readSensorData();
            updateDeviceData();
            break;
            
        case 0x04:  // 批量控制命令
            Serial.println("收到批量控制命令");
            if (command.length() >= 3 + SWITCH_COUNT) {
                for (int i = 0; i < SWITCH_COUNT; i++) {
                    switchStates[i] = (command[3 + i] == 0x01);
                    digitalWrite(switchPins[i], switchStates[i] ? HIGH : LOW);
                    Serial.printf("开关 %d 状态更新为: %s\n", i + 1, switchStates[i] ? "开启" : "关闭");
                }
                updateDeviceData();
            }
            break;
            
        default:
            Serial.printf("收到未知命令: %02X\n", cmd);
            break;
    }
}

// 解析控制命令
void parseControlCommand(const std::string &command) {
    // 兼容米家设备命令格式
    parseMiControlCommand(command);
}

// 设备连接状态回调
class ServerCallbacks : public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
        deviceConnected = true;
        Serial.println("设备已连接");
    }
    
    void onDisconnect(BLEServer* pServer) {
        deviceConnected = false;
        Serial.println("设备已断开连接");
        // 重新开启广播
        delay(500);
        pServer->startAdvertising();
        Serial.println("重新开始广播");
    }
};

// 初始化BLE
void initBLE() {
    Serial.println("初始化BLE设备...");
    
    // 创建BLE设备
    BLEDevice::init(DEVICE_NAME);
    
    // 创建BLE服务器
    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new ServerCallbacks());
    
    // 创建米家服务
    BLEService *pMiService = pServer->createService(BLEUUID(MI_SERVICE_UUID));
    
    // 创建米家特征（主特征）
    BLECharacteristic *pMiCharacteristic = pMiService->createCharacteristic(
        BLEUUID(MI_CHARACTERISTIC_UUID),
        BLECharacteristic::PROPERTY_READ |
        BLECharacteristic::PROPERTY_WRITE |
        BLECharacteristic::PROPERTY_NOTIFY
    );
    pMiCharacteristic->addDescriptor(new BLE2902());
    pMiCharacteristic->setCallbacks(new ControlCharacteristicCallbacks());
    
    // 构建米家设备信息数据
    std::string miDeviceInfo = buildMiDeviceInfo();
    pMiCharacteristic->setValue(miDeviceInfo);
    
    // 更新设备数据
    updateDeviceData();
    
    // 启动服务
    pMiService->start();
    
    // 开始广播
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    
    // 设置广播数据为米家设备格式
    std::string advData = buildMiAdvertisingData();
    pAdvertising->setAdvertisementData(BLEAdvertisementData(advData));
    
    pAdvertising->addServiceUUID(BLEUUID(MI_SERVICE_UUID));
    pAdvertising->setScanResponse(true);
    pAdvertising->setMinPreferred(0x06);  // 最小BLE连接间隔
    pAdvertising->setMinPreferred(0x12);  // 最大BLE连接间隔
    BLEDevice::startAdvertising();
    
    Serial.println("BLE设备已初始化并开始广播");
    Serial.printf("设备名称: %s\n", DEVICE_NAME);
    Serial.printf("设备型号: %s\n", DEVICE_MODEL);
    Serial.printf("设备ID: %s\n", deviceId.c_str());
    Serial.printf("MAC地址: %s\n", macAddress.c_str());
}

// 构建米家设备广播数据
std::string buildMiAdvertisingData() {
    // 获取MAC地址
    uint8_t mac[6];
    esp_read_mac(mac, ESP_MAC_WIFI_STA);
    char macStr[18];
    sprintf(macStr, "%02X:%02X:%02X:%02X:%02X:%02X", 
            mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    macAddress = String(macStr);
    
    // 生成设备ID（基于MAC地址）
    deviceId = macAddress;
    deviceId.replace(":", "");
    
    // 构建米家设备广播数据格式
    // 参考米家BLE设备的广播格式
    uint8_t advData[31] = {0};
    int offset = 0;
    
    // 设备类型和版本
    advData[offset++] = 0x02;
    advData[offset++] = 0x01;
    advData[offset++] = 0x06;
    
    // 米家设备信息
    advData[offset++] = 0x1A;
    advData[offset++] = 0xFF;
    advData[offset++] = 0x55;
    advData[offset++] = 0x01;  // 米家设备标识
    
    // 设备型号
    const char* model = DEVICE_MODEL;
    for (int i = 0; i < strlen(model); i++) {
        advData[offset++] = model[i];
    }
    advData[offset++] = 0x00;
    
    // MAC地址（逆序）
    for (int i = 5; i >= 0; i--) {
        advData[offset++] = mac[i];
    }
    
    // 设备状态（简化版）
    advData[offset++] = 0x00;
    advData[offset++] = 0x00;
    advData[offset++] = 0x00;
    
    return std::string((const char*)advData, offset);
}

// 构建米家设备信息
std::string buildMiDeviceInfo() {
    // 构建米家设备信息数据格式
    // 这里使用米家设备的标准格式
    uint8_t infoData[64] = {0};
    int offset = 0;
    
    // 设备信息头
    infoData[offset++] = 0x01;  // 版本
    infoData[offset++] = 0x00;  // 设备类型
    
    // 设备型号
    const char* model = DEVICE_MODEL;
    for (int i = 0; i < strlen(model); i++) {
        infoData[offset++] = model[i];
    }
    infoData[offset++] = 0x00;
    
    // 设备MAC地址
    uint8_t mac[6];
    esp_read_mac(mac, ESP_MAC_WIFI_STA);
    for (int i = 0; i < 6; i++) {
        infoData[offset++] = mac[i];
    }
    
    return std::string((const char*)infoData, offset);
}

// 读取传感器数据
void readSensorData() {
    temperature = dht.readTemperature();
    humidity = dht.readHumidity();
    
    // 检查传感器读取是否成功
    if (isnan(temperature) || isnan(humidity)) {
        Serial.println("DHT11传感器读取失败");
        return;
    }
    
    Serial.printf("DHT11读取成功: 温度=%.1f°C, 湿度=%.1f%%\n", temperature, humidity);
}

// 构建米家设备状态报告
std::string buildMiStatusReport() {
    // 读取最新传感器数据
    readSensorData();
    
    // 构建米家设备状态报告格式
    uint8_t statusData[32] = {0};
    int offset = 0;
    
    // 状态报告头
    statusData[offset++] = 0x04;  // 帧类型：状态报告
    statusData[offset++] = 0x00;  // 设备类型
    
    // 开关状态
    statusData[offset++] = MI_PROP_SWITCH_STATE;
    statusData[offset++] = SWITCH_COUNT;
    for (int i = 0; i < SWITCH_COUNT; i++) {
        statusData[offset++] = switchStates[i] ? 0x01 : 0x00;
    }
    
    // 温度数据
    statusData[offset++] = MI_PROP_TEMPERATURE;
    statusData[offset++] = 0x04;
    int temp = (int)(temperature * 100);
    statusData[offset++] = (temp >> 24) & 0xFF;
    statusData[offset++] = (temp >> 16) & 0xFF;
    statusData[offset++] = (temp >> 8) & 0xFF;
    statusData[offset++] = temp & 0xFF;
    
    // 湿度数据
    statusData[offset++] = MI_PROP_HUMIDITY;
    statusData[offset++] = 0x04;
    int humi = (int)(humidity * 100);
    statusData[offset++] = (humi >> 24) & 0xFF;
    statusData[offset++] = (humi >> 16) & 0xFF;
    statusData[offset++] = (humi >> 8) & 0xFF;
    statusData[offset++] = humi & 0xFF;
    
    // 电池电量
    statusData[offset++] = MI_PROP_BATTERY;
    statusData[offset++] = 0x01;
    statusData[offset++] = battery;
    
    return std::string((const char*)statusData, offset);
}

// 更新设备数据并上报
void updateDeviceData() {
    // 构建米家状态报告
    std::string statusReport = buildMiStatusReport();
    
    // 更新主特征值
    BLECharacteristic *pMiCharacteristic = pServer->getService(BLEUUID(MI_SERVICE_UUID))->getCharacteristic(BLEUUID(MI_CHARACTERISTIC_UUID));
    pMiCharacteristic->setValue(statusReport);
    
    // 如果设备已连接，通知更新
    if (deviceConnected) {
        pMiCharacteristic->notify();
        
        // 打印开关状态
        String switchStatus = "";
        for (int i = 0; i < SWITCH_COUNT; i++) {
            switchStatus += String(i + 1) + ":" + (switchStates[i] ? "开" : "关") + " ";
        }
        
        Serial.printf("设备数据已更新并通知: %s, 温度=%.1f°C, 湿度=%.1f%%, 电量=%d%%\n", 
                     switchStatus.c_str(), temperature, humidity, battery);
    }
}

// 读取并更新传感器数据
void updateSensorData() {
    readSensorData();
    
    // 模拟电量消耗
    battery -= random(0, 10) * 0.01;
    if (battery < 0) battery = 0;
}

void setup() {
    Serial.begin(115200);
    delay(1000);
    
    Serial.println("========================================");
    Serial.println("ESP32 米家传感器开关设备");
    Serial.println("可被青萍盲网关发现并通过米家系统控制");
    Serial.println("支持DHT11温湿度传感器和多个IO开关");
    Serial.println("========================================");
    
    // 初始化DHT11传感器
    dht.begin();
    Serial.printf("DHT11传感器初始化完成，连接到GPIO%d\n", DHT_PIN);
    
    // 初始化开关IO口
    for (int i = 0; i < SWITCH_COUNT; i++) {
        pinMode(switchPins[i], OUTPUT);
        digitalWrite(switchPins[i], LOW);  // 初始状态为关闭
        Serial.printf("开关 %d 初始化完成，连接到GPIO%d\n", i + 1, switchPins[i]);
    }
    
    // 初始化BLE设备
    initBLE();
    
    // 初始化随机数生成器
    randomSeed(esp_random());
}

void loop() {
    // 更新传感器数据
    static unsigned long lastSensorUpdate = 0;
    if (millis() - lastSensorUpdate > 5000) {  // 每5秒更新一次传感器数据
        lastSensorUpdate = millis();
        updateSensorData();
        updateDeviceData();
    }
    
    // 设备连接状态变化处理
    if (deviceConnected != oldDeviceConnected) {
        oldDeviceConnected = deviceConnected;
        if (deviceConnected) {
            Serial.println("青萍盲网关已连接");
        } else {
            Serial.println("青萍盲网关已断开连接");
        }
    }
    
    // 短暂延迟
    delay(100);
}