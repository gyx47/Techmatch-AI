"""
论文相关路由
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
import pydantic as pydantic
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from database.database import save_paper, get_papers_by_query
from api.routes.auth import get_current_user

router = APIRouter()

class PaperResponse(pydantic.BaseModel):
    arxiv_id: str
    title: str
    authors: str
    abstract: str
    published_date: str
    categories: str
    pdf_url: str

def parse_arxiv_response(xml_content: str) -> List[dict]:
    """解析arXiv API响应"""
    papers = []
    try:
        root = ET.fromstring(xml_content)
        
        for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
            paper = {}
            
            # 获取arXiv ID
            arxiv_id = entry.find('.//{http://arxiv.org/schemas/atom}id')
            if arxiv_id is not None:
                paper['arxiv_id'] = arxiv_id.text.split('/')[-1]
            
            # 获取标题
            title = entry.find('.//{http://www.w3.org/2005/Atom}title')
            if title is not None:
                paper['title'] = title.text.strip()
            
            # 获取作者
            authors = []
            for author in entry.findall('.//{http://www.w3.org/2005/Atom}author'):
                name = author.find('.//{http://www.w3.org/2005/Atom}name')
                if name is not None:
                    authors.append(name.text)
            paper['authors'] = ', '.join(authors)
            
            # 获取摘要
            summary = entry.find('.//{http://www.w3.org/2005/Atom}summary')
            if summary is not None:
                paper['abstract'] = summary.text.strip()
            
            # 获取发布日期
            published = entry.find('.//{http://www.w3.org/2005/Atom}published')
            if published is not None:
                paper['published_date'] = published.text[:10]  # 只取日期部分
            
            # 获取分类
            categories = []
            for category in entry.findall('.//{http://arxiv.org/schemas/atom}primary_category'):
                if category.get('term'):
                    categories.append(category.get('term'))
            paper['categories'] = ', '.join(categories)
            
            # 生成PDF URL
            if paper.get('arxiv_id'):
                paper['pdf_url'] = f"https://arxiv.org/pdf/{paper['arxiv_id']}.pdf"
            
            papers.append(paper)
            
    except ET.ParseError as e:
        print(f"XML解析错误: {e}")
    
    return papers

@router.get("/search", response_model=List[PaperResponse])
async def search_papers(
    query: str = Query(..., description="搜索关键词"),
    max_results: int = Query(20, description="最大结果数量"),
    current_user: str = Depends(get_current_user)
):
    """搜索论文"""
    try:
        # 构建arXiv API请求URL
        base_url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending"
        }
        
        # 发送请求到arXiv API
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        
        # 解析响应
        papers = parse_arxiv_response(response.text)
        
        # 保存论文到数据库
        for paper in papers:
            try:
                save_paper(paper)
            except Exception as e:
                print(f"保存论文失败: {e}")
        
        return papers
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"搜索请求失败: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索处理失败: {str(e)}")

@router.get("/local-search", response_model=List[PaperResponse])
async def local_search_papers(
    query: str = Query(..., description="搜索关键词"),
    limit: int = Query(20, description="结果数量限制"),
    current_user: str = Depends(get_current_user)
):
    """本地数据库搜索论文"""
    try:
        papers = get_papers_by_query(query, limit)
        return papers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"本地搜索失败: {str(e)}")

@router.get("/categories")
async def get_categories():
    """获取论文分类列表"""
    categories = [
        "cs.AI", "cs.CL", "cs.CC", "cs.CE", "cs.CG", "cs.GT", "cs.CV", "cs.CY",
        "cs.CR", "cs.DS", "cs.DB", "cs.DL", "cs.DM", "cs.DC", "cs.ET", "cs.FL",
        "cs.GL", "cs.GR", "cs.AR", "cs.HC", "cs.IR", "cs.IT", "cs.LG", "cs.LO",
        "cs.MS", "cs.MA", "cs.MM", "cs.NI", "cs.NE", "cs.NA", "cs.OS", "cs.OH",
        "cs.PF", "cs.PL", "cs.RO", "cs.SI", "cs.SE", "cs.SD", "cs.SC", "cs.SY"
    ]
    return {"categories": categories}
