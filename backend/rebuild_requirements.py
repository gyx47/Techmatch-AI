import sys
from pathlib import Path
import chromadb
from chromadb.config import Settings
import time

# 路径
db_path = Path(__file__).parent.parent / "chroma_db"
print(f"数据库路径: {db_path}")

# 确保目录存在
db_path.mkdir(exist_ok=True, parents=True)

# 连接
client = chromadb.PersistentClient(
    path=str(db_path),
    settings=Settings(anonymized_telemetry=False)
)

print("1. 删除旧的 requirements 集合...")
try:
    client.delete_collection(name="requirements")
    print("   ✅ 已删除")
    time.sleep(0.5)
except Exception as e:
    print(f"   ℹ️ 删除时: {e}")

print("\n2. 创建新的 requirements 集合...")
try:
    req_collection = client.create_collection(
        name="requirements",
        metadata={"hnsw:space": "cosine"}
    )
    print(f"   ✅ 创建成功")
except Exception as e:
    print(f"   ❌ 创建失败: {e}")
    # 尝试另一种方式
    try:
        req_collection = client.get_or_create_collection(
            name="requirements",
            metadata={"hnsw:space": "cosine"}
        )
        print(f"   ✅ 使用 get_or_create 成功")
    except Exception as e2:
        print(f"   ❌ 完全失败: {e2}")
        sys.exit(1)

print(f"\n3. 验证集合...")
print(f"   集合名称: {req_collection.name}")
print(f"   初始数量: {req_collection.count()}")

print("\n4. 添加一个测试向量...")
try:
    # 添加一个简单的测试数据
    req_collection.add(
        embeddings=[[0.1] * 384],  # 384维的简单向量（根据你的模型维度）
        ids=["test_requirement_001"],
        metadatas=[{
            "title": "测试需求",
            "description": "这是一个测试需求",
            "industry": "测试行业",
            "status": "active"
        }]
    )
    print(f"   ✅ 测试数据添加成功")
    print(f"   新数量: {req_collection.count()}")
except Exception as e:
    print(f"   ❌ 添加测试数据失败: {e}")

print("\n✅ 重建完成!")
