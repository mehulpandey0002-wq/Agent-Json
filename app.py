import io, json
import pandas as pd
import streamlit as st
from agent import plan_dashboard

st.set_page_config(page_title="Data Dashboard", layout="wide")


def to_df(raw: bytes, name: str) -> pd.DataFrame:
    name = name.lower()
    if name.endswith(".json"):
        data = json.loads(raw)
        if isinstance(data, dict):  # use the first list inside, e.g. {"airports": [...]}
            data = next((v for v in data.values() if isinstance(v, list)), [data])
        return pd.json_normalize(data)  # flattens nested objects
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(raw))
    return pd.read_csv(io.BytesIO(raw))


@st.cache_data(ttl=60)  # re-fetch the sheet at most once a minute
def load_url(url: str) -> pd.DataFrame:
    return pd.read_csv(url)


st.sidebar.header("Data source")
mode = st.sidebar.radio("Load from", ["Google Sheet (auto-updates)", "Upload file"])
df = None
try:
    if mode.startswith("Google"):
        url = st.sidebar.text_input("Published CSV link", help="Sheet > File > Share > Publish to web > CSV")
        if url:
            df = load_url(url)
        if st.sidebar.button("Refresh now"):
            load_url.clear(); st.rerun()
    else:
        f = st.sidebar.file_uploader("JSON, CSV or Excel", type=["json", "csv", "xlsx", "xls"])
        if f:
            df = to_df(f.getvalue(), f.name)
except Exception as e:
    st.error(f"Could not read the data: {e}")

if df is None:
    st.title("Data Dashboard")
    st.info("Pick a data source in the sidebar to begin.")
    st.stop()

plan = plan_dashboard(df) if st.session_state.get("cols") != list(df.columns) else st.session_state["plan"]
st.session_state["cols"], st.session_state["plan"] = list(df.columns), plan

st.title(plan["title"])
for col in plan["filter_columns"]:
    picked = st.sidebar.multiselect(col, sorted(df[col].dropna().unique()))
    if picked:
        df = df[df[col].isin(picked)]
q = st.sidebar.text_input("Search all columns")
if q:
    df = df[df.astype(str).apply(lambda r: r.str.contains(q, case=False).any(), axis=1)]

c1, c2 = st.columns(2)
c1.metric("Rows", len(df))
c2.metric("Columns", df.shape[1])

g, agg, val = plan["group_by"], plan["agg"], plan.get("value_column")
chart = df.groupby(g).size() if agg == "count" else df.groupby(g)[val].agg(agg)
st.subheader(f"{agg.title()} by {g}")
st.bar_chart(chart.sort_values(ascending=False))

if plan.get("lat_column") and plan.get("lon_column"):
    st.subheader("Map")
    st.map(df.rename(columns={plan["lat_column"]: "lat", plan["lon_column"]: "lon"})[["lat", "lon"]].dropna())

st.subheader("Data")
st.dataframe(df, use_container_width=True)
st.download_button("Download CSV", df.to_csv(index=False), "data.csv", "text/csv")
