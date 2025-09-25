from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List

import io
import math
import random

import httpx

USER_AGENT = {"User-Agent": "fullstack-dashboard/1.0"}


async def fetch_stooq_history(symbol: str) -> List[dict]:
	"""Fetch daily history from Stooq (no key). Returns list of {date, close}."""
	candidates = [symbol.lower(), f"{symbol.lower()}.us"]
	async with httpx.AsyncClient(headers=USER_AGENT, timeout=10) as client:
		for cand in candidates:
			url = f"https://stooq.com/q/d/l/?s={cand}&i=d"
			resp = await client.get(url)
			text = resp.text or ""
			if resp.status_code == 200 and "Date,Open,High,Low,Close,Volume" in text:
				lines = text.strip().splitlines()
				if len(lines) <= 1:
					continue
				out: List[dict] = []
				for line in lines[1:]:
					parts = line.split(",")
					if len(parts) < 5:
						continue
					try:
						d = datetime.strptime(parts[0], "%Y-%m-%d").date()
						close = float(parts[4])
						out.append({"date": d, "close": close})
					except Exception:
						continue
				if out:
					out.sort(key=lambda r: r["date"])  
					return out
	# Return empty on failure
	return []


def daterange(start: date, end: date) -> List[date]:
	res: List[date] = []
	cur = start
	while cur <= end:
		res.append(cur)
		cur = cur + timedelta(days=1)
	return res


def simulate_gbm(start: date, end: date, start_price: float = 100.0,
				 mu: float = 0.07, sigma: float = 0.2) -> List[dict]:
	"""Simulate daily GBM prices as fallback; returns list of {date, close}."""
	dates = daterange(start, end)
	if not dates:
		return []
	dt = 1.0 / 252.0
	price = start_price
	series: List[dict] = []
	for i, d in enumerate(dates):
		if i == 0:
			series.append({"date": d, "close": price})
			continue
		shock = random.gauss((mu - 0.5 * sigma * sigma) * dt, sigma * math.sqrt(dt))
		price = price * math.exp(shock)
		series.append({"date": d, "close": price})
	return series


async def get_price_history(symbols: List[str], start: date, end: date) -> Dict[str, List[dict]]:
	"""Get price history for symbols between start and end; use fallback simulation if API fails."""
	results: Dict[str, List[dict]] = {}
	for sym in symbols:
		try:
			series = await fetch_stooq_history(sym)
			series = [row for row in series if start <= row["date"] <= end]
			if not series:
				series = simulate_gbm(start, end)
		except Exception:
			series = simulate_gbm(start, end)
		results[sym] = series
	return results


async def get_last_prices(symbols: List[str], as_of: date) -> Dict[str, float]:
	start = as_of - timedelta(days=365)
	hist = await get_price_history(symbols, start, as_of)
	last: Dict[str, float] = {}
	for sym, series in hist.items():
		if series:
			last[sym] = float(series[-1]["close"]) 
		else:
			last[sym] = 0.0
	return last
