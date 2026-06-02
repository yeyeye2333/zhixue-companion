"""智能问答服务"""
import uuid

from sqlalchemy.orm import Session

from app.models.chat import ChatMessage
from app.schemas.chat import ChatRequest
from app.services import minimax_client


def send_message(req: ChatRequest, user_id: str, db: Session) -> dict:
    # 确定会话 ID
    session_id = req.session_id or str(uuid.uuid4())

    # 读取历史消息（最近 10 条）
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .limit(10)
        .all()
    )
    history_data = [{"role": m.role, "content": m.content} for m in history]

    # 调用 MiniMax
    result = minimax_client.answer_question(req.question, req.course, history_data)

    # 保存用户问题
    db.add(ChatMessage(
        user_id=user_id,
        session_id=session_id,
        role="user",
        content=req.question,
        course=req.course,
    ))
    # 保存 AI 回答
    db.add(ChatMessage(
        user_id=user_id,
        session_id=session_id,
        role="assistant",
        content=result.get("answer", ""),
        course=req.course,
    ))
    db.commit()

    return {
        "session_id": session_id,
        "answer": result.get("answer", ""),
        "suggestions": result.get("suggestions", []),
    }


def get_session_messages(session_id: str, user_id: str, db: Session) -> list:
    messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.session_id == session_id,
            ChatMessage.user_id == user_id,
        )
        .order_by(ChatMessage.created_at)
        .all()
    )
    return messages
