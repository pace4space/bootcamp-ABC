from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status as http
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user           # read-only → ANY authenticated user (incl. viewer)
from app.db import get_db
from app.models import User
from app.query import run_chat_query
from app.query.types import ChatStatus, ChatTurn
from app.schemas import ChatRequest, ChatResponse, ChatTrace

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ChatResponse:
    history = [ChatTurn(role=t.role, content=t.content) for t in body.history]
    result = await run_chat_query(body.question, history, db, model=body.model)
    await db.commit()   # commit the query_runs row regardless of outcome

    # Hard LLM failure → 422 (loop could not run). Unsafe / sql_error → 200 with a trace, so the
    # chat UI can show what happened (the diagnostic IS the value).
    if result.status == ChatStatus.LLM_ERROR:
        raise HTTPException(
            status_code=http.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": result.error, "suggestion": result.suggestion},
        )

    return ChatResponse(
        answer=result.answer,
        sql=result.sql,
        status=result.status.value,
        model=result.model_id,
        run_id=result.run_id,
        trace=ChatTrace(
            row_count=result.execution.row_count,
            columns=result.execution.columns,
            rows=result.execution.rows,
        ),
        error=result.error,
        suggestion=result.suggestion,
    )
