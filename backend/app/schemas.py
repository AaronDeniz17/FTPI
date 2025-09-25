from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# User Schemas
class UserCreate(BaseModel):
	name: str = Field(..., min_length=1, max_length=100)
	email: EmailStr


class UserRead(BaseModel):
	id: int
	name: str
	email: EmailStr
	created_at: datetime

	class Config:
		from_attributes = True


# Transaction Schemas
class TransactionCreate(BaseModel):
	user_id: int
	date: date
	type: str = Field(..., pattern="^(income|expense|transfer|trade)$")
	category: Optional[str] = None
	amount: float = Field(..., gt=0)
	asset_symbol: Optional[str] = None
	shares: Optional[float] = Field(default=None)
	price_at_trade: Optional[float] = None


class TransactionRead(BaseModel):
	id: int
	user_id: int
	date: date
	type: str
	category: Optional[str]
	amount: float
	asset_symbol: Optional[str]
	shares: Optional[float]
	price_at_trade: Optional[float]

	class Config:
		from_attributes = True


# Analytics Schemas
class PortfolioValueRequest(BaseModel):
	user_id: int
	as_of: Optional[date] = None


class PortfolioValuePoint(BaseModel):
	date: date
	value: float


class CashflowPoint(BaseModel):
	date: date
	income: float
	expense: float
	net: float


class AllocationSlice(BaseModel):
	label: str
	value: float


class NetWorthPoint(BaseModel):
	date: date
	net_worth: float


class MonteCarloParams(BaseModel):
	user_id: int
	initial_value: Optional[float] = None
	expected_return: float = 0.07
	volatility: float = 0.15
	periods: int = 120  # months
	simulations: int = 500


class MonteCarloResult(BaseModel):
	median: list[float]
	p10: list[float]
	p90: list[float]
