from __future__ import annotations

import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import text

from app.db.session import get_session
from app.db import chat_io_repo
from app.schemas_chat_io import ImportChatRequest, ImportChatResponse

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

@router.get("/chat/export")
async def export_chat(session_id: str, limit: int = 2000):
    """
    Download chat as portable JSONL.
    """
    db = get_session()
    if not db:
        raise HTTPException(status_code=500, detail="DB not configured")

    try:
        jsonl = chat_io_repo.export_messages_jsonl(db, session_id=session_id, limit=limit)
        # filename hint (browsers use this if you later proxy through frontend)
        headers = {
            "Content-Disposition": f'attachment; filename="seekle_{session_id}.chat.jsonl"'
        }
        return PlainTextResponse(content=jsonl, headers=headers)
    finally:
        db.close()


@router.post("/chat/import", response_model=ImportChatResponse)
async def import_chat(req: ImportChatRequest):
    """
    Import portable JSONL into a new or existing session.
    Returns session_id + imported count.
    """
    db = get_session()
    if not db:
        raise HTTPException(status_code=500, detail="DB not configured")

    try:
        # Decide target session_id
        session_id = (req.session_id or "").strip()
        if not session_id:
            session_id = str(uuid.uuid4())

        # Ensure session exists
        chat_io_repo.ensure_session(db, session_id=session_id, is_anonymous=req.is_anonymous)

        imported = 0

        if req.jsonl and req.jsonl.strip():
            imported += chat_io_repo.import_jsonl_into_session(
                db,
                jsonl_text=req.jsonl,
                session_id=session_id,
                max_messages=req.max_messages,
            )
        elif req.text and req.text.strip():
            # Store raw transcript as ONE system message (quick & safe)
            imported += chat_io_repo.import_text_as_system_message(
                db, text_blob=req.text, session_id=session_id
            )
        else:
            raise HTTPException(status_code=422, detail="Provide jsonl or text")

        db.commit()
        return ImportChatResponse(ok=True, session_id=session_id, imported_messages=imported)

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
