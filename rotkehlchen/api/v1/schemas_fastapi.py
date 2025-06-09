"""FastAPI/Pydantic schemas to replace Marshmallow schemas during migration"""
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from rotkehlchen.types import Timestamp


class BaseResponseModel(BaseModel):
    """Base response model for all API responses"""
    result: Any
    message: str = ""
    status_code: Optional[int] = None
    
    class Config:
        extra = "forbid"


class ErrorResponseModel(BaseResponseModel):
    """Error response model"""
    result: None = None
    message: str
    error: bool = True


class SuccessResponseModel(BaseResponseModel):
    """Success response model"""
    error: bool = False


# Simple endpoint schemas
class PingResponseModel(SuccessResponseModel):
    result: dict[str, str]


class AppInfoModel(BaseModel):
    """Application information model"""
    version: str
    latest_version: Optional[str] = None
    data_directory: str
    log_level: str
    accept_docker_risk: bool
    backend_default_arguments: dict[str, Any]


class AppInfoResponseModel(SuccessResponseModel):
    result: AppInfoModel


# Async query schemas
class AsyncQueryModel(BaseModel):
    """Model for async query parameters"""
    async_query: bool = False


class AsyncTaskModel(BaseModel):
    """Model for async task responses"""
    task_id: str
    status: Literal["pending", "completed", "failed"]
    result: Optional[Any] = None
    error: Optional[str] = None


class AsyncTaskResponseModel(SuccessResponseModel):
    result: AsyncTaskModel


# Balance schemas
class AssetBalanceModel(BaseModel):
    """Model for asset balance"""
    amount: str
    usd_value: str
    
    @field_validator('amount', 'usd_value')
    @classmethod
    def validate_numeric_string(cls, v: str) -> str:
        """Ensure numeric strings are valid"""
        try:
            float(v)
        except ValueError:
            raise ValueError(f"Invalid numeric string: {v}")
        return v


class BalanceSnapshotModel(BaseModel):
    """Model for balance snapshot"""
    timestamp: Timestamp
    category: str
    asset: str
    balance: AssetBalanceModel


# History event schemas  
class HistoryEventModel(BaseModel):
    """Model for history events"""
    identifier: int
    event_identifier: str
    sequence_index: int
    timestamp: Timestamp
    location: str
    event_type: str
    event_subtype: Optional[str] = None
    asset: str
    amount: str
    usd_value: Optional[str] = None
    notes: Optional[str] = None
    location_label: Optional[str] = None
    address: Optional[str] = None
    transaction_hash: Optional[str] = None


class CreateHistoryEventModel(BaseModel):
    """Model for creating history events"""
    event_identifier: str
    sequence_index: int
    timestamp: Timestamp
    location: str
    event_type: str
    event_subtype: Optional[str] = None
    asset: str
    amount: str
    usd_value: Optional[str] = None
    notes: Optional[str] = None
    location_label: Optional[str] = None
    address: Optional[str] = None
    transaction_hash: Optional[str] = None


class EditHistoryEventModel(CreateHistoryEventModel):
    """Model for editing history events"""
    identifier: int


# WebSocket message models
class WSMessageModel(BaseModel):
    """WebSocket message model"""
    type: str
    data: Any


# Database backup models
class DatabaseBackupModel(BaseModel):
    """Database backup request model"""
    action: Literal["download", "upload"]
    file: Optional[bytes] = None


class DatabaseInfoModel(BaseModel):
    """Database info response model"""
    version: int
    size: int
    last_write_ts: Timestamp
    backup_path: Optional[str] = None


# Settings models
class SettingsModel(BaseModel):
    """Settings model matching the Marshmallow schema"""
    # This would include all settings fields
    # Simplified for example
    main_currency: str = "USD"
    decimal_places: int = 2
    anonymized_logs: bool = True
    # ... many more fields


class EditSettingsModel(BaseModel):
    """Model for editing settings - all fields optional"""
    main_currency: Optional[str] = None
    decimal_places: Optional[int] = None
    anonymized_logs: Optional[bool] = None
    # ... matching optional fields


# Exchange-specific models
class ExchangeCredentialsModel(BaseModel):
    """Model for exchange credentials"""
    name: str
    location: str
    api_key: str
    api_secret: str = Field(..., alias="secret")  # Handle field name differences
    passphrase: Optional[str] = None
    kraken_account_type: Optional[str] = None
    binance_selected_trade_pairs: Optional[list[str]] = None
    
    class Config:
        populate_by_name = True  # Allow both field name and alias


# Pagination models
class PaginationModel(BaseModel):
    """Base pagination model"""
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    order_by_attributes: Optional[list[str]] = None
    ascending: Optional[list[bool]] = None


# Filter models
class TimestampFilterModel(BaseModel):
    """Timestamp filter model"""
    from_timestamp: Optional[Timestamp] = None
    to_timestamp: Optional[Timestamp] = None


# Response wrapper helper
def create_success_response(result: Any, status_code: int = 200) -> dict:
    """Create a success response matching Flask format"""
    return {
        "result": result,
        "message": "",
        "status_code": status_code,
    }


def create_error_response(message: str, status_code: int = 400) -> dict:
    """Create an error response matching Flask format"""
    return {
        "result": None,
        "message": message,
        "error": True,
        "status_code": status_code,
    }