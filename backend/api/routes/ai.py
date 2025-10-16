"""
AI相关路由
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from api.routes.auth import get_current_user
import openai
import os
from database.database import get_db_connection

router = APIRouter()

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

class PaperSummaryRequest(BaseModel):
    paper_id: str
    summary_type: str = "brief"  # brief, detailed, key_points

class PaperSummaryResponse(BaseModel):
    summary: str
    key_points: List[str]
    relevance_score: float

# OpenAI配置（需要设置环境变量）
openai.api_key = os.getenv("OPENAI_API_KEY", "your-openai-api-key")

def get_ai_response(message: str, context: str = "") -> str:
    """获取AI响应"""
    try:
        if not openai.api_key or openai.api_key == "your-openai-api-key":
            return "AI服务未配置，请设置OPENAI_API_KEY环境变量"
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一个专业的学术助手，专门帮助用户理解和分析学术论文。"},
                {"role": "user", "content": f"{context}\n\n用户问题: {message}"}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"AI服务暂时不可用: {str(e)}"

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    chat_data: ChatMessage,
    current_user: str = Depends(get_current_user)
):
    """与AI对话"""
    try:
        # 获取AI响应
        ai_response = get_ai_response(chat_data.message)
        
        # 保存对话记录到数据库
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取用户ID
        cursor.execute("SELECT id FROM users WHERE username = ?", (current_user,))
        user_result = cursor.fetchone()
        user_id = user_result[0] if user_result else None
        
        if user_id:
            cursor.execute("""
                INSERT INTO ai_conversations (user_id, session_id, user_message, ai_response)
                VALUES (?, ?, ?, ?)
            """, (user_id, chat_data.session_id or "default", chat_data.message, ai_response))
            conn.commit()
        
        conn.close()
        
        return {
            "response": ai_response,
            "session_id": chat_data.session_id or "default"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI对话失败: {str(e)}")

@router.post("/summarize-paper", response_model=PaperSummaryResponse)
async def summarize_paper(
    summary_request: PaperSummaryRequest,
    current_user: str = Depends(get_current_user)
):
    """论文摘要生成"""
    try:
        # 从数据库获取论文信息
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE arxiv_id = ?", (summary_request.paper_id,))
        paper = cursor.fetchone()
        conn.close()
        
        if not paper:
            raise HTTPException(status_code=404, detail="论文不存在")
        
        # 构建论文上下文
        paper_context = f"""
        论文标题: {paper['title']}
        作者: {paper['authors']}
        摘要: {paper['abstract']}
        分类: {paper['categories']}
        """
        
        # 根据摘要类型生成不同的提示
        if summary_request.summary_type == "brief":
            prompt = "请为这篇论文生成一个简洁的摘要（100-150字）："
        elif summary_request.summary_type == "detailed":
            prompt = "请为这篇论文生成一个详细的摘要（300-500字）："
        else:  # key_points
            prompt = "请提取这篇论文的关键要点："
        
        # 获取AI摘要
        ai_summary = get_ai_response(prompt, paper_context)
        
        # 提取关键要点（简单实现）
        key_points = []
        if "关键要点" in ai_summary or "要点" in ai_summary:
            lines = ai_summary.split('\n')
            for line in lines:
                if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '-', '•')):
                    key_points.append(line.strip())
        
        # 计算相关性分数（简单实现）
        relevance_score = 0.8  # 这里可以实现更复杂的相关性计算
        
        return {
            "summary": ai_summary,
            "key_points": key_points[:5],  # 最多5个关键要点
            "relevance_score": relevance_score
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"论文摘要生成失败: {str(e)}")

@router.get("/conversation-history")
async def get_conversation_history(
    session_id: str = "default",
    limit: int = 20,
    current_user: str = Depends(get_current_user)
):
    """获取对话历史"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取用户ID
        cursor.execute("SELECT id FROM users WHERE username = ?", (current_user,))
        user_result = cursor.fetchone()
        user_id = user_result[0] if user_result else None
        
        if not user_id:
            return {"conversations": []}
        
        cursor.execute("""
            SELECT user_message, ai_response, created_at
            FROM ai_conversations
            WHERE user_id = ? AND session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, session_id, limit))
        
        conversations = []
        for row in cursor.fetchall():
            conversations.append({
                "user_message": row[0],
                "ai_response": row[1],
                "created_at": row[2]
            })
        
        conn.close()
        return {"conversations": conversations}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取对话历史失败: {str(e)}")
