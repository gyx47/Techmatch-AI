# run_requirement_indexing.py（或diagnose_chromadb.py）
import sys
from pathlib import Path

def run_indexing():
    print("🚀 开始索引需求数据到向量库...")
    
    # 添加正确的导入路径
    backend_path = Path(__file__).parent / "backend"
    sys.path.insert(0, str(backend_path))
    
    try:
        # 导入索引函数
        from services.vector_service import get_vector_service
        from database.database import get_db_connection
        
        print("✅ 导入成功")
        
        # 获取向量服务
        vector_service = get_vector_service()
        
        # 🔴 第一步：清理旧数据（关键！）
        print("🧹 清理旧向量数据...")
        try:
            # 获取当前向量库中的所有ID
            existing_ids = vector_service.requirement_collection.get()["ids"]
            if existing_ids:
                print(f"   发现 {len(existing_ids)} 个旧记录，正在删除...")
                vector_service.requirement_collection.delete(ids=existing_ids)
                print(f"   ✅ 已清理 {len(existing_ids)} 条旧记录")
            else:
                print("   ✅ 向量库为空，无需清理")
        except Exception as e:
            print(f"   ⚠️  清理时出错: {e}")
        
        # 获取数据库连接
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. 首先检查SQLite中有多少需求
        cursor.execute("SELECT COUNT(*) as count FROM requirements WHERE status = 'active'")
        db_count = cursor.fetchone()['count']
        print(f"\n📊 SQLite数据库中的需求数量: {db_count}")
        
        if db_count == 0:
            print("❌ 数据库中没有需求数据！")
            print("   请先运行: python backend/scripts/create_requirements_service.py")
            return
        
        # 显示一些样本
        cursor.execute("SELECT requirement_id, title, industry FROM requirements LIMIT 5")
        samples = cursor.fetchall()
        print("   样本数据:")
        for req in samples:
            print(f"     - {req['requirement_id']}: {req['title']} [{req['industry']}]")
        
        # 2. 获取所有需求
        cursor.execute("""
            SELECT requirement_id, title, description, industry, pain_points
            FROM requirements 
            WHERE status = 'active'
        """)
        
        requirements = cursor.fetchall()
        conn.close()
        
        print(f"\n📋 准备索引 {len(requirements)} 个需求...")
        
        # 3. 索引每个需求
        indexed_count = 0
        skipped_count = 0
        error_count = 0
        
        for i, req in enumerate(requirements):
            try:
                requirement_id = req["requirement_id"]
                
                print(f"   [{i+1}/{len(requirements)}] 处理: {requirement_id}")
                
                # 准备数据
                title = req["title"] or ""
                description = req["description"] or ""
                industry = req["industry"] or ""
                pain_points = req["pain_points"] or ""
                
                # 使用add_requirement方法
                success = vector_service.add_requirement(
                    requirement_id=requirement_id,
                    title=title,
                    description=description,
                    industry=industry,
                    pain_points=pain_points
                )
                
                if success:
                    indexed_count += 1
                    if indexed_count % 5 == 0:
                        print(f"     ✅ 已成功索引 {indexed_count} 个")
                else:
                    error_count += 1
                    print(f"     ❌ 添加失败")
                    
            except Exception as e:
                error_count += 1
                print(f"     ❌ 处理失败: {str(e)[:100]}")
                continue
        
        # 4. 验证结果
        final_count = vector_service.requirement_collection.count()
        
        print(f"\n🎉 索引完成!")
        print(f"   数据库需求总数: {len(requirements)}")
        print(f"   成功索引: {indexed_count}")
        print(f"   处理失败: {error_count}")
        print(f"   向量库最终数量: {final_count}")
        
        # 5. 测试搜索
        if final_count > 0:
            print(f"\n🧪 测试搜索功能...")
            test_queries = ["人工智能", "大数据", "解决方案", "技术"]
            
            for query in test_queries:
                try:
                    results = vector_service.search_requirements(query, top_k=3)
                    if results:
                        print(f"   搜索 '{query}': 找到 {len(results)} 个结果")
                        for j, (req_id, score) in enumerate(results[:3]):
                            print(f"     {j+1}. {req_id} (相似度: {score:.3f})")
                    else:
                        print(f"   搜索 '{query}': 无结果")
                except Exception as e:
                    print(f"   搜索 '{query}' 失败: {e}")
        
    except Exception as e:
        print(f"❌ 索引过程失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_indexing()