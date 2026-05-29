"""
SmartQuery 数据库初始化脚本
创建模拟电商数据库并插入示例数据
运行方式：python init_db.py
"""

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, Text

# 创建 SQLite 数据库引擎
engine = create_engine("sqlite:///smartquery.db", echo=True)
metadata = MetaData()

# 定义 users 表
users_table = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", Text, nullable=False),
    Column("city", Text, nullable=False),
    Column("register_date", Text, nullable=False),
)

# 定义 products 表
products_table = Table(
    "products",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", Text, nullable=False),
    Column("category", Text, nullable=False),
    Column("price", Float, nullable=False),
)

# 定义 orders 表
orders_table = Table(
    "orders",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False),
    Column("product_id", Integer, nullable=False),
    Column("amount", Integer, nullable=False),
    Column("order_date", Text, nullable=False),
)

# 创建所有表
metadata.create_all(engine)

# 插入示例数据
with engine.connect() as conn:
    # 插入用户数据
    conn.execute(
        users_table.insert(),
        [
            {"name": "张三", "city": "北京", "register_date": "2024-01-15"},
            {"name": "李四", "city": "上海", "register_date": "2024-02-20"},
            {"name": "王五", "city": "广州", "register_date": "2024-03-10"},
            {"name": "赵六", "city": "深圳", "register_date": "2024-04-05"},
            {"name": "孙七", "city": "杭州", "register_date": "2024-05-18"},
            {"name": "周八", "city": "北京", "register_date": "2024-06-22"},
        ],
    )

    # 插入产品数据
    conn.execute(
        products_table.insert(),
        [
            {"name": "智能手机", "category": "数码", "price": 4999.00},
            {"name": "笔记本电脑", "category": "数码", "price": 7999.00},
            {"name": "运动跑鞋", "category": "运动", "price": 599.00},
            {"name": "Java编程思想", "category": "图书", "price": 99.00},
            {"name": "无线耳机", "category": "数码", "price": 899.00},
            {"name": "瑜伽垫", "category": "运动", "price": 129.00},
            {"name": "Python深度学习", "category": "图书", "price": 79.00},
        ],
    )

    # 插入订单数据
    conn.execute(
        orders_table.insert(),
        [
            {"user_id": 1, "product_id": 1, "amount": 1, "order_date": "2024-03-01"},
            {"user_id": 1, "product_id": 5, "amount": 2, "order_date": "2024-03-15"},
            {"user_id": 2, "product_id": 2, "amount": 1, "order_date": "2024-04-10"},
            {"user_id": 2, "product_id": 3, "amount": 2, "order_date": "2024-04-20"},
            {"user_id": 3, "product_id": 4, "amount": 3, "order_date": "2024-05-05"},
            {"user_id": 3, "product_id": 6, "amount": 1, "order_date": "2024-05-12"},
            {"user_id": 4, "product_id": 1, "amount": 1, "order_date": "2024-06-01"},
            {"user_id": 4, "product_id": 3, "amount": 2, "order_date": "2024-06-18"},
            {"user_id": 5, "product_id": 5, "amount": 1, "order_date": "2024-07-03"},
            {"user_id": 5, "product_id": 7, "amount": 4, "order_date": "2024-07-22"},
            {"user_id": 6, "product_id": 2, "amount": 1, "order_date": "2024-08-08"},
            {"user_id": 6, "product_id": 6, "amount": 1, "order_date": "2024-08-15"},
        ],
    )

    conn.commit()

print("数据库初始化完成！已创建 smartquery.db，包含 users、products、orders 三张表及示例数据。")
