from __future__ import annotations

import os
from datetime import date

import requests

import dash
from dash import Dash, dcc, html, Input, Output, State
import plotly.graph_objects as go
import dash_bootstrap_components as dbc

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")

external_stylesheets = [dbc.themes.MINTY]
app: Dash = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app.title = "Finance Dashboard"


def navbar() -> dbc.Navbar:
	return dbc.Navbar(
		[
			dbc.NavbarBrand("FINANCE DASHBOARD", class_name="ms-2 fw-bold"),
			dbc.Nav(
				[
					dbc.Button("API DOCS", href=f"{BACKEND_URL}/docs", color="light", outline=True, class_name="me-2", external_link=True),
				],
				class_name="ms-auto",
			),
		],
		color="primary",
		dark=True,
		class_name="mb-4 shadow",
	)


controls = dbc.Card(
	dbc.CardBody([
		dbc.Row([
			dbc.Col([
				dbc.Label("User ID"),
				dbc.Input(id="user-id", type="number", value=1, debounce=True, min=1, placeholder="Enter or seed demo"),
			], md=3),
			dbc.Col([
				dbc.Button("Refresh", id="refresh", color="info", class_name="mt-4 me-2"),
				dbc.Button("Seed Demo Data", id="seed", color="success", class_name="mt-4"),
			], md="auto"),
		])
	]), class_name="mb-3"
)


def build_tabs() -> dbc.Tabs:
	return dbc.Tabs(
		[
			dbc.Tab(label="Net Worth", tab_id="networth"),
			dbc.Tab(label="Cash Flow", tab_id="cashflow"),
			dbc.Tab(label="Allocation", tab_id="allocation"),
			dbc.Tab(label="Monte Carlo", tab_id="montecarlo"),
		], id="tabs", active_tab="networth"
	)


toasts = html.Div([
	dbc.Toast(id="toast", header="Info", is_open=False, dismissable=True, duration=3000, icon="primary", style={"position": "fixed", "top": 70, "right": 20, "zIndex": 1060}),
])


app.layout = dbc.Container([
	navbar(),
	controls,
	build_tabs(),
	dbc.Alert(id="error", color="danger", is_open=False, dismissable=True, class_name="mt-2"),
	toasts,
	dbc.Card(dbc.CardBody([
		dcc.Loading(id="loading", type="cube", children=html.Div(id="content"))
	]), class_name="mt-3"),
], fluid=True)


def _fetch_json(method: str, path: str, **kwargs):
	url = f"{BACKEND_URL}{path}"
	resp = requests.request(method, url, timeout=30, **kwargs)
	resp.raise_for_status()
	return resp.json()


@app.callback(Output("user-id", "value"), Output("toast", "is_open"), Output("toast", "children"), Input("seed", "n_clicks"), prevent_initial_call=True)
def seed_demo(n):
	try:
		data = _fetch_json("POST", "/api/demo/seed")
		uid = data.get("user_id")
		return uid, True, f"Seeded demo data for user_id {uid}."
	except Exception as e:
		return dash.no_update, True, f"Seed failed: {e}"


@app.callback(Output("content", "children"), Output("error", "is_open"), Output("error", "children"), [Input("tabs", "active_tab"), Input("user-id", "value"), Input("refresh", "n_clicks")])
def render_content(tab: str, user_id: int, _n):
	if not user_id:
		return html.Div(dbc.Alert("No user selected. Click Seed Demo Data to create one.", color="warning")), False, ""
	try:
		if tab == "networth":
			points = _fetch_json("GET", "/api/networth", params={"user_id": user_id})
			fig = go.Figure()
			if points:
				fig.add_trace(go.Scatter(x=[p["date"] for p in points], y=[p["net_worth"] for p in points], mode="lines", name="Net Worth", line=dict(color="#00b894", width=3)))
				fig.update_layout(template="plotly", margin=dict(l=20, r=20, t=20, b=20))
				return dcc.Graph(figure=fig), False, ""
			return html.Div(dbc.Alert("No data yet. Add transactions or seed demo.", color="secondary")), False, ""
		elif tab == "cashflow":
			points = _fetch_json("GET", "/api/cashflow", params={"user_id": user_id})
			fig = go.Figure()
			if points:
				x = [p["date"] for p in points]
				fig.add_trace(go.Bar(x=x, y=[p["income"] for p in points], name="Income", marker_color="#0984e3"))
				fig.add_trace(go.Bar(x=x, y=[-p["expense"] for p in points], name="Expense", marker_color="#d63031"))
				fig.add_trace(go.Scatter(x=x, y=[p["net"] for p in points], name="Net", mode="lines+markers", line=dict(color="#fdcb6e")))
				fig.update_layout(barmode="relative", template="plotly", margin=dict(l=20, r=20, t=20, b=20))
				return dcc.Graph(figure=fig), False, ""
			return html.Div(dbc.Alert("No data yet. Add income/expenses or seed demo.", color="secondary")), False, ""
		elif tab == "allocation":
			slices = _fetch_json("GET", "/api/allocation", params={"user_id": user_id})
			fig = go.Figure()
			if slices:
				fig.add_trace(go.Pie(labels=[s["label"] for s in slices], values=[s["value"] for s in slices], hole=0.3))
				fig.update_layout(template="plotly", margin=dict(l=20, r=20, t=20, b=20))
				return dcc.Graph(figure=fig), False, ""
			return html.Div(dbc.Alert("No positions yet. Add trades or seed demo.", color="secondary")), False, ""
		elif tab == "montecarlo":
			res = _fetch_json("POST", "/api/montecarlo", json={"user_id": user_id})
			fig = go.Figure()
			if res.get("median"):
				x = list(range(len(res["median"])))
				fig.add_trace(go.Scatter(x=x, y=res["p10"], line=dict(color="#b2bec3"), name="P10"))
				fig.add_trace(go.Scatter(x=x, y=res["p90"], line=dict(color="#b2bec3"), name="P90", fill="tonexty"))
				fig.add_trace(go.Scatter(x=x, y=res["median"], line=dict(color="#00b894"), name="Median"))
				fig.update_layout(template="plotly", margin=dict(l=20, r=20, t=20, b=20))
				return dcc.Graph(figure=fig), False, ""
			return html.Div(dbc.Alert("Not enough data to simulate.", color="secondary")), False, ""
		return html.Div("Unknown tab"), False, ""
	except Exception as e:
		return html.Div(), True, f"Error: {e}"


if __name__ == "__main__":
	app.run_server(host="0.0.0.0", port=8050, debug=True)
