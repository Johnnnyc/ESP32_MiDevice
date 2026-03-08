import requests
import json
import time
from secret import FIREBASE_URL, FIREBASE_API_KEY

def push_data_to_firebase(data):
    """推送数据到Firebase"""
    try:
        print("正在推送数据到Firebase...")
        url = f"{FIREBASE_URL}/data.json"
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=data, headers=headers)
        print(f"Firebase推送成功: {response.status_code}")
        print(f"响应内容: {response.text}")
        return True
    except Exception as e:
        print(f"Firebase推送失败: {e}")
        return False

def get_data_from_firebase():
    """从Firebase读取数据"""
    try:
        print("正在从Firebase读取数据...")
        url = f"{FIREBASE_URL}/data.json"
        response = requests.get(url)
        print(f"Firebase读取成功: {response.status_code}")
        data = response.json()
        print(f"读取到的数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
        return data
    except Exception as e:
        print(f"Firebase读取失败: {e}")
        return None

def generate_test_data():
    """生成测试数据"""
    # 生成模拟的温湿度数据
    import random
    temperature = round(random.uniform(20, 30), 1)
    humidity = round(random.uniform(40, 70), 1)
    current_time = time.localtime()
    time_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        current_time[0], current_time[1], current_time[2],
        current_time[3], current_time[4], current_time[5]
    )
    
    data = {
        'temperature': temperature,
        'humidity': humidity,
        'datetime': time_str
    }
    return data

def main():
    print("Firebase数据库测试程序")
    print("=" * 50)
    print(f"Firebase URL: {FIREBASE_URL}")
    print("=" * 50)
    
    while True:
        print("\n请选择操作:")
        print("1. 推送测试数据到Firebase")
        print("2. 从Firebase读取数据")
        print("3. 退出")
        
        choice = input("请输入选项 (1-3): ")
        
        if choice == "1":
            # 生成测试数据
            test_data = generate_test_data()
            print(f"\n生成的测试数据: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
            # 推送数据
            push_data_to_firebase(test_data)
        elif choice == "2":
            # 读取数据
            get_data_from_firebase()
        elif choice == "3":
            print("退出程序...")
            break
        else:
            print("无效的选项，请重新输入")

if __name__ == "__main__":
    main()
