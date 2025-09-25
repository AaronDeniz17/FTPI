from __future__ import annotations

from datetime import date, timedelta
from typing import List

import math
import random
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud, schemas
from .db import get_session, lifespan
from .market import get_last_prices, get_price_history

app = FastAPI(lifespan=lifespan, title="Full-Stack Finance API", version="0.1.0")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# Users
@app.post("/api/users", response_model=schemas.UserRead, tags=["Users"], summary="Create User")
async def create_user(payload: schemas.UserCreate, session: AsyncSession = Depends(get_session)):
	return await crud.create_user(session, payload.name, payload.email)

@app.get("/api/users", response_model=List[schemas.UserRead], tags=["Users"], summary="List Users")
async def list_users(session: AsyncSession = Depends(get_session)):
	return await crud.list_users(session)

# Transactions
@app.post("/api/transactions", response_model=schemas.TransactionRead, tags=["Transactions"], summary="Add Transaction")
async def add_transaction(payload: schemas.TransactionCreate, session: AsyncSession = Depends(get_session)):
	return await crud.create_transaction(
		session,
		user_id=payload.user_id,
		date_=payload.date,
		type_=payload.type,
		category=payload.category,
		amount=payload.amount,
		asset_symbol=payload.asset_symbol,
		shares=payload.shares,
		price_at_trade=payload.price_at_trade,
	)


@app.get("/api/transactions", response_model=List[schemas.TransactionRead], tags=["Transactions"], summary="Get Transactions")
async def get_transactions(user_id: int | None = None, session: AsyncSession = Depends(get_session)):
	return await crud.list_transactions(session, user_id)


# Helpers

def date_range(start: date, end: date) -> List[date]:
	res: List[date] = []
	cur = start
	while cur <= end:
		res.append(cur)
		cur = cur + timedelta(days=1)
	return res
 

# Analytics
@app.get("/api/portfolio/value", response_model=List[schemas.PortfolioValuePoint], tags=["Analytics"], summary="Portfolio Value")
async def portfolio_value(user_id: int, as_of: date | None = None, session: AsyncSession = Depends(get_session)):
	as_of = as_of or date.today()
	positions = await crud.get_positions(session, user_id)
	cash = await crud.get_cash_balance(session, user_id)
	if not positions:
		return [{"date": as_of, "value": float(cash)}]
	symbols = list(positions.keys())
	start = as_of - timedelta(days=365)
	history = await get_price_history(symbols, start, as_of)
	points: list[schemas.PortfolioValuePoint] = []
	for d in date_range(start, as_of):
		total = cash
		for sym, shares in positions.items():
			series = history.get(sym, [])
			# find last price at or before d
			price = 0.0
			for row in reversed(series):
				if row["date"] <= d:
					price = float(row["close"])
					break
			total += shares * price
		points.append({"date": d, "value": float(total)})
	return points


@app.get("/api/cashflow", response_model=List[schemas.CashflowPoint], tags=["Analytics"], summary="Cashflow")
async def cashflow(user_id: int, session: AsyncSession = Depends(get_session)):
	txns = await crud.list_transactions(session, user_id)
	if not txns:
		return []
	monthly: dict[tuple[int, int], dict[str, float]] = {}
	for t in txns:
		if t.type not in ("income", "expense"):
			continue
		key = (t.date.year, t.date.month)
		if key not in monthly:
			monthly[key] = {"income": 0.0, "expense": 0.0}
		if t.type == "income":
			monthly[key]["income"] += float(t.amount)
		else:
			monthly[key]["expense"] += float(t.amount)
	points: list[schemas.CashflowPoint] = []
	for (y, m) in sorted(monthly.keys()):
		income = monthly[(y, m)]["income"]
		expense = monthly[(y, m)]["expense"]
		points.append({
			"date": date(y, m, 1),
			"income": float(income),
			"expense": float(expense),
			"net": float(income - expense),
		})
	return points


@app.get("/api/allocation", response_model=List[schemas.AllocationSlice], tags=["Analytics"], summary="Allocation")
async def allocation(user_id: int, as_of: date | None = None, session: AsyncSession = Depends(get_session)):
	as_of = as_of or date.today()
	positions = await crud.get_positions(session, user_id)
	cash = await crud.get_cash_balance(session, user_id)
	symbols = list(positions.keys())
	prices = await get_last_prices(symbols, as_of) if symbols else {}
	parts: list[dict] = []
	if cash > 0:
		parts.append({"label": "Cash", "value": float(cash)})
	for s in symbols:
		value = positions[s] * prices.get(s, 0.0)
		if value > 0:
			parts.append({"label": s.upper(), "value": float(value)})
	return parts


@app.get("/api/networth", response_model=List[schemas.NetWorthPoint], tags=["Analytics"], summary="Networth")
async def networth(user_id: int, as_of: date | None = None, session: AsyncSession = Depends(get_session)):
	as_of = as_of or date.today()
	pv = await portfolio_value(user_id=user_id, as_of=as_of, session=session)
	return [{"date": p["date"], "net_worth": p["value"]} for p in pv]


@app.post("/api/montecarlo", response_model=schemas.MonteCarloResult, tags=["Analytics"], summary="Monte Carlo")
async def monte_carlo(params: schemas.MonteCarloParams, session: AsyncSession = Depends(get_session)):
	as_of = date.today()
	positions = await crud.get_positions(session, params.user_id)
	cash = await crud.get_cash_balance(session, params.user_id)
	total = float(cash)
	if positions:
		last_prices = await get_last_prices(list(positions.keys()), as_of)
		for s, sh in positions.items():
			total += sh * last_prices.get(s, 0.0)
	initial = params.initial_value if params.initial_value is not None else total
	n = params.periods
	sims = params.simulations
	mu = params.expected_return
	sigma = params.volatility
	dt = 1.0 / 12.0
	means = (mu - 0.5 * sigma * sigma) * dt
	stds = sigma * math.sqrt(dt)
	def simulate_path() -> list[float]:
		value = initial
		vals = [value]
		for _ in range(n):
			shock = random.gauss(means, stds)
			value = value * math.exp(shock)
			vals.append(value)
		return vals
	all_vals = [simulate_path() for _ in range(sims)]
	median = [float(sorted(col)[len(col)//2]) for col in zip(*all_vals)]
	p10 = [float(sorted(col)[max(0, int(0.10 * (len(col)-1)))]) for col in zip(*all_vals)]
	p90 = [float(sorted(col)[int(0.90 * (len(col)-1))]) for col in zip(*all_vals)]
	return {"median": median, "p10": p10, "p90": p90}


# Demo seed
@app.post("/api/demo/seed", tags=["Demo"], summary="Seed Demo", description="Create a demo user with repeating income/expense and a couple of trades.")
async def seed_demo(session: AsyncSession = Depends(get_session)):
	uid = random.randint(1000, 9999)
	user = await crud.create_user(session, name=f"Demo {uid}", email=f"demo{uid}@example.com")
	user_id = user.id
	start = date.today().replace(day=1) - timedelta(days=150)
	for i in range(6):
		month_date = (start + timedelta(days=30*i)).replace(day=5)
		await crud.create_transaction(session,
			user_id=user_id,
			date_=month_date,
			type_="income",
			category="salary",
			amount=5000.0,
			asset_symbol=None,
			shares=None,
			price_at_trade=None,
		)
		await crud.create_transaction(session,
			user_id=user_id,
			date_=month_date.replace(day=10),
			type_="expense",
			category="rent",
			amount=2000.0,
			asset_symbol=None,
			shares=None,
			price_at_trade=None,
		)
	await crud.create_transaction(session, user_id=user_id, date_=date.today() - timedelta(days=120), type_="trade", category="buy", amount=1500.0, asset_symbol="AAPL", shares=10, price_at_trade=150.0)
	await crud.create_transaction(session, user_id=user_id, date_=date.today() - timedelta(days=90), type_="trade", category="buy", amount=2000.0, asset_symbol="MSFT", shares=5, price_at_trade=400.0)
	return {"user_id": user_id}


# Root
@app.get("/")
async def root():
	return {"status": "ok", "service": "Full-Stack Finance API"}
