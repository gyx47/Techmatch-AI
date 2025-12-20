"""
向量化服务 - 使用 Sentence-Transformers 和 ChromaDB
"""

import logging
import os
# 在导入任何库之前设置环境变量，禁用 TensorFlow
# 这可以避免 transformers 库尝试加载 TensorFlow
os.environ.setdefault('TRANSFORMERS_NO_TF', '1')  # 禁用 TensorFlow
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')  # 禁用 TensorFlow 日志

from typing import List, Dict, Tuple
from pathlib import Path


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

        # 原有的论文集合
        self.paper_collection = self.client.get_or_create_collection(
            name="papers",
            metadata={"hnsw:space": "cosine"}
        )
        
        # 新增需求集合
        self.requirement_collection = self.client.get_or_create_collection(
            name="requirements",
            metadata={"hnsw:space": "cosine"}
        )
        
        # 获取或创建集合
        try:
            self.collection = self.client.get_or_create_collection(
                name="papers",
                metadata={"hnsw:space": "cosine"}
            )
            # 尝试检查集合状态（验证是否可用）
            try:
                count = self.collection.count()
                logger.info(f"ChromaDB 连接成功，集合中有 {count} 篇论文")
            except Exception as check_err:
                error_msg = str(check_err)
                # 检测数据库结构不兼容错误
                if 'no such column' in error_msg.lower() or 'collections.topic' in error_msg:
                    logger.error("=" * 60)
                    logger.error("警告：ChromaDB 数据库结构不兼容")
                    logger.error("=" * 60)
                    logger.error("这通常是因为 ChromaDB 版本升级导致的")
                    logger.error("")
                    logger.error("解决方案（保留数据）：")
                    logger.error("  运行迁移脚本: python backend/scripts/migrate_chromadb.py")
                    logger.error("  此脚本会导出数据、修复结构、重新导入数据")
                    logger.error("")
                    logger.error("或者（会丢失数据）：")
                    logger.error(f"  删除目录: {db_path}")
                    logger.error("  然后重新运行索引任务")
                    logger.error("=" * 60)
                    # 不自动删除，让用户选择运行迁移脚本
                    raise RuntimeError(
                        "ChromaDB 数据库结构不兼容。请运行迁移脚本: python backend/scripts/migrate_chromadb.py"
                    )
                elif 'Cannot open header file' in error_msg or 'header file' in error_msg.lower():
                    logger.error("=" * 60)
                    logger.error("警告：ChromaDB 集合已损坏，无法读取")
                    logger.error("=" * 60)
                    logger.error("请运行修复脚本: python backend/scripts/fix_chromadb.py")
                    logger.error("或手动删除 chroma_db 目录后重新索引")
                    logger.error("=" * 60)
                    # 不抛出异常，允许服务启动，但搜索时会失败
                else:
                    logger.warning(f"无法检查集合状态: {check_err}")
        except Exception as e:
            error_msg = str(e)
            # 检测数据库结构不兼容错误
            if 'no such column' in error_msg.lower() or 'collections.topic' in error_msg:
                logger.error("=" * 60)
                logger.error("初始化 ChromaDB 集合失败：数据库结构不兼容")
                logger.error("=" * 60)
                logger.error("这通常是因为 ChromaDB 版本升级导致的")
                logger.error("")
                logger.error("解决方案（保留数据）：")
                logger.error("  1. 停止服务")
                logger.error("  2. 运行迁移脚本: python backend/scripts/migrate_chromadb.py")
                logger.error("  3. 重启服务")
                logger.error("")
                logger.error("或者（会丢失数据）：")
                logger.error(f"  1. 停止服务")
                logger.error(f"  2. 删除目录: {db_path}")
                logger.error(f"  3. 重启服务（会自动创建新目录）")
                logger.error(f"  4. 运行索引任务重新索引论文")
                logger.error("=" * 60)
                raise RuntimeError(
                    "ChromaDB 数据库结构不兼容。请运行迁移脚本: python backend/scripts/migrate_chromadb.py"
                )
            else:
                logger.error(f"初始化 ChromaDB 集合失败: {e}")
                raise
    
    def _load_model(self):
        """延迟加载模型"""
        if self.model is None:
            try:
                # 确保环境变量已设置（防止被其他代码修改）
                os.environ['TRANSFORMERS_NO_TF'] = '1'
                os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
                
                from sentence_transformers import SentenceTransformer
                logger.info(f"开始加载向量模型: {self._model_name} (延迟加载)")
                self.model = SentenceTransformer(self._model_name)
                logger.info(f"向量模型加载完成: {self._model_name}")
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
        else:
            logger.debug(f"向量模型已加载，跳过加载步骤")
    
    def embed_text(self, text: str) -> List[float]:
        """将文本转换为向量"""
        self._load_model()  # 如果模型未加载，这里会加载
        embedding = self.model.encode(text, convert_to_numpy=True, show_progress_bar=False)
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
                    "abstract": abstract[:1500]  # 限制摘要长度
                }]
            )
            
            logger.debug(f"论文 {paper_id} 已添加到向量数据库")
            return True
            
        except Exception as e:
            logger.error(f"添加论文 {paper_id} 到向量数据库失败: {str(e)}")
            raise

    def add_requirement(self, requirement_id: str, title: str, description: str, 
                       industry: str = "", pain_points: str = "") -> bool:
        """
        将需求添加到向量数据库
        """
        try:
            # 组合文本：标题 + 描述 + 行业 + 痛点
            text = f"{title}\n{description}\n行业:{industry}\n痛点:{pain_points}"
            
            # 生成向量
            embedding = self.embed_text(text)
            
            # 存储到需求集合
            self.requirement_collection.add(
                embeddings=[embedding],
                ids=[requirement_id],
                metadatas=[{
                    "title": title,
                    "description": description[:500],
                    "industry": industry,
                    "status": "active",
                    "type": "requirement"
                }]
            )
            return True
        except Exception as e:
            logger.error(f"添加需求失败: {e}")
            return False
    
    def add_achievement(self, achievement_id: int, name: str, description: str, application: str = None, field: str = None) -> bool:
        """
        将发布的成果添加到向量数据库（与论文共用同一个 collection）
        achievement_id: 成果的数据库ID
        name: 成果名称
        description: 成果描述
        application: 应用场景（可选）
        field: 技术领域（可选）
        返回: True 如果成功添加，False 如果已存在
        """
        try:
            # 使用前缀避免与论文ID冲突
            vector_id = f"achievement_{achievement_id}"
            
            # 先检查是否已存在
            try:
                results = self.collection.get(ids=[vector_id])
                if results and results.get('ids') and len(results['ids']) > 0:
                    logger.debug(f"成果 {achievement_id} 已存在于向量数据库，跳过")
                    return False
            except Exception:
                pass  # 不存在，继续添加
            
            # 组合文本：名称 + 描述 + 应用场景 + 技术领域
            text_parts = [name]
            if description:
                text_parts.append(description)
            if application:
                text_parts.append(application)
            if field:
                text_parts.append(field)  # 包含技术领域
            text = "\n".join(text_parts)
            
            # 生成向量
            embedding = self.embed_text(text)
            
            # 存储到 ChromaDB（与论文共用同一个 collection）
            self.collection.add(
                embeddings=[embedding],
                ids=[vector_id],
                metadatas=[{
                    "type": "achievement",
                    "name": name,
                    "description": description[:1500] if description else "",
                    "application": application[:500] if application else "",
                    "field": field if field else ""
                }]
            )
            
            logger.info(f"成果 {achievement_id} 已添加到向量数据库")
            return True
            
        except Exception as e:
            logger.error(f"添加成果 {achievement_id} 到向量数据库失败: {str(e)}")
            raise
    
    def delete_achievement(self, achievement_id: int) -> bool:
        """
        从向量数据库删除成果
        achievement_id: 成果的数据库ID
        返回: True 如果成功删除，False 如果不存在
        """
        try:
            vector_id = f"achievement_{achievement_id}"
            self.collection.delete(ids=[vector_id])
            logger.info(f"成果 {achievement_id} 已从向量数据库删除")
            return True
        except Exception as e:
            logger.warning(f"删除成果 {achievement_id} 从向量数据库失败（可能不存在）: {str(e)}")
            return False
    
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
            error_msg = str(e)
            logger.error(f"向量搜索失败: {error_msg}")
            
            # 检查是否是 ChromaDB 索引文件损坏的错误
            if 'Cannot open header file' in error_msg or 'header file' in error_msg.lower():
                logger.error("=" * 60)
                logger.error("检测到 ChromaDB 索引文件损坏错误")
                logger.error("=" * 60)
                logger.error("")
                logger.error("可能的原因：")
                logger.error("  1. ChromaDB 数据库文件损坏")
                logger.error("  2. HNSW 索引文件损坏")
                logger.error("  3. ChromaDB 版本不兼容")
                logger.error("  4. 数据库文件被其他进程占用")
                logger.error("")
                logger.error("当前集合状态：")
                try:
                    count = self.collection.count()
                    logger.error(f"  - 集合中的论文数量: {count}")
                except Exception as count_err:
                    logger.error(f"  - 无法获取集合状态: {count_err}")
                logger.error("")
                logger.error("解决方案（按顺序尝试）：")
                logger.error("  1. 重启服务，可能是临时文件锁定问题")
                logger.error("  2. 运行修复脚本: python backend/scripts/fix_chromadb.py")
                logger.error("  3. 手动删除 chroma_db 目录并重新索引")
                logger.error("  4. 检查 ChromaDB 版本兼容性")
                logger.error("")
                logger.error("注意：不要自动删除集合，这会导致数据丢失！")
                logger.error("=" * 60)
                
                raise RuntimeError(
                    "ChromaDB 索引文件损坏。请使用修复脚本或手动删除 chroma_db 目录后重新索引。"
                    f"详细错误: {error_msg}"
                )
            
            raise

    def search_requirements(self, query_text: str, top_k: int = 50) -> List[Tuple[str, float]]:
        """
        搜索相似需求（完全复用search_similar的逻辑，只改变集合）
        返回: [(requirement_id, similarity_score), ...]
        """
        try:
            # 将查询文本转换为向量（复用search_similar的embed_text调用）
            query_embedding = self.embed_text(query_text)
            
            # 在 ChromaDB 中搜索（与search_similar完全一致的查询方式）
            results = self.requirement_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            # 提取结果（与search_similar完全一致的处理方式）
            requirement_ids = results['ids'][0]
            distances = results['distances'][0]
            
            # 将距离转换为相似度分数（cosine distance -> similarity）
            # cosine distance = 1 - cosine similarity
            similarities = [(rid, 1 - dist) for rid, dist in zip(requirement_ids, distances)]
            
            logger.info(f"找到 {len(similarities)} 个相似需求")
            
            return similarities
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"需求搜索失败: {error_msg}")
            
            # 检查是否是 ChromaDB 索引文件损坏的错误（与search_similar保持一致）
            if 'Cannot open header file' in error_msg or 'header file' in error_msg.lower():
                logger.error("=" * 60)
                logger.error("检测到 ChromaDB 索引文件损坏错误（需求集合）")
                logger.error("=" * 60)
                logger.error("")
                logger.error("可能的原因：")
                logger.error("  1. ChromaDB 数据库文件损坏")
                logger.error("  2. HNSW 索引文件损坏")
                logger.error("  3. ChromaDB 版本不兼容")
                logger.error("  4. 数据库文件被其他进程占用")
                logger.error("")
                logger.error("当前集合状态：")
                try:
                    count = self.requirement_collection.count()
                    logger.error(f"  - 集合中的需求数量: {count}")
                except Exception as count_err:
                    logger.error(f"  - 无法获取集合状态: {count_err}")
                logger.error("")
                logger.error("解决方案（按顺序尝试）：")
                logger.error("  1. 重启服务，可能是临时文件锁定问题")
                logger.error("  2. 运行修复脚本: python backend/scripts/fix_chromadb.py")
                logger.error("  3. 手动删除 chroma_db 目录并重新索引")
                logger.error("  4. 检查 ChromaDB 版本兼容性")
                logger.error("")
                logger.error("注意：不要自动删除集合，这会导致数据丢失！")
                logger.error("=" * 60)
                
                raise RuntimeError(
                    "ChromaDB 索引文件损坏（需求集合）。请使用修复脚本或手动删除 chroma_db 目录后重新索引。"
                    f"详细错误: {error_msg}"
                )
            
            raise
    
    def get_paper_count(self) -> int:
        """获取向量数据库中的论文数量"""
        try:
            return self.collection.count()
        except Exception as e:
            error_msg = str(e)
            if 'Cannot open header file' in error_msg or 'header file' in error_msg.lower():
                logger.error("无法获取论文数量：ChromaDB 索引文件损坏")
                logger.error("请运行修复脚本: python backend/scripts/fix_chromadb.py")
            raise
    
    def check_collection_health(self) -> Dict:
        """
        检查集合健康状态
        返回: {"healthy": bool, "count": int, "error": str}
        """
        try:
            count = self.collection.count()
            return {
                "healthy": True,
                "count": count,
                "error": None
            }
        except Exception as e:
            error_msg = str(e)
            return {
                "healthy": False,
                "count": 0,
                "error": error_msg
            }

# 全局单例
_vector_service = None

def get_vector_service() -> VectorService:
    """获取向量服务单例"""
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorService()
    return _vector_service

