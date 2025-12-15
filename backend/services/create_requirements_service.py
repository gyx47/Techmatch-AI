"""
创建完整的100条需求数据（包含所有必需字段）
"""
import sqlite3
from pathlib import Path
import random
from datetime import datetime, timedelta

DB_PATH = Path(__file__).parent.parent / "database" / "app.db"

def create_complete_requirements():
    """创建完整的100条需求数据"""
    print("🚀 创建100条完整需求数据...")
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        # 先清空表
        cursor.execute("DELETE FROM requirements")
        print("🗑️  已清空旧数据")
        
        # 定义完整的数据模板
        industries = ['人工智能', '大数据', '云计算', '物联网', '区块链', 
                     '金融科技', '医疗健康', '智能制造', '智慧城市', '新能源']
        
        tech_descriptions = {
            '低': ['基础技术实现', '简单系统开发', '标准方案应用'],
            '中': ['系统集成开发', '算法优化实现', '平台级解决方案'],
            '高': ['前沿技术研发', '复杂系统架构', '创新算法设计']
        }
        
        market_descriptions = {
            '小型': ['初创企业市场', '细分垂直领域', '区域性需求'],
            '中型': ['行业解决方案', '中型企业市场', '区域龙头企业'],
            '大型': ['国家级项目', '行业头部客户', '大规模应用场景']
        }
        
        pain_points_templates = [
            "技术更新快，现有系统难以跟上技术发展节奏",
            "数据处理能力不足，无法满足实时分析需求",
            "系统集成困难，不同平台数据无法互通",
            "安全风险高，面临数据泄露和网络攻击威胁",
            "运维成本高昂，需要大量人力维护系统运行",
            "用户体验差，系统响应慢且界面不友好",
            "扩展性差，业务增长后系统无法快速扩容",
            "缺乏专业人才，技术团队能力不足",
            "合规要求严格，需满足行业监管标准",
            "技术债务累积，历史遗留问题难以解决"
        ]
        
        solution_areas = [
            "自动化流程", "智能分析", "实时监控", "预测维护",
            "资源优化", "风险控制", "质量检测", "供应链管理",
            "客户服务", "决策支持", "安全防护", "效率提升"
        ]
        
        inserted_count = 0
        
        for i in range(1, 101):
            requirement_id = f"REQ{i:04d}"
            industry = random.choice(industries)
            tech_level = random.choice(['低', '中', '高'])
            market_size = random.choice(['小型', '中型', '大型'])
            
            # 生成完整的标题和描述
            solution_area = random.choice(solution_areas)
            title = f"{industry}领域的{solution_area}解决方案"
            
            description = f"""
            针对{industry}行业在{solution_area}方面面临的挑战，寻求创新技术解决方案。
            要求能够处理大规模数据，支持实时分析，具备良好的可扩展性和安全性。
            期望通过技术升级，提升业务效率{random.randint(20, 80)}%，降低运营成本{random.randint(15, 50)}%。
            """
            
            # 生成具体的痛点描述
            pain_points = f"""
            1. {random.choice(pain_points_templates)}
            2. {random.choice(pain_points_templates)}
            3. 在{random.choice(['数据采集', '处理分析', '系统集成', '用户交互'])}环节存在瓶颈
            """
            
            # 技术难度描述
            tech_description = random.choice(tech_descriptions[tech_level])
            
            # 市场规模描述
            market_description = random.choice(market_descriptions[market_size])
            
            # 完整的插入语句（包含所有字段）
            try:
                cursor.execute("""
                    INSERT INTO requirements 
                    (requirement_id, title, description, industry, 
                     pain_points, technical_level, market_size,
                     contact_info, published_date, source_url, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    requirement_id,
                    title,
                    description.strip(),
                    industry,
                    pain_points.strip(),
                    tech_level,
                    market_size,
                    f"contact{i:04d}@example.com",
                    (datetime.now() - timedelta(days=random.randint(1, 365))).strftime('%Y-%m-%d'),
                    f"https://example.com/req/{requirement_id}",
                    'active'
                ))
                
                inserted_count += 1
                
                if inserted_count % 20 == 0:
                    print(f"  已插入 {inserted_count} 条...")
                    
            except Exception as e:
                print(f"插入 {requirement_id} 失败: {e}")
                continue
        
        conn.commit()
        print(f"\n✅ 成功插入 {inserted_count} 条完整需求数据")
        
        # 验证数据完整性
        print("\n📊 数据完整性验证:")
        
        # 检查是否有空值
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN pain_points IS NULL OR pain_points = '' THEN 1 ELSE 0 END) as null_pain_points,
                SUM(CASE WHEN technical_level IS NULL OR technical_level = '' THEN 1 ELSE 0 END) as null_tech_level,
                SUM(CASE WHEN market_size IS NULL OR market_size = '' THEN 1 ELSE 0 END) as null_market_size
            FROM requirements
        """)
        
        stats = cursor.fetchone()
        print(f"   总记录数: {stats[0]}")
        print(f"   空痛点描述: {stats[1]}")
        print(f"   空技术难度: {stats[2]}")
        print(f"   空市场规模: {stats[3]}")
        
        # 显示样本
        cursor.execute("""
            SELECT requirement_id, title, industry, technical_level, market_size, 
                   LENGTH(pain_points) as pain_points_length
            FROM requirements 
            ORDER BY requirement_id 
            LIMIT 5
        """)
        
        print("\n📋 样本数据:")
        for row in cursor.fetchall():
            pain_status = "✅" if row[5] > 10 else "❌"
            print(f"  {row[0]}: {row[1][:30]}...")
            print(f"      行业: {row[2]}, 难度: {row[3]}, 规模: {row[4]}, 痛点: {pain_status}")
            
    finally:
        conn.close()

def clear_and_recreate():
    """完整流程：清理并重新创建"""
    print("=" * 60)
    print("🔄 完整需求数据重建流程")
    print("=" * 60)
    
    # 1. 确保表结构完整
    print("\n1. 检查表结构...")
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 确保所有字段都存在
    required_fields = [
        ('pain_points', 'TEXT'),
        ('technical_level', 'VARCHAR(50)'),
        ('market_size', 'VARCHAR(50)'),
        ('contact_info', 'TEXT'),
        ('published_date', 'DATE'),
        ('source_url', 'TEXT'),
        ('status', 'VARCHAR(20)')
    ]
    
    cursor.execute("PRAGMA table_info(requirements)")
    existing_fields = {col[1]: col[2] for col in cursor.fetchall()}
    
    for field_name, field_type in required_fields:
        if field_name not in existing_fields:
            try:
                cursor.execute(f"ALTER TABLE requirements ADD COLUMN {field_name} {field_type}")
                print(f"   ✅ 添加字段: {field_name}")
            except Exception as e:
                print(f"   ⚠️  添加字段 {field_name} 失败: {e}")
    
    conn.commit()
    conn.close()
    
    # 2. 创建完整数据
    create_complete_requirements()
    
    print("\n" + "=" * 60)
    print("🎉 数据重建完成！")
    print("=" * 60)
    print("\n下一步操作:")
    print("1. 运行: python diagnose_chromadb.py  # 将数据索引到向量库")
    print("2. 重启FastAPI服务")
    print("3. 测试成果→需求匹配功能")

if __name__ == "__main__":
    clear_and_recreate()