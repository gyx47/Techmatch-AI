"""
向量化服务 - 使用 Sentence-Transformers 和 ChromaDB
"""
import logging
import os
from typing import List, Dict, Tuple
from pathlib import Path

# 在导入任何库之前设置环境变量，禁用 TensorFlow
# 这可以避免 transformers 库尝试加载 TensorFlow
os.environ.setdefault('TRANSFORMERS_NO_TF', '1')  # 禁用 TensorFlow
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')  # 禁用 TensorFlow 日志

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self):
        """初始化向量服务"""
        # 延迟导入 SentenceTransformer，避免启动时加载
        self.model = None
        self._model_name = 'paraphrase-multilingual-MiniLM-L12-v2'
        
        # 初始化 ChromaDB
        db_path = Path(__file__).parent.parent.parent / "chroma_db"
        db_path.mkdir(exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=str(db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name="papers",
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("ChromaDB 连接成功")
    
    def _load_model(self):
        """延迟加载模型"""
        if self.model is None:
            try:
                # 确保环境变量已设置（防止被其他代码修改）
                os.environ['TRANSFORMERS_NO_TF'] = '1'
                os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
                
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(self._model_name)
                logger.info("向量模型加载完成")
            except ImportError as e:
                logger.error(f"无法导入 sentence_transformers: {e}")
                raise ImportError(
                    "请安装 sentence-transformers: pip install sentence-transformers"
                )
            except Exception as e:
                # 处理其他加载错误（如 TensorFlow DLL 问题）
                error_msg = str(e)
                if 'DLL load failed' in error_msg or 'tensorflow' in error_msg.lower():
                    logger.error("=" * 60)
                    logger.error("向量模型加载失败：TensorFlow DLL 问题")
                    logger.error("=" * 60)
                    logger.error("")
                    logger.error("虽然已设置 TRANSFORMERS_NO_TF=1，但 transformers 库仍尝试加载 TensorFlow")
                    logger.error("")
                    logger.error("解决方案：")
                    logger.error("  1. 安装 Visual C++ Redistributable（推荐）")
                    logger.error("     下载: https://aka.ms/vs/17/release/vc_redist.x64.exe")
                    logger.error("  2. 重新安装 tensorflow-cpu:")
                    logger.error("     pip uninstall tensorflow tensorflow-cpu")
                    logger.error("     pip install tensorflow-cpu")
                    logger.error("  3. 使用 conda 安装（最稳定）:")
                    logger.error("     conda install tensorflow-cpu")
                    logger.error("  4. 或者降级 transformers 版本:")
                    logger.error("     pip install transformers==4.30.0")
                    logger.error("=" * 60)
                    raise RuntimeError(
                        "向量模型加载失败，请检查 TensorFlow 环境配置。"
                        "详细错误: " + error_msg
                    )
                raise
    
    def embed_text(self, text: str) -> List[float]:
        """将文本转换为向量"""
        self._load_model()
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def add_paper(self, paper_id: str, title: str, abstract: str) -> bool:
        """
        将论文添加到向量数据库
        paper_id: 论文ID（如 arxiv_id 或数据库主键）
        title: 论文标题
        abstract: 论文摘要
        返回: True 如果成功添加，False 如果已存在
        """
        try:
            # 先检查是否已存在
            try:
                results = self.collection.get(ids=[paper_id])
                if results and results.get('ids') and len(results['ids']) > 0:
                    logger.debug(f"论文 {paper_id} 已存在于向量数据库，跳过")
                    return False
            except Exception:
                pass  # 不存在，继续添加
            
            # 组合标题和摘要作为待向量化的文本
            text = f"{title}\n{abstract}"
            
            # 生成向量
            embedding = self.embed_text(text)
            
            # 存储到 ChromaDB
            self.collection.add(
                embeddings=[embedding],
                ids=[paper_id],
                metadatas=[{
                    "title": title,
                    "abstract": abstract[:500]  # 限制摘要长度
                }]
            )
            
            logger.debug(f"论文 {paper_id} 已添加到向量数据库")
            return True
            
        except Exception as e:
            logger.error(f"添加论文 {paper_id} 到向量数据库失败: {str(e)}")
            raise
    
    def search_similar(self, query_text: str, top_k: int = 50) -> List[Tuple[str, float]]:
        """
        搜索相似论文
        返回: [(paper_id, similarity_score), ...]
        """
        try:
            # 将查询文本转换为向量
            query_embedding = self.embed_text(query_text)
            
            # 在 ChromaDB 中搜索
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            # 提取结果
            paper_ids = results['ids'][0]
            distances = results['distances'][0]
            
            # 将距离转换为相似度分数（cosine distance -> similarity）
            # cosine distance = 1 - cosine similarity
            similarities = [(pid, 1 - dist) for pid, dist in zip(paper_ids, distances)]
            
            logger.info(f"找到 {len(similarities)} 篇相似论文")
            
            return similarities
            
        except Exception as e:
            logger.error(f"向量搜索失败: {str(e)}")
            raise
    
    def get_paper_count(self) -> int:
        """获取向量数据库中的论文数量"""
        return self.collection.count()

# 全局单例
_vector_service = None

def get_vector_service() -> VectorService:
    """获取向量服务单例"""
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorService()
    return _vector_service

