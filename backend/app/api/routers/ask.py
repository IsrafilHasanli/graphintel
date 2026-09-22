"""Question answering endpoints.

Contract
--------
POST /ask            AskRequest -> AnswerOut   (grounded answer, citations,
                                                reasoning path, confidence, actions)
GET  /answers/{id}   -> AnswerOut | 404          (retrieve a persisted answer)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.api.deps import get_db
from app.schemas import AnswerOut, AskRequest, Citation, QueryPlan, ReasoningEdge
from app.services.answer import AnswerService

router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=AnswerOut)
def ask(req: AskRequest, db: Session = Depends(get_db)) -> AnswerOut:
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question is empty")
    svc = AnswerService(db)
    return svc.ask(req.question, top_k=req.top_k, as_of=req.as_of)


@router.get("/answers/{answer_id}", response_model=AnswerOut)
def get_answer(answer_id: str, db: Session = Depends(get_db)) -> AnswerOut:
    row = db.get(models.Answer, answer_id)
    if row is None:
        raise HTTPException(status_code=404, detail="answer not found")
    return AnswerOut(
        id=row.id, question=row.question, answer=row.answer_text,
        confidence=row.confidence, confidence_score=row.confidence_score,
        citations=[Citation(**c) for c in row.citations],
        reasoning_path=[ReasoningEdge(**r) for r in row.reasoning_path],
        actions=row.actions, limitations=row.limitations,
        plan=QueryPlan(intent=(row.meta or {}).get("intent") or "generic"),
        created_at=row.created_at,
    )
