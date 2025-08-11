import streamlit as st

# ===============================
# dOUBLE CALENDER RECOMMENDER
# ===============================

st.set_page_config(page_title="dOUBLE CALENDER RECOMMENDER", layout="wide")

st.title("dOUBLE CALENDER RECOMMENDER")
st.caption("Enter your morning inputs. The app applies simple rules to decide: ENTER or WAIT. Supports SPY, QQQ, IWM.")

# -------------------------------
# Helper functions
# -------------------------------
def status_color(label):
    colors = {"GREEN": "#C6EFCE", "YELLOW": "#FFF2CC", "RED": "#F8CBAD"}
    return f"background-color:{colors.get(label,'#FFFFFF')}; padding:6px; border-radius:6px;"

def traffic(value, green_fn, yellow_fn):
    if green_fn(value):
        return "GREEN"
    elif yellow_fn(value):
        return "YELLOW"
    else:
        return "RED"

def final_decision(statuses):
    score_map = {"GREEN": 2, "YELLOW": 1, "RED": 0}
    score = sum(score_map[s] for s in statuses.values())
    reds = sum(1 for s in statuses.values() if s == "RED")
    n = len(statuses)
    if score == 2 * n and reds == 0:
        return "ENTER (All green) ✅"
    elif score >= 2 * (n - 1) and reds == 0:
        return "ENTER — CAUTION ⚠️"
    else:
        return "WAIT ❌"

# -------------------------------
# Sidebar inputs
# -------------------------------
st.sidebar.header("Inputs")

symbol = st.sidebar.selectbox("Underlying", ["SPY", "QQQ", "IWM"], index=0)

price = st.sidebar.number_input(f"{symbol} Price", min_value=0.0, value=635.0, step=0.1)

# Strikes you plan to SELL for the FRONT week
put_strike = st.sidebar.number_input("Short PUT Strike (front week)", value=615.0, step=1.0)
call_strike = st.sidebar.number_input("Short CALL Strike (front week)", value=650.0, step=1.0)

st.sidebar.markdown("---")
st.sidebar.write("Front and Back IV inputs (use % numbers, e.g., 22 for 22%)")
front_put_iv = st.sidebar.number_input("Front-week PUT IV %", min_value=0.0, value=22.0, step=0.1)
front_call_iv = st.sidebar.number_input("Front-week CALL IV %", min_value=0.0, value=20.0, step=0.1)
back_put_iv = st.sidebar.number_input("Back-week PUT IV %", min_value=0.0, value=18.0, step=0.1)
back_call_iv = st.sidebar.number_input("Back-week CALL IV %", min_value=0.0, value=19.0, step=0.1)

st.sidebar.markdown("---")
iv_rank_pct = st.sidebar.number_input("IV Rank (0-100%)", min_value=0.0, max_value=100.0, value=42.0, step=0.1)
days_to_event = st.sidebar.number_input("Days to major event (CPI/FOMC/tariff)", min_value=0, value=4, step=1)
vix_value = st.sidebar.number_input("VIX value", min_value=0.0, value=17.5, step=0.1)

with st.sidebar.expander("Optional guardrail"):
    atr_points = st.number_input(f"{symbol} ATR(5) daily points", min_value=0.0, value=6.0, step=0.1)
    use_atr = st.checkbox("Enable ATR guardrail in decision", value=False)

# -------------------------------
# Computations
# -------------------------------
midpoint = (put_strike + call_strike) / 2.0
dist_from_mid = abs(price - midpoint) / midpoint if midpoint else 1.0  # fraction
strike_width = abs(call_strike - put_strike)

front_avg_iv = (front_put_iv + front_call_iv) / 2.0  # %
back_avg_iv = (back_put_iv + back_call_iv) / 2.0     # %
term_gap_pts = front_avg_iv - back_avg_iv            # percentage points (IV pts)

iv_rank = iv_rank_pct / 100.0  # convert to 0-1 for rules
atr_ok = atr_points <= max(1e-9, strike_width / 2.0)  # simple volatility guardrail

# -------------------------------
# Status lights (rules)
# -------------------------------
statuses = {}

# Price location rule: within +/-1% ideal, +/-2% acceptable
statuses["Price Location"] = traffic(
    dist_from_mid,
    green_fn=lambda x: x <= 0.01,
    yellow_fn=lambda x: x <= 0.02,
)

# Term structure rule: front avg IV at least 2 pts over back avg IV
statuses["Term Structure"] = traffic(
    term_gap_pts,
    green_fn=lambda x: x >= 2.0,
    yellow_fn=lambda x: x >= 1.0,
)

# IV Rank rule: 30-50% ideal; 20-29% or 51-60% caution
statuses["IV Rank"] = traffic(
    iv_rank,
    green_fn=lambda x: 0.30 <= x <= 0.50,
    yellow_fn=lambda x: (0.20 <= x < 0.30) or (0.50 < x <= 0.60),
)

# Event proximity: 3-7 days ideal; 1-2 days caution
statuses["Event Proximity"] = traffic(
    days_to_event,
    green_fn=lambda x: 3 <= x <= 7,
    yellow_fn=lambda x: 1 <= x <= 2,
)

# VIX band: 14-20 ideal; 20-25 caution
statuses["VIX"] = traffic(
    vix_value,
    green_fn=lambda x: 14 <= x <= 20,
    yellow_fn=lambda x: 20 < x <= 25,
)

# Optional ATR guardrail
if use_atr:
    statuses["ATR Guardrail"] = traffic(
        atr_ok,
        green_fn=lambda ok: ok is True,
        yellow_fn=lambda ok: False,  # no yellow state; either OK or RED
    )

# -------------------------------
# Display computed metrics
# -------------------------------
st.subheader("Computed Metrics")
left, right = st.columns(2)

with left:
    st.write(f"Midpoint: **{midpoint:.2f}**")
    st.write(f"Distance from midpoint: **{dist_from_mid*100:.2f}%**")
    st.write(f"Strike width: **{strike_width:.2f}**")

with right:
    st.write(f"Front Avg IV: **{front_avg_iv:.2f}%**")
    st.write(f"Back Avg IV: **{back_avg_iv:.2f}%**")
    st.write(f"Term structure gap (front - back): **{term_gap_pts:.2f} IV pts**")

if use_atr:
    st.write(f"ATR(5): **{atr_points:.2f}**  -> Guardrail {'OK' if atr_ok else 'Too High'}")

# -------------------------------
# Status lights UI
# -------------------------------
st.subheader("Status Lights")
for name, label in statuses.items():
    st.markdown(f"**{name}:** <span style='{status_color(label)}'>{label}</span>", unsafe_allow_html=True)

# -------------------------------
# Final decision
# -------------------------------
st.markdown("---")
st.subheader("Final Decision")
decision = final_decision(statuses)
st.markdown(f"### {decision}")

# -------------------------------
# Strategy suggestion (simple)
# -------------------------------
st.subheader("Suggested Strategy (rule-based)")
suggestions = []
if statuses.get("IV Rank") == "GREEN" and statuses.get("Term Structure") in ("GREEN", "YELLOW") and statuses.get("Price Location") != "RED":
    suggestions.append("Double Calendar (front week vs back week)")
if iv_rank < 0.25 and statuses.get("Price Location") == "GREEN":
    suggestions.append("Cheaper OTM Vertical (directional)")
if 0.45 < iv_rank <= 0.60 and vix_value >= 18 and statuses.get("Price Location") == "GREEN":
    suggestions.append("Short-duration Iron Condor (range)")

if not suggestions:
    suggestions.append("No trade — wait for better IV/term structure or re-center strikes")

st.write(" • " + " | ".join(suggestions))
st.caption("Educational tool only. Not financial advice.")
