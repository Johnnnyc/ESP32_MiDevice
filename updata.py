# update=1
# 上面这行决定是否更新（第10个字符=1）
ver = 2.0

import urequests
import os
import time

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

# 要更新的文件列表
file_map = {
    "main.py": "https://raw.githubusercontent.com/Johnnnyc/ESP32_MiDevice/main/main.py"
}

print("开始批量更新...")

try:
    for filename, url in file_map.items():
        print(f"更新: {filename}")
        # 备份现有文件
        backup_file(filename)
        # 下载新文件
        res = urequests.get(url, timeout=10)
        with open(filename, "wb") as f:
            f.write(res.content)
        res.close()
    print("所有文件更新完成！")
except Exception as e:
    print(f"更新失败: {e}")

# 重启设备
import machine
print("更新完成，正在重启...")
machine.reset()