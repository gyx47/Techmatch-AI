import sys
import chromadb
from chromadb.config import Settings
from pathlib import Path

# 使用和 vector_service.py 完全相同的路径
db_path = Path(__file__).parent.parent / "chroma_db"
print(f"数据库路径: {db_path}")
print(f"路径存在: {db_path.exists()}")

if db_path.exists():
    print("目录内容:")
    for item in db_path.iterdir():
        print(f"  - {item.name}")

# 连接 ChromaDB
client = chromadb.PersistentClient(
    path=str(db_path),
    settings=Settings(anonymized_telemetry=False)
)

print("\n尝试获取 requirements 集合...")
try:
    # 先尝试获取（如果存在）
    req_collection = client.get_collection(name="requirements")
    print(f"✅ 集合已存在，数量: {req_collection.count()}")
except:
    print("集合不存在，尝试创建...")
    try:
        req_collection = client.get_or_create_collection(
            name="requirements",
            metadata={"hnsw:space": "cosine"}
        )
        print(f"✅ 集合创建成功，数量: {req_collection.count()}")
    except Exception as e:
        print(f"❌ 集合创建失败: {e}")
        
print("\n尝试获取 papers 集合...")
try:
    paper_collection = client.get_collection(name="papers")
    print(f"✅ 论文集合数量: {paper_collection.count()}")
except Exception as e:
    print(f"❌ 论文集合获取失败: {e}")
