from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.repository import save_correction
from backend.app.schemas import CorrectionRequest

router = APIRouter(prefix="/corrections", tags=["corrections"])


@router.post("", status_code=201)
def create_correction(request: CorrectionRequest, db: Session = Depends(get_db)) -> dict[str, int | str]:
    row = save_correction(db, request)
    return {"id": row.id, "status": "recorded"}
