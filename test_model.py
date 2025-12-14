#!/usr/bin/env python3
import os
import sys
import traceback

print("=" * 60)
print("🧪 开始测试模型完整性")
print("=" * 60)

# 设置环境变量
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_DATASETS_OFFLINE'] = '1'

# 模型路径
model_path = "./models/paraphrase-multilingual-MiniLM-L12-v2"
print(f"📁 模型路径: {model_path}")

# 1. 检查文件是否存在
print("\n1. 📋 检查必要文件...")
required_files = [
    'config.json',
    'pytorch_model.bin',
    'tokenizer_config.json',
    'vocab.txt',
    'sentence_bert_config.json'
]

all_files_ok = True
for file in required_files:
    file_path = os.path.join(model_path, file)
    if os.path.exists(file_path):
        size = os.path.getsize(file_path)
        size_mb = size / (1024 * 1024)
        print(f"   ✓ {file}: {size_mb:.2f} MB")
    else:
        print(f"   ✗ {file}: 不存在！")
        all_files_ok = False

if not all_files_ok:
    print("❌ 缺少必要文件，请重新下载")
    sys.exit(1)

# 2. 检查大模型文件是否完整
print("\n2. 🔍 检查模型文件完整性...")
model_file = os.path.join(model_path, 'pytorch_model.bin')
file_size = os.path.getsize(model_file)
print(f"   文件大小: {file_size / (1024*1024):.2f} MB")

# 尝试读取文件开头和结尾
try:
    with open(model_file, 'rb') as f:
        # 读取文件开头（前100字节）
        f.seek(0)
        header = f.read(100)
        print(f"   ✓ 能读取文件开头")
        
        # 读取文件结尾（最后100字节）
        f.seek(-100, 2)  # 从文件末尾向前100字节
        footer = f.read(100)
        print(f"   ✓ 能读取文件结尾")
        
        if len(header) == 100 and len(footer) == 100:
            print("   ✅ 文件可以完整读取")
        else:
            print("   ⚠️ 文件读取不完整")
except Exception as e:
    print(f"   ❌ 文件读取失败: {e}")
    sys.exit(1)

# 3. 尝试加载模型
print("\n3. 🚀 尝试加载模型...")
try:
    from sentence_transformers import SentenceTransformer
    
    print("   导入库成功，开始加载模型...")
    model = SentenceTransformer(model_path)
    print("   ✅ 模型加载成功！")
    
    # 4. 测试编码功能
    print("\n4. 🧪 测试编码功能...")
    test_texts = [
        "这是一个测试句子",
        "This is a test sentence",
        "机器学习是人工智能的重要分支",
        "深度学习需要大量数据和算力"
    ]
    
    print(f"   测试文本: {test_texts}")
    embeddings = model.encode(test_texts)
    print(f"   ✅ 编码成功！")
    print(f"   向量维度: {embeddings.shape}")
    print(f"   第一个向量样例（前5个值）: {embeddings[0][:5]}")
    
    # 5. 测试相似度计算
    print("\n5. 🔗 测试相似度计算...")
    from sentence_transformers import util
    
    query = "机器学习"
    documents = ["深度学习", "人工智能", "编程语言", "数据科学"]
    
    query_embedding = model.encode(query)
    doc_embeddings = model.encode(documents)
    
    # 计算相似度
    cos_scores = util.cos_sim(query_embedding, doc_embeddings)[0]
    
    print(f"   查询: '{query}'")
    for i, (doc, score) in enumerate(zip(documents, cos_scores)):
        print(f"      {i+1}. '{doc}': 相似度 {score:.4f}")
    
    print("\n" + "=" * 60)
    print("🎉 所有测试通过！模型完全正常")
    print("=" * 60)
    
except ImportError as e:
    print(f"   ❌ 导入失败: {e}")
    print("   请安装: pip install sentence-transformers")
    sys.exit(1)
    
except Exception as e:
    print(f"   ❌ 模型加载或测试失败: {type(e).__name__}")
    print(f"   错误信息: {str(e)[:200]}")
    print("\n🔧 调试信息:")
    traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("⚠️ 模型可能损坏，建议：")
    print("   1. 重新下载模型文件")
    print("   2. 检查内存是否充足（需要1GB+空闲内存）")
    print("   3. 换用更小的模型")
    print("=" * 60)