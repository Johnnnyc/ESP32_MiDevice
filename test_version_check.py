import requests
import json
from config import FIRMWARE_VERSION, GITHUB_API_URL

def get_latest_version():
    """从GitHub获取最新版本信息"""
    try:
        print("正在检查GitHub最新版本...")
        response = requests.get(GITHUB_API_URL)
        if response.status_code == 200:
            data = response.json()
            latest_version = data.get("tag_name", "")
            # 移除可能的"v"前缀
            if latest_version.startswith("v"):
                latest_version = latest_version[1:]
            print(f"GitHub最新版本: {latest_version}")
            return latest_version
        else:
            print(f"获取GitHub版本失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"获取GitHub版本异常: {e}")
        return None

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

def check_for_updates():
    """检查是否有版本更新"""
    current_version = FIRMWARE_VERSION
    print(f"当前固件版本: {current_version}")
    
    latest_version = get_latest_version()
    if latest_version:
        comparison = compare_versions(latest_version, current_version)
        if comparison > 0:
            print(f"发现新版本: {latest_version}")
            return latest_version
        else:
            print("当前已是最新版本")
            return None
    return None

def main():
    print("版本更新检查测试程序")
    print("=" * 50)
    print(f"当前版本: {FIRMWARE_VERSION}")
    print(f"GitHub API URL: {GITHUB_API_URL}")
    print("=" * 50)
    
    # 检查版本更新
    check_for_updates()
    
    print("\n测试完成!")

if __name__ == "__main__":
    main()
