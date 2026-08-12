"""初始化示例数据库 - 创建表并插入测试数据"""

import os
import sys

# 将项目根目录加入 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

# 确保 data 目录存在
os.makedirs("data", exist_ok=True)

engine = create_engine("sqlite:///./data/demo.db", echo=True)

# 创建表
with engine.connect() as conn:
    # 员工表
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            position TEXT NOT NULL,
            salary REAL NOT NULL,
            hire_date TEXT NOT NULL
        )
    """))

    # 部门表
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            manager TEXT NOT NULL,
            budget REAL NOT NULL
        )
    """))

    # 订单表
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            customer_name TEXT NOT NULL,
            product TEXT NOT NULL,
            amount REAL NOT NULL,
            quantity INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """))

    # 插入示例数据
    conn.execute(text("""
        INSERT OR IGNORE INTO departments (id, name, manager, budget) VALUES
        (1, '技术部', '张三', 500000),
        (2, '市场部', '李四', 300000),
        (3, '财务部', '王五', 200000),
        (4, '人事部', '赵六', 150000)
    """))

    conn.execute(text("""
        INSERT OR IGNORE INTO employees (id, name, department, position, salary, hire_date) VALUES
        (1, '张三', '技术部', '技术总监', 35000, '2020-03-15'),
        (2, '李四', '市场部', '市场总监', 30000, '2019-07-01'),
        (3, '王五', '财务部', '财务经理', 25000, '2021-01-10'),
        (4, '赵六', '人事部', 'HR经理', 22000, '2020-11-20'),
        (5, '小明', '技术部', '高级工程师', 28000, '2021-06-01'),
        (6, '小红', '技术部', '工程师', 20000, '2022-03-15'),
        (7, '小华', '市场部', '市场专员', 15000, '2022-08-01'),
        (8, '小李', '财务部', '会计', 18000, '2021-09-10'),
        (9, '小王', '技术部', '实习生', 8000, '2023-07-01'),
        (10, '小张', '市场部', '设计师', 22000, '2022-01-15')
    """))

    conn.execute(text("""
        INSERT OR IGNORE INTO orders (id, customer_name, product, amount, quantity, order_date, status) VALUES
        (1, '客户A', '产品X', 9999, 2, '2024-01-15', '已完成'),
        (2, '客户B', '产品Y', 5999, 1, '2024-01-20', '已完成'),
        (3, '客户C', '产品X', 9999, 3, '2024-02-01', '配送中'),
        (4, '客户A', '产品Z', 2999, 5, '2024-02-10', '已完成'),
        (5, '客户D', '产品Y', 5999, 2, '2024-02-15', '待发货'),
        (6, '客户E', '产品X', 9999, 1, '2024-03-01', '已取消'),
        (7, '客户B', '产品Z', 2999, 4, '2024-03-10', '已完成'),
        (8, '客户F', '产品Y', 5999, 2, '2024-03-15', '配送中')
    """))

    conn.commit()

print("✅ 示例数据库初始化完成！")
print("   - employees: 10 条记录")
print("   - departments: 4 条记录")
print("   - orders: 8 条记录")
