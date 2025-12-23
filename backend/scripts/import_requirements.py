"""
导入需求数据到数据库并向量化
专门用于导入生成的requirements.json文件
"""
import json
import sqlite3
from pathlib import Path
import sys
import io

# Windows编码与实时输出修复
if sys.platform == 'win32':
    # 包一层确保中文不报错
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    # 尝试开启行缓冲/及时刷新，避免所有日志在结束时一次性输出
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        # 低版本 Python 没有 reconfigure 就忽略
        pass

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "database" / "app.db"

# 导入向量服务
try:
    from services.vector_service import get_vector_service
    VECTOR_SERVICE_AVAILABLE = True
except ImportError as e:
    print(f"[警告] 无法导入向量服务: {e}")
    VECTOR_SERVICE_AVAILABLE = False

def import_requirements_from_json(json_file: str, clear_existing: bool = False, vectorize: bool = True):
    """
    从JSON文件导入需求数据到数据库并向量化
    
    Args:
        json_file: JSON文件路径
        clear_existing: 是否清空现有数据（默认False）
        vectorize: 是否进行向量化（默认True）
    """
    json_path = Path(json_file)
    if not json_path.is_absolute():
        json_path = Path(__file__).parent.parent / json_file
    
    if not json_path.exists():
        print(f"[错误] JSON文件不存在: {json_path}")
        return
    
    print(f"[开始] 从JSON文件导入需求数据...")
    print(f"[文件] {json_path}")
    
    # 读取JSON文件
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            requirements = json.load(f)
        print(f"[读取] 成功读取 {len(requirements)} 条需求数据")
    except Exception as e:
        print(f"[错误] 读取JSON文件失败: {e}")
        return
    
    # 连接数据库
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # 使结果可以按列名访问
    cursor = conn.cursor()
    
    try:
        # 可选：清空现有数据
        if clear_existing:
            cursor.execute("DELETE FROM requirements WHERE source = 'ai_generated'")
            deleted = cursor.rowcount
            print(f"[清理] 已删除 {deleted} 条现有AI生成的需求")
            conn.commit()
        
        # 导入数据
        inserted = 0
        skipped = 0
        errors = 0
        
        for req in requirements:
            try:
                # 处理 pain_points：如果是列表则转换为字符串
                pain_points = req.get("pain_points", "")
                if isinstance(pain_points, list):
                    pain_points = "\n".join(str(item) for item in pain_points)
                elif pain_points is None:
                    pain_points = ""
                else:
                    pain_points = str(pain_points)
                
                # 确保其他字段也是字符串类型
                requirement_id = str(req.get("requirement_id", ""))
                title = str(req.get("title", ""))
                description = str(req.get("description", ""))
                industry = str(req.get("industry", ""))
                technical_level = str(req.get("technical_level", "")) if req.get("technical_level") else None
                market_size = str(req.get("market_size", "")) if req.get("market_size") else None
                
                # 处理contact_info：如果存在分开的字段，则合并
                contact_info = str(req.get("contact_info", ""))
                if not contact_info and (req.get("contact_name") or req.get("contact_phone") or req.get("contact_email")):
                    contact_info_parts = []
                    if req.get("contact_name"):
                        contact_info_parts.append(f"联系人: {req.get('contact_name')}")
                    if req.get("contact_phone"):
                        contact_info_parts.append(f"电话: {req.get('contact_phone')}")
                    if req.get("contact_email"):
                        contact_info_parts.append(f"邮箱: {req.get('contact_email')}")
                    contact_info = "; ".join(contact_info_parts)
                
                status = str(req.get("status", "active"))
                source = str(req.get("source", "ai_generated"))
                created_at = str(req.get("created_at", ""))
                
                # 检查是否已存在
                cursor.execute("SELECT id FROM requirements WHERE requirement_id = ?", (requirement_id,))
                existing = cursor.fetchone()
                
                if existing:
                    # 更新现有记录
                    cursor.execute("""
                        UPDATE requirements 
                        SET title = ?, description = ?, industry = ?, pain_points = ?,
                            technical_level = ?, market_size = ?, contact_info = ?,
                            status = ?, source = ?, created_at = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE requirement_id = ?
                    """, (
                        title, description, industry, pain_points,
                        technical_level, market_size, contact_info,
                        status, source, created_at, requirement_id
                    ))
                    skipped += 1
                else:
                    # 插入新记录
                    cursor.execute("""
                        INSERT INTO requirements 
                        (requirement_id, title, description, industry, pain_points,
                         technical_level, market_size, contact_info, status, source, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        requirement_id,
                        title,
                        description,
                        industry,
                        pain_points,
                        technical_level,
                        market_size,
                        contact_info,
                        status,
                        source,
                        created_at
                    ))
                    inserted += 1
                    
            except sqlite3.Error as e:
                print(f"  [错误] 处理需求 {req.get('requirement_id', 'unknown')} 失败: {e}")
                errors += 1
            except Exception as e:
                print(f"  [错误] 处理需求 {req.get('requirement_id', 'unknown')} 时出错: {e}")
                errors += 1
        
        conn.commit()
        
        print(f"\n[完成] 导入完成！")
        print(f"  - 新增: {inserted} 条")
        print(f"  - 更新: {skipped} 条")
        print(f"  - 错误: {errors} 条")
        print(f"  - 总计: {inserted + skipped} 条成功")
        
        # 向量化导入的需求
        if vectorize and VECTOR_SERVICE_AVAILABLE and (inserted > 0 or skipped > 0):
            print(f"\n[向量化] 开始向量化需求数据...")
            print(f"[向量化] 正在初始化向量检索服务（如果是首次加载模型，可能需要一点时间）...")
            try:
                vector_service = get_vector_service()
                print(f"[向量化] 向量检索服务初始化完成，开始写入向量...")
                
                # 获取所有导入的需求（包括新增和更新的）
                imported_ids = []
                for req in requirements:
                    req_id = str(req.get("requirement_id", ""))
                    if req_id:
                        imported_ids.append(req_id)
                
                # 从数据库获取这些需求的完整信息
                if imported_ids:
                    placeholders = ",".join(["?"] * len(imported_ids))
                    cursor.execute(f"""
                        SELECT requirement_id, title, description, industry, pain_points
                        FROM requirements 
                        WHERE requirement_id IN ({placeholders}) AND status = 'active'
                    """, imported_ids)
                    
                    reqs_to_vectorize = cursor.fetchall()
                    
                    print(f"  准备向量化 {len(reqs_to_vectorize)} 个需求...")
                    
                    vectorized_count = 0
                    vectorize_errors = 0
                    
                    for i, req_row in enumerate(reqs_to_vectorize):
                        try:
                            requirement_id = req_row["requirement_id"]
                            title = req_row["title"] or ""
                            description = req_row["description"] or ""
                            industry = req_row["industry"] or ""
                            pain_points = req_row["pain_points"] or ""
                            
                            # 向量化
                            success = vector_service.add_requirement(
                                requirement_id=requirement_id,
                                title=title,
                                description=description,
                                industry=industry,
                                pain_points=pain_points
                            )
                            
                            if success:
                                vectorized_count += 1
                                if vectorized_count % 5 == 0:
                                    print(f"    [进度] 已向量化 {vectorized_count}/{len(reqs_to_vectorize)} 个")
                            else:
                                vectorize_errors += 1
                                print(f"    [错误] 向量化失败: {requirement_id}")
                                
                        except Exception as e:
                            vectorize_errors += 1
                            req_id = req_row['requirement_id'] if 'requirement_id' in req_row.keys() else 'unknown'
                            print(f"    [错误] 向量化 {req_id} 失败: {e}")
                            continue
                    
                    # 验证向量化结果
                    final_count = vector_service.requirement_collection.count()
                    
                    print(f"\n[向量化完成]")
                    print(f"  - 成功向量化: {vectorized_count} 条")
                    print(f"  - 向量化失败: {vectorize_errors} 条")
                    print(f"  - 向量库总数量: {final_count} 条")
                    
            except Exception as e:
                print(f"[错误] 向量化过程出错: {e}")
                import traceback
                traceback.print_exc()
        elif not VECTOR_SERVICE_AVAILABLE:
            print(f"\n[跳过] 向量服务不可用，跳过向量化步骤")
        elif not vectorize:
            print(f"\n[跳过] 已通过参数关闭向量化（--no-vectorize），仅完成数据导入")
        
    except Exception as e:
        print(f"[错误] 导入过程出错: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="导入需求数据到数据库")
    parser.add_argument("--file", type=str, default="requirements.json", help="JSON文件路径（默认requirements.json）")
    parser.add_argument("--clear", action="store_true", help="清空现有AI生成的需求数据")
    parser.add_argument("--no-vectorize", action="store_true", help="跳过向量化步骤")
    
    args = parser.parse_args()
    
    import_requirements_from_json(
        args.file, 
        clear_existing=args.clear,
        vectorize=not args.no_vectorize
    )

