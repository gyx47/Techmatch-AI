"""
向量化服务 - 使用 Sentence-Transformers 和 ChromaDB
"""
import logging
from typing import List, Dict, Tuple
import chromadb
from chromadb.config import Settings
from pathlib import Path

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
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(self._model_name)
                logger.info("向量模型加载完成")
            except ImportError as e:
                logger.error(f"无法导入 sentence_transformers: {e}")
                raise ImportError(
                    "请安装 sentence-transformers: pip install sentence-transformers"
                )
    
    def embed_text(self, text: str) -> List[float]:
        """将文本转换为向量"""
        self._load_model()
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def add_paper(self, paper_id: str, title: str, abstract: str):
        """
        将论文添加到向量数据库
        paper_id: 论文ID（如 arxiv_id 或数据库主键）
        title: 论文标题
        abstract: 论文摘要
        """
        try:
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
            
            logger.info(f"论文 {paper_id} 已添加到向量数据库")
            
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

