import uuid
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.db.session import get_session

router = APIRouter(tags=["chat"])


@router.post("/chat/start")
async def chat_start():
    db = get_session()
    if not db:
        raise HTTPException(status_code=500, detail="DB not configured")

    session_id = str(uuid.uuid4())

    # Insert session row (anonymous)
    db.execute(
        text(
            "insert into chat_sessions (session_id, is_anonymous) "
            "values (:sid, true)"
        ),
        {"sid": session_id},
    )
    db.commit()
    db.close()

    return {"session_id": session_id}
