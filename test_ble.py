# 测试脚本：验证BLE广播功能 - 增强版
import time
import gc
from mi_device import MiDevice
from config import DEVICE_NAME

def print_separator():
    """打印分隔线，增强输出可读性"""
    print("-" * 50)

def main():
    print("🚀 启动BLE广播测试 - 增强诊断版")
    print("🔍 请使用手机、米家APP或电脑蓝牙扫描器查找设备")
    print_separator()
    
    # 清理内存
    print("🧹 清理内存...")
    gc.collect()
    
    # 创建设备实例
    device = MiDevice()
    print_separator()
    
    print("📱 开始尝试广播...")
    print("📶 将依次测试不同广播模式和重置策略")
    print("🔄 请耐心等待，每种模式将持续一段时间")
    print_separator()
    
    # 测试多种广播模式和重置策略
    test_strategies = [
        {"name": "标准极简模式", "force_simple": True, "use_deep_reset": False},
        {"name": "标准标准模式", "force_simple": False, "use_deep_reset": False},
        {"name": "深度重置+极简模式", "force_simple": True, "use_deep_reset": True},
        {"name": "高频广播模式", "force_simple": True, "use_deep_reset": False, "custom_interval": True}
    ]
    
    found = False
    
    for idx, strategy in enumerate(test_strategies):
        print(f"\n📱 [{idx+1}/{len(test_strategies)}] 正在测试: {strategy['name']}")
        print(f"🔧 策略参数: 极简模式={strategy['force_simple']}, 深度重置={strategy['use_deep_reset']}")
        
        # 启动广播
        success = device.start_advertising(
            force_simple=strategy["force_simple"],
            use_deep_reset=strategy["use_deep_reset"]
        )
        
        if success:
            print(f"✅ {strategy['name']}广播启动成功")
            
            # 设置测试时间
            test_time = 15 if strategy["use_deep_reset"] else 10
            print(f"📡 等待{test_time}秒，期间请尝试发现设备...")
            
            # 每2秒提示一次
            for i in range(test_time // 2):
                time.sleep(2)
                remaining = test_time - (i + 1) * 2
                print(f"⏰ 剩余等待时间: {remaining}秒 - 请在蓝牙扫描器中查找设备")
            
            # 询问是否已找到设备（通过脚本无法自动检测，需要用户确认）
            print("\n❓ 发现设备测试:")
            print("  - 在手机蓝牙设置中能看到ESP32设备吗？")
            print("  - 米家APP是否能检测到新设备？")
            print("  - 电脑蓝牙扫描器能否找到该设备？")
            
            # 标记为已找到（实际需要用户确认）
            # 这里我们假设有可能找到，以便继续测试
            if not found:
                found = True  # 一旦找到，保持为true
                print("🎉 标记为可能已找到，请继续测试以确认稳定性")
        else:
            print(f"❌ {strategy['name']}广播启动失败")
            # 短暂延迟后继续下一种策略
            time.sleep(3)
        
        print_separator()
    
    # 最终总结
    print("\n📊 测试完成总结:")
    print("🔄 所有广播模式和重置策略均已测试")
    
    if found:
        print("✅ 测试期间可能已成功广播，请在实际设备上验证")
    else:
        print("❌ 所有测试策略均未能成功启动广播")
    
    print("\n💡 排查建议:")
    print("  1. 确认ESP32硬件连接正确，天线是否安装")
    print("  2. 尝试完全断电重启设备（拔下电源后等待10秒再上电）")
    print("  3. 检查MicroPython固件版本是否支持BLE功能")
    print("  4. 尝试使用不同的手机或电脑进行蓝牙扫描")
    print("  5. 确认设备周围没有太多蓝牙设备造成的干扰")
    print("  6. 如果使用的是ESP32-S2或ESP32-C3，请注意它们的BLE实现可能有差异")
    
    print("\n📱 设备信息:")
    print(f"  - 设备名称: {DEVICE_NAME}")
    print(f"  - MAC地址: {device.mac_address if hasattr(device, 'mac_address') else '未知'}")
    print(f"  - 设备ID: {device.device_id if hasattr(device, 'device_id') else '未知'}")

if __name__ == "__main__":
    main()