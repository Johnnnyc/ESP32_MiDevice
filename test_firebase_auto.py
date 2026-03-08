import requests
import json
import time
import random
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
    print("Firebase数据库自动测试程序")
    print("=" * 50)
    print(f"Firebase URL: {FIREBASE_URL}")
    print("=" * 50)
    
    # 步骤1：推送测试数据
    print("\n步骤1: 推送测试数据到Firebase")
    test_data = generate_test_data()
    print(f"生成的测试数据: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
    push_data_to_firebase(test_data)
    
    # 等待1秒
    time.sleep(1)
    
    # 步骤2：读取数据
    print("\n步骤2: 从Firebase读取数据")
    get_data_from_firebase()
    
    print("\n测试完成!")

if __name__ == "__main__":
    main()
