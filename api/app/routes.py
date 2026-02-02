from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .db import get_db
from .models import Tenant, DailySnapshot

router = APIRouter()

@router.post("/tenants")
def create_tenant(name: str, db: Session = Depends(get_db)):
    t = Tenant(name=name)
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": t.id, "name": t.name}

@router.get("/tenants")
def list_tenants(db: Session = Depends(get_db)):
    return [{"id": t.id, "name": t.name} for t in db.query(Tenant).all()]

@router.get("/tenants/{tenant_id}/snapshots/latest")
def latest_snapshot(tenant_id: int, db: Session = Depends(get_db)):
    snap = (
        db.query(DailySnapshot)
        .filter(DailySnapshot.tenant_id == tenant_id)
        .order_by(DailySnapshot.ts.desc())
        .first()
    )
    return snap.__dict__ if snap else None
