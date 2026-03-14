#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Firebase数据库查看工具
功能：显示Firebase实时数据库中的所有表和内容
"""

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db


def initialize_firebase():
    """
    初始化Firebase连接
    需要先下载serviceAccountKey.json文件并放入指定路径
    """
    try:
        # 加载服务账号密钥文件
        cred = credentials.Certificate("esp32-sensor-data-ed101-firebase-adminsdk-fbsvc-2eb6b29bcb.json")
        
        # 初始化Firebase应用
        # databaseURL是你的Firebase数据库URL
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://esp32-sensor-data-ed101-default-rtdb.asia-southeast1.firebasedatabase.app'
        })
        print("Firebase初始化成功")
        return True
    except Exception as e:
        print(f"Firebase初始化失败: {e}")
        return False


def display_data(path, data, indent=0):
    """
    递归显示数据结构
    """
    indent_str = "  " * indent
    
    if isinstance(data, dict):
        if path:
            print(f"{indent_str}{path}:")
        for key, value in data.items():
            new_path = f"{path}/{key}" if path else key
            display_data(new_path, value, indent + 1)
    elif isinstance(data, list):
        print(f"{indent_str}{path}:")
        for i, item in enumerate(data):
            new_path = f"{path}[{i}]"
            display_data(new_path, item, indent + 1)
    else:
        print(f"{indent_str}{path}: {data}")


def show_all_tables():
    """
    显示Firebase数据库中的所有表和内容
    """
    try:
        # 获取根引用
        root_ref = db.reference()
        
        # 获取所有数据
        all_data = root_ref.get()
        
        if all_data:
            print("=== Firebase数据库内容 ===")
            display_data("", all_data)
        else:
            print("Firebase数据库为空")
            
    except Exception as e:
        print(f"获取数据失败: {e}")


def show_specific_table(table_name):
    """
    显示指定表的内容
    """
    try:
        # 获取指定表的引用
        table_ref = db.reference(table_name)
        
        # 获取表数据
        table_data = table_ref.get()
        
        if table_data:
            print(f"=== 表 '{table_name}' 的内容 ===")
            display_data(table_name, table_data)
        else:
            print(f"表 '{table_name}' 为空或不存在")
            
    except Exception as e:
        print(f"获取表数据失败: {e}")


def list_tables():
    """
    列出所有表名
    """
    try:
        # 获取根引用
        root_ref = db.reference()
        
        # 获取所有数据
        all_data = root_ref.get()
        
        if all_data:
            print("=== Firebase数据库表列表 ===")
            tables = list(all_data.keys())
            for i, table in enumerate(tables, 1):
                print(f"{i}. {table}")
            return tables
        else:
            print("Firebase数据库为空，没有表")
            return []
            
    except Exception as e:
        print(f"获取表列表失败: {e}")
        return []


def check_recent_data():
    """
    检查最近的数据
    """
    try:
        # 检查data表的时间戳
        data_ref = db.reference('data')
        data = data_ref.get()
        if data and 'time' in data:
            print(f"\n=== 最新数据时间 ===")
            print(f"data表最新时间: {data['time']}")
        
        # 检查sensor-data表的最新记录
        sensor_data_ref = db.reference('sensor-data')
        sensor_data = sensor_data_ref.get()
        if sensor_data:
            # 获取所有时间戳并排序
            timestamps = list(sensor_data.keys())
            timestamps.sort(reverse=True)
            if timestamps:
                latest_timestamp = timestamps[0]
                latest_data = sensor_data[latest_timestamp]
                print(f"\n=== sensor-data表最新记录 ===")
                print(f"最新时间戳: {latest_timestamp}")
                if 'datetime' in latest_data:
                    print(f"最新日期时间: {latest_data['datetime']}")
                if 'temperature' in latest_data:
                    print(f"最新温度: {latest_data['temperature']}")
                if 'humidity' in latest_data:
                    print(f"最新湿度: {latest_data['humidity']}")
    except Exception as e:
        print(f"检查最近数据失败: {e}")

if __name__ == "__main__":
    # 初始化Firebase
    if initialize_firebase():
        print("\n1. 列出所有表")
        tables = list_tables()
        
        print("\n2. 显示所有表的内容")
        show_all_tables()
        
        # 如果有表，显示第一个表的详细内容
        if tables:
            print(f"\n3. 显示表 '{tables[0]}' 的详细内容")
            show_specific_table(tables[0])
        
        # 检查最近的数据
        check_recent_data()
