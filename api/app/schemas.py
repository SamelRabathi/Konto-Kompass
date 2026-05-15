from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    tenant_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str

    class Config:
        from_attributes = True


class TenantOut(BaseModel):
    id: int
    name: str
    role: Optional[str] = None

    class Config:
        from_attributes = True


class AreaOut(BaseModel):
    id: int
    slug: str
    label: str
    sort_order: int

    class Config:
        from_attributes = True


class AreaCreate(BaseModel):
    slug: str
    label: str
    sort_order: int = 0


class AccountOut(BaseModel):
    id: int
    tenant_id: int
    area_id: int
    connection_id: Optional[int]
    provider: str
    name: str
    currency: str
    is_manual: bool
    external_ref: Optional[str]

    class Config:
        from_attributes = True


class AccountCreate(BaseModel):
    area_id: int
    name: str
    provider: str = "manual"
    currency: str = "EUR"
    is_manual: bool = True
    connection_id: Optional[int] = None
    external_ref: Optional[str] = None


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    area_id: Optional[int] = None
    provider: Optional[str] = None


class HoldingOut(BaseModel):
    id: int
    account_id: int
    asset_type: str
    symbol: str
    isin: Optional[str]
    quantity: float
    market_value_eur: float
    as_of: datetime

    class Config:
        from_attributes = True


class HoldingCreate(BaseModel):
    account_id: int
    asset_type: str
    symbol: str
    isin: Optional[str] = None
    quantity: float
    market_value_eur: float


class HoldingUpdate(BaseModel):
    asset_type: Optional[str] = None
    symbol: Optional[str] = None
    isin: Optional[str] = None
    quantity: Optional[float] = None
    market_value_eur: Optional[float] = None


class BalanceSnapshotOut(BaseModel):
    id: int
    account_id: int
    amount_eur: float
    ts: datetime

    class Config:
        from_attributes = True


class BalanceCreate(BaseModel):
    account_id: int
    amount_eur: float


class LiabilityOut(BaseModel):
    id: int
    tenant_id: int
    label: str
    liability_type: str
    provider: Optional[str]
    principal_eur: float
    remaining_eur: float
    interest_rate: Optional[float]
    monthly_payment_eur: Optional[float]
    due_date: Optional[datetime]

    class Config:
        from_attributes = True


class LiabilityCreate(BaseModel):
    label: str
    liability_type: str = "other"
    provider: Optional[str] = None
    principal_eur: float
    remaining_eur: float
    interest_rate: Optional[float] = None
    monthly_payment_eur: Optional[float] = None
    due_date: Optional[datetime] = None


class LiabilityUpdate(BaseModel):
    label: Optional[str] = None
    liability_type: Optional[str] = None
    provider: Optional[str] = None
    principal_eur: Optional[float] = None
    remaining_eur: Optional[float] = None
    interest_rate: Optional[float] = None
    monthly_payment_eur: Optional[float] = None
    due_date: Optional[datetime] = None


class ConnectionOut(BaseModel):
    id: int
    tenant_id: int
    provider: str
    label: str
    status: str
    external_ref: Optional[str]

    class Config:
        from_attributes = True


class ConnectionCreate(BaseModel):
    provider: str
    label: str
    external_ref: Optional[str] = None
    token_data: Optional[dict | str] = None


class ConnectionUpdate(BaseModel):
    label: Optional[str] = None
    status: Optional[str] = None
    external_ref: Optional[str] = None
    token_data: Optional[dict | str] = None


class CsvImportRequest(BaseModel):
    csv_content: str
    account_name: str = "Trade Republic"


class OverviewOut(BaseModel):
    assets_liquidity_eur: float
    assets_investments_eur: float
    liabilities_total_eur: float
    net_worth_eur: float
    areas: list[dict]


class SnapshotOut(BaseModel):
    id: int
    tenant_id: int
    ts: datetime
    assets_liquidity_eur: float
    assets_investments_eur: float
    liabilities_total_eur: float
    net_worth_eur: float
    eos_eur: float
    stocks_eur: float
    cash_eur: float
    threshold_total_eur: float
    threshold_hit: bool

    class Config:
        from_attributes = True


class LegacySnapshotOut(BaseModel):
    id: int
    tenant_id: int
    ts: datetime
    total_eur: float
    eos_eur: float
    stocks_eur: float
    cash_eur: float
    threshold_total_eur: float
    threshold_hit: bool

    class Config:
        from_attributes = True
