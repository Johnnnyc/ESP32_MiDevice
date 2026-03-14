# ESP32 MicroPython OTA 远程升级方案

## 一、系统组成

本方案包含以下文件：

1. **boot.py** - 开机自动联网和OTA检查
2. **updata.py** - 批量更新多文件
3. **main.py** - 芦丁鸡孵化器温控器业务逻辑

## 二、使用步骤

### 1. 准备工作

- 在 Gitee 新建**公开仓库**
- 上传 `updata.py`、`main.py`、`a.py`（如果需要）
- 复制**原始文件地址**（Raw）

### 2. 配置文件

#### boot.py 配置
```python
# WiFi 信息（改成你自己的）
WIFI_SSID = "你的WiFi名"
WIFI_PWD = "你的WiFi密码"

# 云端更新脚本
UPDATE_URL = "https://gitee.com/你的用户名/仓库/raw/master/updata.py"
```

#### updata.py 配置
```python
# 要更新的文件列表（改成你自己的）
file_map = {
    "main.py": "https://gitee.com/xxx/xxx/raw/master/main.py",
    "a.py": "https://gitee.com/xxx/xxx/raw/master/a.py",
    "b.py": "https://gitee.com/xxx/xxx/raw/master/b.py",
}
```

### 3. 烧录文件

- 烧录 `boot.py` 到 ESP32
- 烧录 `main.py` 到 ESP32（首次烧录）

### 4. 运行流程

1. ESP32 开机运行 `boot.py`
2. 自动连接 WiFi
3. 下载云端 `updata.py` 并检查更新标志
4. 如果需要更新，下载并运行 `updata.py`
5. `updata.py` 批量下载并更新其他文件
6. 更新完成后自动重启
7. 运行更新后的 `main.py`

## 三、更新机制

- **更新标志**：文件第一行 `# update=1` 中的第10个字符（从0开始计数）
- **版本管理**：通过 `ver` 变量管理版本号
- **备份机制**：每次更新前会自动备份现有文件
- **清理机制**：自动删除3小时前的备份文件

## 四、硬件配置

- **OLED**：SCL=GPIO14, SDA=GPIO12
- **DS18B20**：数据引脚=GPIO13
- **继电器**：控制引脚=GPIO22

## 五、注意事项

1. 确保 Gitee 仓库是公开的
2. 确保 WiFi 信息正确
3. 确保文件路径和URL正确
4. 首次使用时需要手动烧录 `boot.py` 和 `main.py`
5. 后续更新可通过修改 Gitee 上的文件实现

## 六、故障排查

- **WiFi 连接失败**：检查 WiFi 名称和密码
- **OTA 失败**：检查网络连接和 Gitee URL
- **传感器读取失败**：检查硬件连接
- **继电器不工作**：检查继电器连接和控制逻辑

## 七、功能扩展

- 可添加按键设置目标温度
- 可添加温度历史记录
- 可添加远程控制功能
- 可添加异常报警功能