"""
app.py — Streamlit Dashboard for IPO GMP Predictor
Matches the dark theme UI from the screenshots exactly.
"""

import sys
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.db_manager import (
    fetch_scores_latest, fetch_gmp_trend, fetch_gmp_latest,
    fetch_score_history, fetch_model_performance,
    fetch_performance_history, fetch_raw_gmp_data,
)
from pipeline.run_pipeline import run as run_pipeline
from scorer.scoring_engine import MAX_TOTAL

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IPO GMP Predictor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS (dark theme matching screenshots) ──────────────────────────────
st.markdown("""
<style>
  /* Dark background */
  .stApp { background-color: #0e1117; }
  section[data-testid="stSidebar"] { background-color: #161b22; }

  /* Signal badge colours */
  .badge-STRONG-BUY  { background:#00c853;color:#fff;padding:3px 10px;border-radius:5px;font-size:12px;font-weight:700 }
  .badge-BUY         { background:#1db954;color:#fff;padding:3px 10px;border-radius:5px;font-size:12px;font-weight:700 }
  .badge-HOLD        { background:#2979ff;color:#fff;padding:3px 10px;border-radius:5px;font-size:12px;font-weight:700 }
  .badge-WEAK        { background:#ff6d00;color:#fff;padding:3px 10px;border-radius:5px;font-size:12px;font-weight:700 }
  .badge-AVOID       { background:#d50000;color:#fff;padding:3px 10px;border-radius:5px;font-size:12px;font-weight:700 }

  /* Top IPO card */
  .top-ipo-card {
    background: linear-gradient(135deg, #0d2b1a 0%, #0a3d2b 100%);
    border: 1px solid #1db954;
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 16px;
  }
  .top-ipo-card h2 { color: #00e676; margin: 4px 0 8px 0; font-size: 26px; }
  .top-ipo-card p  { color: #b2dfdb; margin: 4px 0; font-size: 14px; }

  /* Metric cards */
  div[data-testid="metric-container"] {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px 16px;
  }
</style>
""", unsafe_allow_html=True)


# ── Signal badge helper ───────────────────────────────────────────────────────
def signal_badge(signal: str) -> str:
    cls = f"badge-{signal.replace(' ', '-')}"
    return f'<span class="{cls}">{signal}</span>'


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Controls")

    if st.button("🔄 Scrape + Score Now", type="primary", use_container_width=True):
        with st.spinner("Running pipeline..."):
            try:
                run_pipeline()
                st.success("Pipeline complete!")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Pipeline error: {e}")

    st.divider()

    # Scoring factors legend
    st.markdown("**Scoring factors**")
    factors_df = pd.DataFrame({
        "Factor": ["GMP %", "Trend", "Status", "Listing"],
        "Max":    [15,       10,      10,       5],
    })
    st.dataframe(factors_df, hide_index=True, use_container_width=True)
    st.caption(f"Total max = {MAX_TOTAL} pts")

    st.divider()

    # Signal legend
    st.markdown("**Signal legend**")
    for sig, col in [("STRONG BUY","#00c853"),("BUY","#1db954"),
                     ("HOLD","#2979ff"),("WEAK","#ff6d00"),("AVOID","#d50000")]:
        st.markdown(
            f'<span style="background:{col};color:#fff;padding:2px 10px;'
            f'border-radius:4px;font-size:12px;font-weight:700">{sig}</span>',
            unsafe_allow_html=True,
        )

    st.divider()

    min_conf = st.slider("Min Confidence %", 0, 95, 0, 5)

    show_signals = st.multiselect(
        "Show signals",
        ["STRONG BUY", "BUY", "HOLD", "WEAK", "AVOID"],
        default=["STRONG BUY", "BUY", "HOLD", "WEAK", "AVOID"],
    )


# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def load_scores():
    try:
        return fetch_scores_latest()
    except Exception:
        return []

@st.cache_data(ttl=120)
def load_trend(name=None):
    try:
        return fetch_gmp_trend(name)
    except Exception:
        return []

@st.cache_data(ttl=120)
def load_model_perf():
    try:
        return fetch_model_performance()
    except Exception:
        return {}

@st.cache_data(ttl=120)
def load_perf_history():
    try:
        return fetch_performance_history()
    except Exception:
        return []

@st.cache_data(ttl=120)
def load_raw():
    try:
        return fetch_raw_gmp_data(500)
    except Exception:
        return []


scores_raw   = load_scores()
perf_kpi     = load_model_perf()
perf_history = load_perf_history()
raw_gmp      = load_raw()

# Apply sidebar filters
scores_filtered = [
    s for s in scores_raw
    if s.get("signal") in show_signals
    and (s.get("confidence") or 0) >= min_conf
]

scores_df = pd.DataFrame(scores_filtered) if scores_filtered else pd.DataFrame()

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📈 IPO GMP Predictor")
st.caption("Grey Market Premium based listing prediction — Data: investorgain.com")

# ── Top IPO Opportunity ───────────────────────────────────────────────────────
if scores_raw:
    top = max(scores_raw, key=lambda x: x.get("score", 0))
    badge_color = {"STRONG BUY": "#00c853", "BUY": "#1db954", "HOLD": "#2979ff",
                   "WEAK": "#ff6d00", "AVOID": "#d50000"}.get(top.get("signal",""), "#888")
    st.markdown(f"""
    <div class="top-ipo-card">
      <div style="font-size:20px;font-weight:700;color:#b2dfdb">🏆 Top IPO Opportunity</div>
      <h2>{top.get("ipo_name", "N/A")}</h2>
      <p>
        Score: <strong style="color:#eee">{top.get("score",0):.1f}/{MAX_TOTAL}</strong>
        &nbsp;|&nbsp; Signal:
        <span style="background:{badge_color};color:#fff;padding:2px 8px;border-radius:4px;
                     font-size:13px;font-weight:700">{top.get("signal","")}</span>
        &nbsp;|&nbsp; Confidence: <strong style="color:#eee">{top.get("confidence",0):.0f}%</strong>
      </p>
      <p style="color:#80cbc4">{top.get("reasons","")}</p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.info("No score data yet — click **Scrape + Score Now** to start.")

# ── Market Overview ───────────────────────────────────────────────────────────
st.subheader("📊 Market Overview")

if scores_raw:
    sig_counts = {s: 0 for s in ["STRONG BUY","BUY","HOLD","WEAK","AVOID"]}
    for s in scores_raw:
        sig = s.get("signal","")
        if sig in sig_counts:
            sig_counts[sig] += 1

    avg_conf  = sum(s.get("confidence",0) for s in scores_raw) / len(scores_raw)
    avg_score = sum(s.get("score",0) for s in scores_raw) / len(scores_raw)

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("Total IPOs",       len(scores_raw))
    c2.metric("🚀 Strong Buy",    sig_counts["STRONG BUY"])
    c3.metric("✅ Buy",           sig_counts["BUY"])
    c4.metric("🔲 Hold/Neutral",  sig_counts["HOLD"])
    c5.metric("🔴 Weak/Avoid",    sig_counts["WEAK"] + sig_counts["AVOID"])
    c6.metric("Avg Confidence",   f"{avg_conf:.0f}%")
    c7.metric("Avg Score",        f"{avg_score:.1f}/{MAX_TOTAL}")

# ── IPO Scoreboard ────────────────────────────────────────────────────────────
st.subheader("📋 IPO Scoreboard")

if not scores_df.empty:
    display_cols = ["ipo_name", "score", "signal", "confidence", "reasons", "scored_at"]
    existing = [c for c in display_cols if c in scores_df.columns]
    tbl = scores_df[existing].copy()

    # Format signal as HTML badge
    if "signal" in tbl.columns:
        tbl["signal"] = tbl["signal"].apply(signal_badge)

    if "scored_at" in tbl.columns:
        tbl["scored_at"] = pd.to_datetime(tbl["scored_at"]).dt.strftime("%Y-%m-%d %H:%M")

    tbl = tbl.rename(columns={
        "ipo_name": "IPO Name", "score": "Score", "signal": "Signal",
        "confidence": "Conf %", "reasons": "Reason", "scored_at": "Scored At"
    })

    # Merge with GMP latest for price band + est gain + status
    latest_raw = load_trend()
    if latest_raw:
        latest_df  = pd.DataFrame(latest_raw)
        if not latest_df.empty and "ipo_name" in latest_df.columns:
            latest_latest = latest_df.sort_values("scraped_at").groupby("ipo_name").last().reset_index()
            extra = latest_latest[["ipo_name","gmp_percent","price_band","est_listing_gain","ipo_status"]].copy()
            extra = extra.rename(columns={
                "ipo_name": "IPO Name", "gmp_percent": "GMP %",
                "price_band": "Price Band (₹)", "est_listing_gain": "Est. Gain %",
                "ipo_status": "Status",
            })
            tbl = tbl.merge(extra, on="IPO Name", how="left")

    st.write(tbl.to_html(escape=False, index=False), unsafe_allow_html=True)
else:
    st.info("No IPOs match current filters.")

# ── Score Breakdown Chart ─────────────────────────────────────────────────────
st.subheader("🔍 Score Breakdown")

if not scores_df.empty:
    breakdown_cols = ["ipo_name","gmp_score","listing_score","status_score","trend_score"]
    bc = [c for c in breakdown_cols if c in scores_df.columns]
    if len(bc) > 1:
        melt = scores_df[bc].melt(id_vars="ipo_name", var_name="color", value_name="value")
        melt["color"] = melt["color"].str.replace("_score","").str.title()
        fig = px.bar(
            melt, x="ipo_name", y="value", color="color",
            barmode="stack",
            color_discrete_map={"Gmp":"#2979ff","Listing":"#80deea","Status":"#ef9a9a","Trend":"#ef5350"},
            labels={"ipo_name":"", "value":"Score", "color":""},
            template="plotly_dark",
        )
        fig.update_layout(
            plot_bgcolor="#161b22", paper_bgcolor="#0e1117",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(t=20, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)

# ── GMP Trend — Individual IPO ────────────────────────────────────────────────
st.subheader("📈 GMP Trend — Individual IPO")

all_names = sorted(set(s.get("ipo_name","") for s in scores_raw)) if scores_raw else []
if all_names:
    selected_ipo = st.selectbox("Select IPO", all_names)
    trend_data   = load_trend(selected_ipo)

    if trend_data:
        trend_df = pd.DataFrame(trend_data)
        trend_df["scraped_at"] = pd.to_datetime(trend_df["scraped_at"])

        col_a, col_b = st.columns(2)

        with col_a:
            st.caption("GMP % over time")
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(
                x=trend_df["scraped_at"], y=trend_df["gmp_percent"],
                mode="lines+markers", name="gmp_percent",
                line=dict(color="#2979ff", width=2),
            ))
            if "prev_gmp" in trend_df.columns:
                fig1.add_trace(go.Scatter(
                    x=trend_df["scraped_at"], y=trend_df["prev_gmp"],
                    mode="lines", name="prev_gmp",
                    line=dict(color="#80cbc4", width=1, dash="dot"),
                ))
            fig1.update_layout(
                template="plotly_dark", plot_bgcolor="#161b22", paper_bgcolor="#0e1117",
                margin=dict(t=10, b=40, l=40, r=10), height=250,
                legend=dict(orientation="h"),
            )
            st.plotly_chart(fig1, use_container_width=True)

        with col_b:
            st.caption("GMP Delta (change per scrape)")
            if "gmp_delta" in trend_df.columns:
                fig2 = go.Figure(go.Bar(
                    x=trend_df["scraped_at"],
                    y=trend_df["gmp_delta"],
                    marker_color=["#00e676" if v and v >= 0 else "#ef5350"
                                  for v in trend_df["gmp_delta"].fillna(0)],
                ))
                fig2.update_layout(
                    template="plotly_dark", plot_bgcolor="#161b22", paper_bgcolor="#0e1117",
                    margin=dict(t=10, b=40, l=40, r=10), height=250,
                )
                st.plotly_chart(fig2, use_container_width=True)

        # Score history
        st.caption(f"Score history — {selected_ipo}")
        try:
            sh = fetch_score_history(selected_ipo)
            if sh:
                sh_df = pd.DataFrame(sh)
                sh_df["scored_at"] = pd.to_datetime(sh_df["scored_at"])
                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(
                    x=sh_df["scored_at"], y=sh_df["confidence"],
                    mode="lines", name="confidence",
                    line=dict(color="#2979ff"),
                ))
                fig3.add_trace(go.Scatter(
                    x=sh_df["scored_at"], y=sh_df["score"],
                    mode="lines", name="score",
                    line=dict(color="#00e676"),
                ))
                fig3.update_layout(
                    template="plotly_dark", plot_bgcolor="#161b22", paper_bgcolor="#0e1117",
                    margin=dict(t=10, b=40, l=40, r=10), height=220,
                    legend=dict(orientation="h"),
                )
                st.plotly_chart(fig3, use_container_width=True)
        except Exception:
            pass

        with st.expander("📊 Raw score history table"):
            try:
                sh2 = fetch_score_history(selected_ipo)
                if sh2:
                    st.dataframe(pd.DataFrame(sh2), use_container_width=True)
            except Exception:
                st.info("No score history.")

# ── Model Performance ─────────────────────────────────────────────────────────
st.subheader("🎯 Model Performance")

if perf_kpi:
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Predictions Tracked",  perf_kpi.get("predictions_tracked", 0))
    p2.metric("Direction Accuracy",   f"{perf_kpi.get('direction_accuracy', 0)}%")
    p3.metric("Avg Absolute Error",   f"{perf_kpi.get('avg_absolute_error', 0)}%")
    p4.metric("Tracking Since",       str(perf_kpi.get("tracking_since", "—")))

if perf_history:
    perf_df = pd.DataFrame(perf_history)

    st.markdown("**Prediction vs Actual**")
    disp = perf_df.copy()
    if "correct_direction" in disp.columns:
        disp["correct_direction"] = disp["correct_direction"].apply(
            lambda x: "✅ Yes" if x else "❌ No"
        )
    if "tracked_at" in disp.columns:
        disp["tracked_at"] = pd.to_datetime(disp["tracked_at"]).dt.strftime("%Y-%m-%d %H:%M")

    rename_map = {
        "ipo_name": "IPO Name", "predicted_gain": "Predicted Gain",
        "actual_gain": "Actual Gain", "abs_error": "Abs Error",
        "correct_direction": "Correct Direction", "tracked_at": "Tracked At",
    }
    disp = disp.rename(columns={k: v for k, v in rename_map.items() if k in disp.columns})
    show_cols = ["IPO Name","Predicted Gain","Actual Gain","Abs Error","Correct Direction","Tracked At"]
    show_cols = [c for c in show_cols if c in disp.columns]
    st.dataframe(disp[show_cols], use_container_width=True, hide_index=True)

    # Error distribution histogram
    if "abs_error" in perf_df.columns:
        st.markdown("**Error distribution**")
        fig_err = px.histogram(
            perf_df, x="abs_error",
            nbins=10,
            template="plotly_dark",
            color_discrete_sequence=["#80deea"],
        )
        fig_err.update_layout(
            plot_bgcolor="#161b22", paper_bgcolor="#0e1117",
            margin=dict(t=10, b=40), height=280,
            xaxis_title="Abs Error (%)", yaxis_title="Count",
        )
        st.plotly_chart(fig_err, use_container_width=True)
else:
    st.info("No performance data yet.")

# ── Raw GMP Data ──────────────────────────────────────────────────────────────
with st.expander("📋 Raw GMP Data"):
    if raw_gmp:
        st.dataframe(pd.DataFrame(raw_gmp), use_container_width=True)
    else:
        st.info("No raw data available.")

# ── Footer ────────────────────────────────────────────────────────────────────
last_refresh = scores_raw[0].get("scored_at", "—") if scores_raw else "—"
st.caption(
    f"Last refreshed: {last_refresh} | Data: investorgain.com | Not financial advice"
)
