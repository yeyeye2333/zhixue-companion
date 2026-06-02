from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.chat import ChatRequest
from app.services import chat_service
from app.services.auth_service import require_student

router = APIRouter(tags=["智能问答"])


def _ok(data, message="ok"):
    return {"success": True, "data": data, "message": message}


@router.post("/chat")
def send_message(req: ChatRequest, current_user=Depends(require_student), db: Session = Depends(get_db)):
    result = chat_service.send_message(req, current_user.id, db)
    return _ok(result)


@router.get("/chat/sessions/{session_id}/messages")
def get_session_messages(session_id: str, current_user=Depends(require_student), db: Session = Depends(get_db)):
    messages = chat_service.get_session_messages(session_id, current_user.id, db)
    return _ok({
        "session_id": session_id,
        "messages": [
            {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at}
            for m in messages
        ],
    })
