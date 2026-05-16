from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from konto_models import (
    Tenant,
    User,
    TenantMembership,
    FinancialArea,
    Account,
    Holding,
    BalanceSnapshot,
    Liability,
    Connection,
    NetWorthSnapshot,
    DailySnapshot,
)
from .imports import import_holdings_csv, import_balance_csv

from .auth import (
    create_access_token,
    get_current_user,
    hash_password,
    require_tenant_access,
    require_tenant_member,
    verify_password,
)
from .celery_client import trigger_sync_tenant
from .crypto import encrypt_token_blob
from .db import get_db
from .schemas import (
    TokenResponse,
    RegisterRequest,
    LoginRequest,
    UserOut,
    TenantOut,
    AreaOut,
    AreaCreate,
    AccountOut,
    AccountCreate,
    AccountUpdate,
    HoldingOut,
    HoldingCreate,
    HoldingUpdate,
    BalanceSnapshotOut,
    BalanceCreate,
    LiabilityOut,
    LiabilityCreate,
    LiabilityUpdate,
    ConnectionOut,
    ConnectionCreate,
    ConnectionUpdate,
    CsvImportRequest,
    HoldingsCsvImportRequest,
    BalanceCsvImportRequest,
    OverviewOut,
    SnapshotOut,
    LegacySnapshotOut,
)
from .services import seed_default_areas, compute_tenant_overview

router = APIRouter()


@router.post("/auth/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="E-Mail bereits registriert")

    tenant_name = body.tenant_name or body.email.split("@")[0]
    if db.query(Tenant).filter(Tenant.name == tenant_name).first():
        tenant_name = f"{tenant_name}-{datetime.utcnow().strftime('%H%M%S')}"

    user = User(email=body.email, password_hash=hash_password(body.password))
    tenant = Tenant(name=tenant_name, threshold_total_eur=25000.0)
    db.add(user)
    db.add(tenant)
    db.flush()

    db.add(TenantMembership(user_id=user.id, tenant_id=tenant.id, role="owner"))
    seed_default_areas(db, tenant.id)
    db.commit()

    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token)


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Ungültige Anmeldedaten")
    return TokenResponse(access_token=create_access_token(user.id, user.email))


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/tenants", response_model=list[TenantOut])
def list_tenants(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Tenant, TenantMembership.role)
        .join(TenantMembership, TenantMembership.tenant_id == Tenant.id)
        .filter(TenantMembership.user_id == user.id)
        .all()
    )
    return [TenantOut(id=t.id, name=t.name, role=role) for t, role in rows]


@router.get("/tenants/{tenant_id}/overview", response_model=OverviewOut)
def tenant_overview(
    tenant_id: int,
    _: TenantMembership = Depends(require_tenant_access),
    db: Session = Depends(get_db),
):
    return compute_tenant_overview(db, tenant_id)


@router.get("/tenants/{tenant_id}/snapshots", response_model=list[SnapshotOut])
def list_snapshots(
    tenant_id: int,
    limit: int = 90,
    _: TenantMembership = Depends(require_tenant_access),
    db: Session = Depends(get_db),
):
    snaps = (
        db.query(NetWorthSnapshot)
        .filter(NetWorthSnapshot.tenant_id == tenant_id)
        .order_by(NetWorthSnapshot.ts.desc())
        .limit(limit)
        .all()
    )
    return snaps


@router.get("/tenants/{tenant_id}/snapshots/latest", response_model=SnapshotOut | None)
def latest_snapshot(
    tenant_id: int,
    _: TenantMembership = Depends(require_tenant_access),
    db: Session = Depends(get_db),
):
    return (
        db.query(NetWorthSnapshot)
        .filter(NetWorthSnapshot.tenant_id == tenant_id)
        .order_by(NetWorthSnapshot.ts.desc())
        .first()
    )


@router.get("/tenants/{tenant_id}/snapshots/legacy/latest", response_model=LegacySnapshotOut | None)
def latest_legacy_snapshot(
    tenant_id: int,
    _: TenantMembership = Depends(require_tenant_access),
    db: Session = Depends(get_db),
):
    return (
        db.query(DailySnapshot)
        .filter(DailySnapshot.tenant_id == tenant_id)
        .order_by(DailySnapshot.ts.desc())
        .first()
    )


@router.get("/tenants/{tenant_id}/areas", response_model=list[AreaOut])
def list_areas(
    tenant_id: int,
    _: TenantMembership = Depends(require_tenant_access),
    db: Session = Depends(get_db),
):
    return (
        db.query(FinancialArea)
        .filter(FinancialArea.tenant_id == tenant_id)
        .order_by(FinancialArea.sort_order)
        .all()
    )


@router.post("/tenants/{tenant_id}/areas", response_model=AreaOut)
def create_area(
    tenant_id: int,
    body: AreaCreate,
    membership: TenantMembership = Depends(require_tenant_member),
    db: Session = Depends(get_db),
):
    area = FinancialArea(tenant_id=tenant_id, **body.model_dump())
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


@router.get("/tenants/{tenant_id}/accounts", response_model=list[AccountOut])
def list_accounts(
    tenant_id: int,
    _: TenantMembership = Depends(require_tenant_access),
    db: Session = Depends(get_db),
):
    return db.query(Account).filter(Account.tenant_id == tenant_id).all()


@router.post("/tenants/{tenant_id}/accounts", response_model=AccountOut)
def create_account(
    tenant_id: int,
    body: AccountCreate,
    membership: TenantMembership = Depends(require_tenant_member),
    db: Session = Depends(get_db),
):
    area = db.query(FinancialArea).filter(FinancialArea.id == body.area_id, FinancialArea.tenant_id == tenant_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Bereich nicht gefunden")
    account = Account(tenant_id=tenant_id, **body.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.patch("/tenants/{tenant_id}/accounts/{account_id}", response_model=AccountOut)
def update_account(
    tenant_id: int,
    account_id: int,
    body: AccountUpdate,
    membership: TenantMembership = Depends(require_tenant_member),
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.id == account_id, Account.tenant_id == tenant_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Konto nicht gefunden")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(account, key, value)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/tenants/{tenant_id}/accounts/{account_id}", status_code=204)
def delete_account(
    tenant_id: int,
    account_id: int,
    membership: TenantMembership = Depends(require_tenant_member),
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.id == account_id, Account.tenant_id == tenant_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Konto nicht gefunden")
    db.delete(account)
    db.commit()


@router.get("/tenants/{tenant_id}/holdings", response_model=list[HoldingOut])
def list_holdings(
    tenant_id: int,
    _: TenantMembership = Depends(require_tenant_access),
    db: Session = Depends(get_db),
):
    account_ids = [a.id for a in db.query(Account.id).filter(Account.tenant_id == tenant_id).all()]
    if not account_ids:
        return []
    return db.query(Holding).filter(Holding.account_id.in_(account_ids)).all()


@router.post("/tenants/{tenant_id}/holdings", response_model=HoldingOut)
def create_holding(
    tenant_id: int,
    body: HoldingCreate,
    membership: TenantMembership = Depends(require_tenant_member),
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.id == body.account_id, Account.tenant_id == tenant_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Konto nicht gefunden")
    holding = Holding(**body.model_dump())
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return holding


@router.patch("/tenants/{tenant_id}/holdings/{holding_id}", response_model=HoldingOut)
def update_holding(
    tenant_id: int,
    holding_id: int,
    body: HoldingUpdate,
    membership: TenantMembership = Depends(require_tenant_member),
    db: Session = Depends(get_db),
):
    holding = (
        db.query(Holding)
        .join(Account, Account.id == Holding.account_id)
        .filter(Holding.id == holding_id, Account.tenant_id == tenant_id)
        .first()
    )
    if not holding:
        raise HTTPException(status_code=404, detail="Position nicht gefunden")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(holding, key, value)
    db.commit()
    db.refresh(holding)
    return holding


@router.delete("/tenants/{tenant_id}/holdings/{holding_id}", status_code=204)
def delete_holding(
    tenant_id: int,
    holding_id: int,
    membership: TenantMembership = Depends(require_tenant_member),
    db: Session = Depends(get_db),
):
    holding = (
        db.query(Holding)
        .join(Account, Account.id == Holding.account_id)
        .filter(Holding.id == holding_id, Account.tenant_id == tenant_id)
        .first()
    )
    if not holding:
        raise HTTPException(status_code=404, detail="Position nicht gefunden")
    db.delete(holding)
    db.commit()


@router.post("/tenants/{tenant_id}/balances", response_model=BalanceSnapshotOut)
def create_balance(
    tenant_id: int,
    body: BalanceCreate,
    membership: TenantMembership = Depends(require_tenant_member),
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.id == body.account_id, Account.tenant_id == tenant_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Konto nicht gefunden")
    snap = BalanceSnapshot(account_id=body.account_id, amount_eur=body.amount_eur)
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


@router.get("/tenants/{tenant_id}/liabilities", response_model=list[LiabilityOut])
def list_liabilities(
    tenant_id: int,
    _: TenantMembership = Depends(require_tenant_access),
    db: Session = Depends(get_db),
):
    return db.query(Liability).filter(Liability.tenant_id == tenant_id).all()


@router.post("/tenants/{tenant_id}/liabilities", response_model=LiabilityOut)
def create_liability(
    tenant_id: int,
    body: LiabilityCreate,
    membership: TenantMembership = Depends(require_tenant_member),
    db: Session = Depends(get_db),
):
    liability = Liability(tenant_id=tenant_id, **body.model_dump())
    db.add(liability)
    db.commit()
    db.refresh(liability)
    return liability


@router.patch("/tenants/{tenant_id}/liabilities/{liability_id}", response_model=LiabilityOut)
def update_liability(
    tenant_id: int,
    liability_id: int,
    body: LiabilityUpdate,
    membership: TenantMembership = Depends(require_tenant_member),
    db: Session = Depends(get_db),
):
    liability = db.query(Liability).filter(Liability.id == liability_id, Liability.tenant_id == tenant_id).first()
    if not liability:
        raise HTTPException(status_code=404, detail="Schuld nicht gefunden")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(liability, key, value)
    db.commit()
    db.refresh(liability)
    return liability


@router.delete("/tenants/{tenant_id}/liabilities/{liability_id}", status_code=204)
def delete_liability(
    tenant_id: int,
    liability_id: int,
    membership: TenantMembership = Depends(require_tenant_member),
    db: Session = Depends(get_db),
):
    liability = db.query(Liability).filter(Liability.id == liability_id, Liability.tenant_id == tenant_id).first()
    if not liability:
        raise HTTPException(status_code=404, detail="Schuld nicht gefunden")
    db.delete(liability)
    db.commit()


@router.get("/tenants/{tenant_id}/connections", response_model=list[ConnectionOut])
def list_connections(
    tenant_id: int,
    _: TenantMembership = Depends(require_tenant_access),
    db: Session = Depends(get_db),
):
    return db.query(Connection).filter(Connection.tenant_id == tenant_id).all()


@router.post("/tenants/{tenant_id}/connections", response_model=ConnectionOut)
def create_connection(
    tenant_id: int,
    body: ConnectionCreate,
    membership: TenantMembership = Depends(require_tenant_member),
    db: Session = Depends(get_db),
):
    token_blob = encrypt_token_blob(body.token_data) if body.token_data is not None else None
    conn = Connection(
        tenant_id=tenant_id,
        provider=body.provider,
        label=body.label,
        external_ref=body.external_ref,
        token_blob=token_blob,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return conn


@router.patch("/tenants/{tenant_id}/connections/{connection_id}", response_model=ConnectionOut)
def update_connection(
    tenant_id: int,
    connection_id: int,
    body: ConnectionUpdate,
    membership: TenantMembership = Depends(require_tenant_member),
    db: Session = Depends(get_db),
):
    conn = db.query(Connection).filter(Connection.id == connection_id, Connection.tenant_id == tenant_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Verbindung nicht gefunden")
    data = body.model_dump(exclude_unset=True)
    token_data = data.pop("token_data", None)
    for key, value in data.items():
        setattr(conn, key, value)
    if token_data is not None:
        conn.token_blob = encrypt_token_blob(token_data)
    db.commit()
    db.refresh(conn)
    return conn


@router.delete("/tenants/{tenant_id}/connections/{connection_id}", status_code=204)
def delete_connection(
    tenant_id: int,
    connection_id: int,
    membership: TenantMembership = Depends(require_tenant_member),
    db: Session = Depends(get_db),
):
    conn = db.query(Connection).filter(Connection.id == connection_id, Connection.tenant_id == tenant_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Verbindung nicht gefunden")
    db.delete(conn)
    db.commit()


@router.post("/tenants/{tenant_id}/connections/{connection_id}/sync")
def sync_connection(
    tenant_id: int,
    connection_id: int,
    membership: TenantMembership = Depends(require_tenant_member),
    db: Session = Depends(get_db),
):
    conn = db.query(Connection).filter(Connection.id == connection_id, Connection.tenant_id == tenant_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Verbindung nicht gefunden")
    trigger_sync_tenant(tenant_id)
    return {"status": "queued", "tenant_id": tenant_id, "connection_id": connection_id}


@router.post("/tenants/{tenant_id}/sync")
def sync_tenant(
    tenant_id: int,
    membership: TenantMembership = Depends(require_tenant_member),
):
    trigger_sync_tenant(tenant_id)
    return {"status": "queued", "tenant_id": tenant_id}


@router.post("/tenants/{tenant_id}/import/trade-republic-csv")
def import_trade_republic_csv_route(
    tenant_id: int,
    body: CsvImportRequest,
    membership: TenantMembership = Depends(require_tenant_member),
    db: Session = Depends(get_db),
):
    try:
        result = import_holdings_csv(
            db,
            tenant_id,
            body.csv_content,
            body.account_name,
            provider_label="Trade Republic CSV",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    trigger_sync_tenant(tenant_id)
    return {"status": "imported", **result}


@router.post("/tenants/{tenant_id}/import/holdings-csv")
def import_holdings_csv_route(
    tenant_id: int,
    body: HoldingsCsvImportRequest,
    membership: TenantMembership = Depends(require_tenant_member),
    db: Session = Depends(get_db),
):
    try:
        result = import_holdings_csv(
            db,
            tenant_id,
            body.csv_content,
            body.account_name,
            provider_label=body.provider_label,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    trigger_sync_tenant(tenant_id)
    return {"status": "imported", **result}


@router.post("/tenants/{tenant_id}/import/balance-csv")
def import_balance_csv_route(
    tenant_id: int,
    body: BalanceCsvImportRequest,
    membership: TenantMembership = Depends(require_tenant_member),
    db: Session = Depends(get_db),
):
    try:
        result = import_balance_csv(
            db,
            tenant_id,
            body.csv_content,
            body.default_account_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    trigger_sync_tenant(tenant_id)
    return {"status": "imported", **result}
