from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
	__tablename__ = "users"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False)
	email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

	transactions: Mapped[list["Transaction"]] = relationship(
		back_populates="user", cascade="all, delete-orphan"
	)


class Transaction(Base):
	__tablename__ = "transactions"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

	# Basic money movement
	date: Mapped[date] = mapped_column(Date, nullable=False)
	type: Mapped[str] = mapped_column(String(20), nullable=False)  # income | expense | transfer | trade
	category: Mapped[Optional[str]] = mapped_column(String(50))
	amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)  # positive always; sign handled by type

	# Investment specific
	asset_symbol: Mapped[Optional[str]] = mapped_column(String(20), index=True)
	shares: Mapped[Optional[float]] = mapped_column(Numeric(18, 6))
	price_at_trade: Mapped[Optional[float]] = mapped_column(Numeric(14, 4))

	user: Mapped["User"] = relationship(back_populates="transactions")
