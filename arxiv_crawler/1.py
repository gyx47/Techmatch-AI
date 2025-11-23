import sqlite3
import pandas as pd

def explore_papers_db(db_path):
    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=== papers.db 数据库信息 ===")
    
    # 查看所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print(f"\n找到 {len(tables)} 个表:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # 详细查看每个表
    for table in tables:
        table_name = table[0]
        print(f"\n=== 表: {table_name} ===")
        
        # 获取表结构
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print("表结构:")
        for col in columns:
            print(f"  {col[0]}: {col[1]} ({col[2]})")
        
        # 获取数据行数
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"数据行数: {count}")
        
        # 显示前几行数据
        if count > 0:
            print("前5行数据:")
            df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 5", conn)
            print(df)
            print("\n" + "="*50)
            print(df.columns)
    
    conn.close()

# 使用
explore_papers_db('papers.db')