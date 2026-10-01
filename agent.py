"""The 'agent': Claude inspects the data's schema + a small sample and decides how
the dashboard should look, by calling one tool. Falls back to heuristics if no API key."""
import json, os
import pandas as pd

TOOL = {
    "name": "configure_dashboard",
    "description": "Decide the dashboard layout for this dataset.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "filter_columns": {"type": "array", "items": {"type": "string"},
                               "description": "Low-cardinality categorical columns to filter by (max 3)"},
            "group_by": {"type": "string", "description": "Column for the main chart"},
            "agg": {"type": "string", "enum": ["count", "sum", "mean"]},
            "value_column": {"type": ["string", "null"], "description": "Numeric column for sum/mean"},
            "lat_column": {"type": ["string", "null"]},
            "lon_column": {"type": ["string", "null"]},
        },
        "required": ["title", "filter_columns", "group_by", "agg"],
    },
}


def heuristic_plan(df: pd.DataFrame) -> dict:
    cats = [c for c in df.select_dtypes("object") if 1 < df[c].nunique() <= 20]
    cols = {c.lower(): c for c in df.columns}
    return {
        "title": "Data dashboard",
        "filter_columns": cats[:2],
        "group_by": cats[0] if cats else df.columns[0],
        "agg": "count",
        "value_column": None,
        "lat_column": cols.get("lat") or cols.get("latitude"),
        "lon_column": cols.get("lon") or cols.get("lng") or cols.get("longitude"),
    }


def plan_dashboard(df: pd.DataFrame) -> dict:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return heuristic_plan(df)
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        summary = {"columns": {c: str(t) for c, t in df.dtypes.items()},
                   "rows": len(df),
                   "sample": json.loads(df.head(5).to_json(orient="records"))}
        resp = client.messages.create(
            model="claude-sonnet-5-5", max_tokens=1000,
            tools=[TOOL], tool_choice={"type": "tool", "name": "configure_dashboard"},
            messages=[{"role": "user", "content":
                       "Design a dashboard for this dataset. Use only existing column names.\n"
                       + json.dumps(summary)}])
        plan = next(b.input for b in resp.content if b.type == "tool_use")
        # Validate: drop anything that isn't a real column
        ok = set(df.columns)
        plan["filter_columns"] = [c for c in plan.get("filter_columns", []) if c in ok]
        if plan.get("group_by") not in ok:
            plan["group_by"] = heuristic_plan(df)["group_by"]
        for k in ("value_column", "lat_column", "lon_column"):
            if plan.get(k) not in ok:
                plan[k] = None
        if plan["agg"] != "count" and not plan.get("value_column"):
            plan["agg"] = "count"
        return plan
    except Exception:
        return heuristic_plan(df)
