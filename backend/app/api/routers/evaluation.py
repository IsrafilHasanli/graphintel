"""Evaluation + release-gate endpoints.

Contract
--------
POST /eval/run            -> EvalRunOut          (run golden questions, persist)
GET  /eval/latest         -> EvalRunOut | 404     (most recent run)
GET  /eval/release-gate   -> ReleaseGateOut       (PASS|CONDITIONAL PASS|FAIL)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas import EvalRunOut, ReleaseGateOut
from app.services.evaluation import EvaluationService

router = APIRouter(tags=["evaluation"], prefix="/eval")


@router.post("/run", response_model=EvalRunOut)
def run_eval(db: Session = Depends(get_db)) -> EvalRunOut:
    return EvaluationService(db).run(persist=True)


@router.get("/latest", response_model=EvalRunOut)
def latest_eval(db: Session = Depends(get_db)) -> EvalRunOut:
    run = EvaluationService(db).latest_run()
    if run is None:
        raise HTTPException(status_code=404, detail="no evaluation run recorded yet")
    return run


@router.get("/release-gate", response_model=ReleaseGateOut)
def release_gate(db: Session = Depends(get_db)) -> ReleaseGateOut:
    return EvaluationService(db).release_gate()
