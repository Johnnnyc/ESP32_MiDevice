import ubluetooth
import struct
import time
import network
from micropython import const
from config import *

# BLE事件常量
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_READ_REQUEST = const(4)

class MiDevice:
    def __init__(self):
        print("🔄 开始初始化米家BLE设备...")
        
        # 初始化设备状态
        self.switch_states = [False] * SWITCH_COUNT
        self.temperature = 0.0
        self.humidity = 0.0
        self.battery = 100
        
        # 设备信息 - 添加详细日志
        print("📱 获取设备信息...")
        # 使用统一的MAC地址获取方法，内部已包含错误处理
        self.mac_address = self._get_mac_address()
        print(f"✅ MAC地址获取成功: {self.mac_address}")
        self.device_id = self.mac_address.replace(':', '')
        print(f"📝 设备ID: {self.device_id}")
        
        # BLE相关 - 增强初始化和错误处理
        print("🔵 初始化BLE模块...")
        try:
            self.ble = ubluetooth.BLE()
            print("✅ BLE对象创建成功")
            
            # 先检查并停用可能的旧实例
            if self.ble.active():
                print("⚠️ BLE已处于激活状态，先停用...")
                self.ble.active(False)
                time.sleep(0.1)
            
            # 激活BLE
            print("🔌 激活BLE模块...")
            success = self.ble.active(True)
            if success:
                print("✅ BLE激活成功")
            else:
                print("❌ BLE激活失败")
                # 尝试多次激活
                for retry in range(2):
                    print(f"🔄 重试激活BLE ({retry+1}/2)...")
                    self.ble.active(False)
                    time.sleep(0.2)
                    success = self.ble.active(True)
                    if success:
                        print("✅ BLE激活成功")
                        break
            
            # 设置中断处理
            print("⚙️  设置BLE事件处理...")
            self.ble.irq(self._irq)
            print("✅ BLE事件处理设置完成")
        except Exception as e:
            print(f"❌ BLE初始化失败: {e}")
        
        # 连接状态
        self.device_connected = False
        self.conn_handle = None
        
        # 注册服务和特征 - 添加详细日志
        print("📋 注册BLE服务和特征...")
        try:
            self._register_services()
            print("✅ BLE服务注册成功")
        except Exception as e:
            print(f"❌ BLE服务注册失败: {e}")
            # 保存错误信息以便后续诊断
            self.last_error = str(e)
        
        print("🔄 设备初始化完成")
    
    def _get_mac_info(self):
        """
        获取MAC地址信息的统一方法
        减少重复代码并确保MAC地址获取的一致性
        """
        try:
            wlan = network.WLAN(network.STA_IF)
            wlan.active(True)  # 确保WLAN接口已激活
            mac_bytes = wlan.config('mac')
            wlan.active(False)  # 读取后可以关闭WLAN接口以节省功耗
            
            # 格式化的MAC地址字符串（带冒号）
            mac_str = ''.join(['%02x:' % b for b in mac_bytes])[:-1].upper()
            
            return mac_str, bytearray(mac_bytes)
        except Exception as e:
            print(f"⚠️ MAC地址获取异常: {e}")
            # 返回默认值以保证程序继续运行
            return "00:00:00:00:00:00", bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    
    def _get_mac_address(self):
        # 获取格式化的MAC地址字符串
        mac_str, _ = self._get_mac_info()
        return mac_str
    
    def _get_mac_bytes(self):
        # 获取MAC地址字节数组（用于广播和数据传输）
        _, mac_bytes = self._get_mac_info()
        return mac_bytes
    
    def _irq(self, event, data):
        # 处理BLE事件
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _, = data
            self.conn_handle = conn_handle
            self.device_connected = True
            print("设备已连接")
        
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _, = data
            self.device_connected = False
            self.conn_handle = None
            print("设备已断开连接")
            # 重新开始广播
            self.start_advertising()
            print("重新开始广播")
        
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            # 读取写入的值
            data = self.ble.gatts_read(self.char_handle)
            self._parse_command(data)
        
        elif event == _IRQ_GATTS_READ_REQUEST:
            conn_handle, value_handle = data
            # 准备状态报告数据
            status_data = self._build_status_report()
            # 只写入数据，移除gatts_read_perm调用（MicroPython的BLE模块不支持）
            self.ble.gatts_write(self.char_handle, status_data)
    
    def _register_services(self):
        # 创建BLE服务和特征 - 增强版本，添加详细日志和错误处理
        print("🔍 开始服务注册流程...")
        
        try:
            # 验证UUID格式
            print(f"📋 服务UUID: {MI_SERVICE_UUID}")
            print(f"📋 特征UUID: {MI_CHARACTERISTIC_UUID}")
            
            # 定义特征
            print("📝 定义BLE特征...")
            mi_characteristic = (
                ubluetooth.UUID(MI_CHARACTERISTIC_UUID),
                ubluetooth.FLAG_READ | ubluetooth.FLAG_WRITE | ubluetooth.FLAG_NOTIFY,
            )
            print("✅ 特征定义成功")
            
            # 定义服务
            print("📝 定义BLE服务...")
            mi_service = (
                ubluetooth.UUID(MI_SERVICE_UUID),
                (mi_characteristic,),
            )
            print("✅ 服务定义成功")
            
            # 准备服务列表
            services = (mi_service,)
            
            # 注册服务 - 这是关键步骤
            print("🔄 注册服务到BLE模块...")
            # 使用try-except捕获可能的错误
            try:
                service_handles = self.ble.gatts_register_services(services)
                print(f"✅ 服务注册返回句柄: {service_handles}")
                # 安全地解构返回值
                if service_handles and len(service_handles) > 0 and len(service_handles[0]) > 0:
                    self.char_handle = service_handles[0][0]
                    print(f"✅ 特征句柄设置成功: {self.char_handle}")
                else:
                    print("❌ 服务注册返回无效句柄")
                    # 使用默认句柄值继续
                    self.char_handle = 1
            except Exception as reg_error:
                print(f"❌ 服务注册过程出错: {reg_error}")
                # 使用默认句柄值继续
                self.char_handle = 1
            
            # 初始设置特征值
            print("📤 设置初始特征值...")
            try:
                initial_data = self._build_device_info()
                print(f"📊 初始数据长度: {len(initial_data)} 字节")
                self.ble.gatts_write(self.char_handle, initial_data)
                print("✅ 初始特征值设置成功")
            except Exception as write_error:
                print(f"❌ 初始特征值设置失败: {write_error}")
                
        except Exception as e:
            print(f"❌ 服务注册整体失败: {e}")
            raise  # 重新抛出异常以通知上层
    
    def _build_advertisement_data(self, simple_mode=False):
        """
        构建BLE广播数据
        
        参数:
            simple_mode: 是否使用极简广播模式，只包含最基本的可发现信息
        """
        if simple_mode:
            # 极简广播模式 - 只包含最基本的信息，确保最大兼容性
            print("📱 使用极简广播模式...")
            adv_data = bytearray()
            
            # 1. 只包含Flags和短名称
            adv_data.extend(b'\x02\x01\x06')  # 通用发现模式，可连接
            
            # 2. 非常短的设备名称（不超过8字节）
            short_name = DEVICE_NAME[:6]  # 更短的名称以确保兼容性
            name_len = len(short_name) + 1
            adv_data.append(name_len)
            adv_data.append(0x08)  # 类型：短本地名称
            adv_data.extend(short_name.encode())
            
            final_len = len(adv_data)
            print(f"✅ 极简广播数据构建完成，长度: {final_len} 字节")
            print("极简广播数据:", ['0x{:02x}'.format(b) for b in adv_data])
            return bytes(adv_data)
        
        # 标准广播模式 - 平衡可发现性和兼容性
        print("📱 构建标准广播数据...")
        adv_data = bytearray()
        
        # 1. Flags - 确保设置为可连接
        adv_data.extend(b'\x02\x01\x06')  # 通用发现模式，可连接
        
        # 2. 短设备名称
        short_name = DEVICE_NAME[:6]  # 更短的名称以确保更多空间用于必要信息
        name_len = len(short_name) + 1
        adv_data.append(name_len)
        adv_data.append(0x08)  # 类型：短本地名称
        adv_data.extend(short_name.encode())
        
        # 3. 服务UUID - 使用16位UUID以节省空间
        uuid_section = bytearray()
        uuid_section.append(0x03)  # 长度
        uuid_section.append(0x03)  # 类型：完整16位服务UUID列表
        uuid_section.extend(b'\xFE\x95')  # 米家设备常用UUID前缀
        
        # 确保总长度不超过31字节
        if len(adv_data) + len(uuid_section) <= 31:
            adv_data.extend(uuid_section)
        
        # 4. 添加制造商特定数据（如果还有空间）
        remaining_space = 31 - len(adv_data)
        if remaining_space >= 5:  # 至少需要5字节的制造商数据（包括头部）
            print("📦 添加制造商数据...")
            # 简化的制造商数据，只包含必要的标识
            # 0x01FF是一个占位符，实际使用时可以替换为真实的制造商ID
            manufacturer_data = bytearray()
            manufacturer_data.append(remaining_space - 1)  # 长度
            manufacturer_data.append(0xFF)  # 类型：制造商特定数据
            manufacturer_data.extend(b'\x01\xFF')  # 示例制造商ID
            
            # 添加设备型号的前两个字节作为标识
            model_bytes = DEVICE_MODEL.encode()[:min(2, remaining_space - 3)]
            manufacturer_data.extend(model_bytes)
            
            adv_data.extend(manufacturer_data)
        
        final_len = len(adv_data)
        print(f"✅ 标准广播数据构建完成，长度: {final_len} 字节")
        print("广播数据:", ['0x{:02x}'.format(b) for b in adv_data])
        
        return bytes(adv_data)
    
    def _build_device_info(self):
        # 构建米家设备信息
        info_data = bytearray()
        
        # 设备信息头
        info_data.append(0x01)  # 版本
        info_data.append(0x00)  # 设备类型
        
        # 设备型号
        info_data.extend(DEVICE_MODEL.encode())
        info_data.append(0x00)  # 结束符
        
        # 设备MAC地址 - 使用统一的获取方法
        mac_bytes = self._get_mac_bytes()
        info_data.extend(mac_bytes)
        
        print(f"📤 设备信息构建完成，MAC字节: {['0x{:02x}'.format(b) for b in mac_bytes]}")
        return bytes(info_data)
    
    def _parse_command(self, data):
        # 解析米家控制命令
        if len(data) < 4:
            return
        
        print("收到米家控制命令:", [hex(b) for b in data])
        
        frame_type = data[0]
        cmd = data[1]
        param_len = data[2]
        
        if cmd == 0x01:  # 设备信息请求
            print("收到设备信息请求命令")
        elif cmd == 0x02:  # 开关控制命令
            if len(data) >= 5:
                switch_index = data[3] - 1  # 米家索引从1开始
                state = data[4]
                
                if 0 <= switch_index < SWITCH_COUNT:
                    self.switch_states[switch_index] = (state == 0x01)
                    print(f"开关 {switch_index + 1} 状态更新为: {'开启' if self.switch_states[switch_index] else '关闭'}")
                    self.update_device_data()
        elif cmd == 0x03:  # 传感器数据请求
            print("收到传感器数据请求命令")
            self.update_device_data()
        elif cmd == 0x04:  # 批量控制命令
            print("收到批量控制命令")
            if len(data) >= 3 + SWITCH_COUNT:
                for i in range(min(SWITCH_COUNT, len(data) - 3)):
                    self.switch_states[i] = (data[3 + i] == 0x01)
                    print(f"开关 {i + 1} 状态更新为: {'开启' if self.switch_states[i] else '关闭'}")
                self.update_device_data()
        else:
            print(f"收到未知命令: {hex(cmd)}")
    
    def _build_status_report(self):
        # 构建状态报告
        status_data = bytearray()
        
        # 状态报告头
        status_data.append(0x04)  # 帧类型：状态报告
        status_data.append(0x00)  # 设备类型
        
        # 开关状态
        status_data.append(MI_PROP_SWITCH_STATE)
        status_data.append(SWITCH_COUNT)
        for state in self.switch_states:
            status_data.append(0x01 if state else 0x00)
        
        # 温度数据
        status_data.append(MI_PROP_TEMPERATURE)
        status_data.append(0x04)
        temp = int(self.temperature * 100)
        status_data.extend(struct.pack('!I', temp))  # 大端序4字节
        
        # 湿度数据
        status_data.append(MI_PROP_HUMIDITY)
        status_data.append(0x04)
        humi = int(self.humidity * 100)
        status_data.extend(struct.pack('!I', humi))  # 大端序4字节
        
        # 电池电量
        status_data.append(MI_PROP_BATTERY)
        status_data.append(0x01)
        status_data.append(min(100, max(0, int(self.battery))))
        
        return bytes(status_data)
    
    def update_device_data(self):
        # 更新设备数据并通知
        try:
            status_data = self._build_status_report()
            
            # 先写入特征值，这一步通常不会出错
            self.ble.gatts_write(self.char_handle, status_data)
            
            # 打印开关状态
            switch_status = " ".join([f"{i+1}:{'开' if s else '关'}" for i, s in enumerate(self.switch_states)])
            print(f"设备数据已更新: {switch_status}, 温度={self.temperature:.1f}°C, 湿度={self.humidity:.1f}%, 电量={self.battery}%")
            
            # 只有在确实连接状态下才尝试发送通知
            # OSError: -128通常是因为连接状态异常导致的通知失败
            if self.device_connected and self.conn_handle is not None:
                try:
                    self.ble.gatts_notify(self.conn_handle, self.char_handle, status_data)
                    print(f"通知已发送到连接的设备 (句柄: {self.conn_handle})")
                except OSError as e:
                    # 捕获通知错误，但不中断整体数据更新流程
                    print(f"⚠️  通知发送失败: {e}. 连接可能已断开或不稳定。")
                    # 尝试重新评估连接状态
                    self._check_connection_status()
        except Exception as e:
            # 捕获所有其他异常，确保程序不会崩溃
            print(f"❌ 设备数据更新出错: {e}")
            # 如果是连接相关错误，重置连接状态
            if isinstance(e, OSError):
                print("重置设备连接状态...")
                self.device_connected = False
                self.conn_handle = None
                # 重新开始广播
                try:
                    self.start_advertising()
                except Exception as adv_error:
                    print(f"广播重启失败: {adv_error}")
    
    def _check_connection_status(self):
        # 检查并更新连接状态
        try:
            # 尝试一个简单的BLE操作来验证连接状态
            self.ble.gatts_read(self.char_handle)
        except OSError:
            # 如果读取失败，说明连接确实有问题
            print("检测到无效连接，重置连接状态")
            self.device_connected = False
            self.conn_handle = None
            # 重新开始广播
            try:
                self.start_advertising()
            except Exception as adv_error:
                print(f"广播重启失败: {adv_error}")
    
    def _deep_reset_ble(self):
        """
        深度重置BLE模块，处理极端情况下的蓝牙模块异常
        这个方法执行完全重置，模拟硬件重置的效果
        """
        print("🔥 执行BLE深度重置...")
        
        # 尝试多种重置方式
        for attempt in range(3):
            print(f"🔄 BLE重置尝试 {attempt+1}/3")
            try:
                # 1. 停止广播
                try:
                    print("🛑 停止广播...")
                    self.ble.gap_advertise(None)
                    time.sleep(0.1)
                except Exception as e:
                    print(f"⚠️  停止广播时出错: {e}")
                
                # 2. 停用BLE
                try:
                    print("🔌 停用BLE...")
                    self.ble.active(False)
                    # 给足够的时间完全关闭
                    time.sleep(0.5)
                except Exception as e:
                    print(f"⚠️  停用BLE时出错: {e}")
                
                # 3. 清除事件处理
                try:
                    print("🧹 清除事件处理...")
                    self.ble.irq(None)
                    time.sleep(0.1)
                except Exception as e:
                    print(f"⚠️  清除事件处理时出错: {e}")
                
                # 4. 重新激活BLE
                try:
                    print("🔋 重新激活BLE...")
                    success = self.ble.active(True)
                    if success:
                        print("✅ BLE重新激活成功")
                        # 重新设置中断处理
                        print("⚙️  重新设置事件处理...")
                        self.ble.irq(self._irq)
                        
                        # 重新注册服务
                        print("📋 重新注册服务...")
                        try:
                            self._register_services()
                            print("✅ 服务重新注册成功")
                            return True
                        except Exception as reg_e:
                            print(f"⚠️  服务重新注册失败: {reg_e}")
                    else:
                        print("❌ BLE重新激活失败")
                except Exception as e:
                    print(f"⚠️  重新激活BLE时出错: {e}")
                    
            except Exception as e:
                print(f"❌ 重置尝试 {attempt+1} 失败: {e}")
            
            # 等待一段时间后重试
            time.sleep(0.3)
        
        print("❌ 所有BLE深度重置尝试均失败")
        return False
    
    def start_advertising(self, force_simple=False, use_deep_reset=False):
        """
        启动BLE广播，支持多种模式
        
        参数:
            force_simple: 是否强制使用极简广播模式
            use_deep_reset: 是否在启动前执行BLE深度重置
        """
        print("🚀 开始启动BLE广播...")
        
        # 如果指定了深度重置，则在开始前执行
        if use_deep_reset:
            if not self._deep_reset_ble():
                print("⚠️  深度重置失败，但仍继续尝试广播")
        
        # 尝试多种广播模式，从简单到复杂
        broadcast_modes = [
            {'name': '极简模式', 'simple': True, 'interval': 320},  # 200ms
            {'name': '标准模式', 'simple': False, 'interval': 200}, # 125ms
            {'name': '高频模式', 'simple': True, 'interval': 160}   # 100ms
        ]
        
        if force_simple:
            # 强制使用极简模式
            broadcast_modes = [broadcast_modes[0]]
        
        for mode in broadcast_modes:
            print(f"🔄 尝试{mode['name']}广播...")
            try:
                # 1. 确保BLE已激活
                if not self.ble.active():
                    print("🔌 激活BLE模块...")
                    self.ble.active(True)
                    self.ble.irq(self._irq)
                
                # 2. 停止当前广播
                print("🛑 停止当前广播...")
                self.ble.gap_advertise(None)
                time.sleep(0.1)
                
                # 3. 根据模式构建广播数据
                adv_data = self._build_advertisement_data(simple_mode=mode['simple'])
                
                # 4. 构建扫描响应数据（仅在非极简模式使用）
                scan_rsp = None
                if not mode['simple']:
                    print("📋 构建扫描响应数据...")
                    scan_rsp = bytearray()
                    
                    # 添加完整设备名称
                    name_bytes = DEVICE_NAME.encode()
                    name_section = bytearray()
                    name_section.append(len(name_bytes) + 1)
                    name_section.append(0x09)  # 类型：完整本地名称
                    name_section.extend(name_bytes)
                    
                    # 确保扫描响应数据不超过31字节
                    if len(name_section) <= 31:
                        scan_rsp.extend(name_section)
                        print(f"✅ 扫描响应数据构建完成，长度: {len(scan_rsp)} 字节")
                    else:
                        print("⚠️  设备名称过长，不包含在扫描响应中")
                
                # 5. 启动广播 - 使用更兼容的参数格式
                print(f"📡 启动广播 (间隔: {mode['interval']} * 0.625ms)...")
                
                # 注意：在某些MicroPython版本中，gap_advertise的参数格式可能不同
                try:
                    # 尝试带扫描响应的版本
                    if scan_rsp:
                        self.ble.gap_advertise(mode['interval'], adv_data, resp_data=scan_rsp)
                    else:
                        self.ble.gap_advertise(mode['interval'], adv_data)
                    
                    # 验证广播是否成功启动（通过再次检查active状态）
                    if self.ble.active():
                        print("🎉 BLE广播成功启动！")
                        print(f"📶 广播模式: {mode['name']}")
                        print(f"📱 设备名称: {DEVICE_NAME}")
                        print(f"🔧 设备型号: {DEVICE_MODEL}")
                        print(f"📡 广播间隔: {mode['interval'] * 0.625:.1f}ms")
                        print("📲 请使用以下方法测试设备发现:")
                        print("  1. 手机蓝牙设置页面扫描")
                        print("  2. 米家APP添加设备")
                        print("  3. 青萍盲网关")
                        print("  4. 电脑蓝牙扫描器")
                        return True
                    else:
                        print("❌ 广播启动后BLE变为非激活状态")
                except TypeError:
                    # 尝试兼容旧版MicroPython的参数格式
                    print("🔄 尝试兼容模式启动广播...")
                    # 只使用必需参数
                    self.ble.gap_advertise(mode['interval'], adv_data)
                    if self.ble.active():
                        print("🎉 BLE广播成功启动（兼容模式）！")
                        return True
                    
            except Exception as e:
                print(f"❌ {mode['name']}广播失败: {e}")
                
            # 如果失败，尝试下一种模式前先重置BLE
            print("🔄 重置BLE状态...")
            try:
                self.ble.active(False)
                time.sleep(0.2)
                self.ble.active(True)
                self.ble.irq(self._irq)
            except Exception:
                pass
        
        # 所有模式都失败了
        print("❌ 所有广播模式均失败！")
        print("💡 建议尝试:")
        print("  1. 检查ESP32硬件连接")
        print("  2. 尝试重新上电设备")
        print("  3. 检查MicroPython固件版本")
        print("  4. 确认BLE功能是否正常")
        print("  5. 尝试使用深度重置功能")
        return False