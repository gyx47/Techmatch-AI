"""
PDF解析服务
支持下载和提取arXiv论文PDF的文本内容
"""
import logging
import requests
import io
from typing import Optional, List, Dict
from pathlib import Path
import tempfile
import os

logger = logging.getLogger(__name__)

try:
    import PyPDF2  # type: ignore
    PDF_LIBRARY = "PyPDF2"
except ImportError:
    try:
        import pdfplumber  # type: ignore
        PDF_LIBRARY = "pdfplumber"
    except ImportError:
        PDF_LIBRARY = None
        logger.warning("未安装PDF解析库，请安装 PyPDF2 或 pdfplumber")


class PDFService:
    """PDF解析服务"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "arxiv_pdfs"
        self.temp_dir.mkdir(exist_ok=True)
    
    def download_pdf(self, pdf_url: str, arxiv_id: str) -> Optional[Path]:
        """
        下载PDF文件到临时目录
        
        Args:
            pdf_url: PDF的URL
            arxiv_id: 论文的arXiv ID，用作文件名
            
        Returns:
            下载后的文件路径，失败返回None
        """
        try:
            # 构建本地文件路径
            local_path = self.temp_dir / f"{arxiv_id}.pdf"
            
            # 如果文件已存在，直接返回
            if local_path.exists():
                logger.info(f"PDF已存在: {local_path}")
                return local_path
            
            # 下载PDF
            logger.info(f"正在下载PDF: {pdf_url}")
            response = requests.get(pdf_url, timeout=30, stream=True)
            response.raise_for_status()
            
            # 保存到本地
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"PDF下载成功: {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"下载PDF失败 {pdf_url}: {e}")
            return None
    
    def extract_text_from_pdf(self, pdf_path: Path, max_pages: int = 20) -> str:
        """
        从PDF文件中提取文本内容
        
        Args:
            pdf_path: PDF文件路径
            max_pages: 最大提取页数（避免处理过长论文）
            
        Returns:
            提取的文本内容
        """
        if PDF_LIBRARY is None:
            raise ImportError("请安装PDF解析库: pip install PyPDF2 或 pip install pdfplumber")
        
        try:
            text_parts = []
            
            if PDF_LIBRARY == "PyPDF2":
                with open(pdf_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    total_pages = min(len(pdf_reader.pages), max_pages)
                    
                    for page_num in range(total_pages):
                        page = pdf_reader.pages[page_num]
                        text = page.extract_text()
                        if text.strip():
                            text_parts.append(f"=== 第 {page_num + 1} 页 ===\n{text}\n")
            
            elif PDF_LIBRARY == "pdfplumber":
                with pdfplumber.open(pdf_path) as pdf:
                    total_pages = min(len(pdf.pages), max_pages)
                    
                    for page_num in range(total_pages):
                        page = pdf.pages[page_num]
                        text = page.extract_text()
                        if text:
                            text_parts.append(f"=== 第 {page_num + 1} 页 ===\n{text}\n")
            
            full_text = "\n".join(text_parts)
            
            # 清理文本：移除多余空白
            full_text = "\n".join(line.strip() for line in full_text.split("\n") if line.strip())
            
            logger.info(f"成功提取PDF文本，共 {total_pages} 页，约 {len(full_text)} 字符")
            return full_text
            
        except Exception as e:
            logger.error(f"提取PDF文本失败 {pdf_path}: {e}")
            raise
    
    def get_paper_content(self, pdf_url: str, arxiv_id: str, max_pages: int = 20) -> Optional[str]:
        """
        获取论文的完整文本内容（下载+解析）
        
        Args:
            pdf_url: PDF的URL
            arxiv_id: 论文的arXiv ID
            max_pages: 最大提取页数
            
        Returns:
            论文文本内容，失败返回None
        """
        try:
            # 下载PDF
            pdf_path = self.download_pdf(pdf_url, arxiv_id)
            if not pdf_path:
                return None
            
            # 提取文本
            text = self.extract_text_from_pdf(pdf_path, max_pages)
            return text
            
        except Exception as e:
            logger.error(f"获取论文内容失败 {arxiv_id}: {e}")
            return None
    
    def cleanup_temp_files(self, arxiv_id: Optional[str] = None):
        """
        清理临时文件
        
        Args:
            arxiv_id: 如果指定，只删除该论文的PDF；否则删除所有临时文件
        """
        try:
            if arxiv_id:
                pdf_path = self.temp_dir / f"{arxiv_id}.pdf"
                if pdf_path.exists():
                    pdf_path.unlink()
                    logger.info(f"已删除临时文件: {pdf_path}")
            else:
                # 删除所有临时PDF文件
                for pdf_file in self.temp_dir.glob("*.pdf"):
                    pdf_file.unlink()
                logger.info("已清理所有临时PDF文件")
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")


# 单例模式
_pdf_service = None

def get_pdf_service() -> PDFService:
    """获取PDF服务单例"""
    global _pdf_service
    if _pdf_service is None:
        _pdf_service = PDFService()
    return _pdf_service

