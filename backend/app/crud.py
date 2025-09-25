from __future__ import annotations

from datetime import date
from typing import Sequence

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Transaction, User


# Users
async def create_user(session: AsyncSession, name: str, email: str) -> User:
	user = User(name=name, email=email)
	session.add(user)
	await session.commit()
	await session.refresh(user)
	return user


async def list_users(session: AsyncSession) -> Sequence[User]:
	result = await session.execute(select(User).order_by(User.id))
	return result.scalars().all()


async def delete_user(session: AsyncSession, user_id: int) -> None:
	await session.execute(delete(User).where(User.id == user_id))
	await session.commit()


# Transactions
async def create_transaction(
	session: AsyncSession,
	*,
	user_id: int,
	date_: date,
	type_: str,
	category: str | None,
	amount: float,
	asset_symbol: str | None,
	shares: float | None,
	price_at_trade: float | None,
) -> Transaction:
	txn = Transaction(
		user_id=user_id,
		date=date_,
		type=type_,
		category=category,
		amount=amount,
		asset_symbol=asset_symbol,
		shares=shares,
		price_at_trade=price_at_trade,
	)
	session.add(txn)
	await session.commit()
	await session.refresh(txn)
	return txn


async def list_transactions(session: AsyncSession, user_id: int | None = None) -> Sequence[Transaction]:
	stmt: Select[tuple[Transaction]] = select(Transaction)
	if user_id is not None:
		stmt = stmt.where(Transaction.user_id == user_id)
	stmt = stmt.order_by(Transaction.date, Transaction.id)
	result = await session.execute(stmt)
	return result.scalars().all()


async def get_positions(session: AsyncSession, user_id: int) -> dict[str, float]:
	"""Aggregate shares by symbol for trades."""
	stmt = (
		select(Transaction.asset_symbol, func.sum(Transaction.shares))
		.where(Transaction.user_id == user_id)
		.where(Transaction.type == "trade")
		.where(Transaction.asset_symbol.is_not(None))
		.group_by(Transaction.asset_symbol)
	)
	rows = (await session.execute(stmt)).all()
	return {symbol: float(shares or 0.0) for symbol, shares in rows if symbol}


async def get_cash_balance(session: AsyncSession, user_id: int) -> float:
	income_stmt = (
		select(func.sum(Transaction.amount))
		.where(Transaction.user_id == user_id)
		.where(Transaction.type == "income")
	)
	expense_stmt = (
		select(func.sum(Transaction.amount))
		.where(Transaction.user_id == user_id)
		.where(Transaction.type == "expense")
	)
	income = (await session.execute(income_stmt)).scalar() or 0.0
	expense = (await session.execute(expense_stmt)).scalar() or 0.0
	return float(income) - float(expense)
