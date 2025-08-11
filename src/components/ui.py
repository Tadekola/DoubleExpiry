"""
UI components for the Mechanical Options Trade Recommender application.
"""
import streamlit as st
from src.utils.helpers import status_color
from src.utils.ibkr_client import IBKRClient
import datetime as dt
import sys

def setup_page():
    """Configure the Streamlit page settings with improved styling."""
    # Set page configuration with custom theme and wide layout
    st.set_page_config(
        page_title="DoubleExpiry",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    # Apply custom CSS for better styling
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #475569;
        margin-bottom: 2rem;
    }
    .status-header {
        font-size: 1.5rem;
        font-weight: 600;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .metrics-container {
        background-color: #F8FAFC;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .decision-container {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        text-align: center;
    }
    .sidebar-header {
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .disclaimer {
        font-size: 0.8rem;
        color: #64748B;
        text-align: center;
        margin-top: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Main header with improved styling
    st.markdown('<h1 class="main-header">DoubleExpiry</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Enter your morning inputs. The app applies simple rules to decide: '
        'ENTER or WAIT. Supports SPY, QQQ, IWM.</p>', 
        unsafe_allow_html=True
    )

def render_sidebar():
    """
    Render the sidebar inputs and collect user input values.
    Implements improved UI organization with sections and tooltips.
    
    Returns:
        dict: Dictionary containing all user inputs
    """
    st.sidebar.markdown('<div class="sidebar-header">📈 Trading Inputs</div>', unsafe_allow_html=True)

    # Input mode toggle
    mode = st.sidebar.radio("Input Mode", ["Manual", "Auto (IBKR)"], horizontal=True)
    if "auto_data" not in st.session_state:
        st.session_state.auto_data = {}
    if "ibkr_last_updated" not in st.session_state:
        st.session_state.ibkr_last_updated = None

    # IBKR Auto fetch controls
    if mode == "Auto (IBKR)":
        with st.sidebar.expander("IBKR Connection", expanded=False):
            colA, colB, colC = st.columns([1,1,1])
            with colA:
                host = st.text_input("Host", value="127.0.0.1")
            with colB:
                port = st.number_input("Port", min_value=1, value=7497, step=1)
            with colC:
                client_id = st.number_input("Client ID", min_value=0, value=1, step=1)
            delayed = st.checkbox("Use Delayed Data", value=True, help="If you lack real-time permissions, use delayed market data (type 3)")
            do_refresh = st.button("🔄 Refresh IBKR Data")

            # Diagnostics: interpreter path and ib_insync status
            try:
                import importlib
                importlib.invalidate_caches()
                _ibm = __import__("ib_insync")
                ib_status = f"ok v{getattr(_ibm, '__version__', 'unknown')}"
            except Exception as _e:
                ib_status = f"import failed: {repr(_e)}"
            st.caption(f"Python: {sys.executable}")
            st.caption(f"ib_insync: {ib_status}")

        # Perform fetch when no cache or user refreshes
        need_fetch = do_refresh or not bool(st.session_state.auto_data)
        if need_fetch:
            client = IBKRClient(host=str(host), port=int(port), client_id=int(client_id), delayed=bool(delayed))
            # Underlying selection first to know symbol
            # Provide temporary default symbol for first render
            tmp_symbol = st.session_state.auto_data.get("symbol", "SPY")
            price_auto = client.get_underlying_price(tmp_symbol)
            if price_auto is None:
                st.sidebar.warning(
                    "Could not fetch underlying price from IBKR (permissions or data unavailable). "
                    "Use manual inputs or try 'Use Delayed Data' / verify market data subscriptions."
                )

            # Determine expirations
            front_exp, back_exp = IBKRClient.nearest_two_fridays()

            # If no strikes cached yet, seed around price
            put_auto = st.session_state.auto_data.get("put_strike")
            call_auto = st.session_state.auto_data.get("call_strike")
            if price_auto is not None and (put_auto is None or call_auto is None):
                # Round to nearest 5 and set +/- 10
                base = round(price_auto / 5) * 5
                put_auto = base - 10
                call_auto = base + 10

            # Fetch IVs if we have strikes
            ivs = {"front_put_iv": None, "front_call_iv": None, "back_put_iv": None, "back_call_iv": None}
            if price_auto is not None and put_auto is not None and call_auto is not None:
                ivs = client.get_option_ivs(tmp_symbol, front_exp, back_exp, float(put_auto), float(call_auto))

            # Fetch VIX (IBKR preferred; fall back to yfinance inside client)
            vix_val = client.get_vix()

            # Compute IV Rank (auto) with fallback
            iv_rank_auto = client.get_iv_rank(tmp_symbol)

            # Cache results
            st.session_state.auto_data.update({
                "symbol": tmp_symbol,
                "price": price_auto,
                "put_strike": put_auto,
                "call_strike": call_auto,
                **ivs,
                "vix_value": vix_val,
                "iv_rank_pct": iv_rank_auto,
                "front_expiry": front_exp.isoformat(),
                "back_expiry": back_exp.isoformat(),
            })
            st.session_state.ibkr_last_updated = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if st.session_state.ibkr_last_updated:
            st.sidebar.caption(f"Last updated: {st.session_state.ibkr_last_updated}")
    
    # Main inputs with tooltips and improved organization
    st.sidebar.markdown('##### Underlying Asset')
    symbol_default = st.session_state.auto_data.get("symbol", "SPY") if mode == "Auto (IBKR)" else "SPY"
    symbol = st.sidebar.selectbox(
        "Select ETF", 
        ["SPY", "QQQ", "IWM"], 
        index=["SPY","QQQ","IWM"].index(symbol_default) if symbol_default in ["SPY","QQQ","IWM"] else 0,
        help="Choose the ETF you're trading options on"
    )
    # If user changes symbol while in Auto mode, note it for next refresh
    if mode == "Auto (IBKR)":
        st.session_state.auto_data["symbol"] = symbol

    price_default = st.session_state.auto_data.get("price", 635.0) if mode == "Auto (IBKR)" else 635.0
    price = st.sidebar.number_input(
        f"{symbol} Current Price", 
        min_value=0.1, 
        value=float(price_default) if price_default is not None else 635.0, 
        step=0.1,
        help="Current market price of the selected ETF"
    )
    
    # Strike inputs with better formatting
    st.sidebar.markdown('##### Option Strikes')
    col1, col2 = st.sidebar.columns(2)
    with col1:
        put_default = st.session_state.auto_data.get("put_strike", 615.0) if mode == "Auto (IBKR)" else 615.0
        put_strike = st.number_input(
            "PUT Strike", 
            value=float(put_default) if put_default is not None else 615.0, 
            step=1.0,
            help="Strike price for your short put option"
        )
    with col2:
        call_default = st.session_state.auto_data.get("call_strike", 650.0) if mode == "Auto (IBKR)" else 650.0
        call_strike = st.number_input(
            "CALL Strike", 
            value=float(call_default) if call_default is not None else 650.0, 
            step=1.0,
            help="Strike price for your short call option"
        )
    
    # IV inputs with improved layout
    st.sidebar.markdown('---')
    st.sidebar.markdown('##### Implied Volatility Data')
    st.sidebar.caption("Use % numbers, e.g., 22 for 22%")
    
    # Front week IVs
    st.sidebar.markdown("**Front-week IV:**")
    fcol1, fcol2 = st.sidebar.columns(2)
    with fcol1:
        fput_default = st.session_state.auto_data.get("front_put_iv", 22.0) if mode == "Auto (IBKR)" else 22.0
        front_put_iv = st.number_input(
            "PUT IV %", 
            min_value=0.0, 
            value=float(fput_default) if fput_default is not None else 22.0, 
            step=0.1,
            key="front_put_iv",
            help="Front-week PUT implied volatility percentage"
        )
    with fcol2:
        fcall_default = st.session_state.auto_data.get("front_call_iv", 20.0) if mode == "Auto (IBKR)" else 20.0
        front_call_iv = st.number_input(
            "CALL IV %", 
            min_value=0.0, 
            value=float(fcall_default) if fcall_default is not None else 20.0, 
            step=0.1,
            key="front_call_iv",
            help="Front-week CALL implied volatility percentage"
        )
    
    # Back week IVs
    st.sidebar.markdown("**Back-week IV:**")
    bcol1, bcol2 = st.sidebar.columns(2)
    with bcol1:
        bput_default = st.session_state.auto_data.get("back_put_iv", 18.0) if mode == "Auto (IBKR)" else 18.0
        back_put_iv = st.number_input(
            "PUT IV %", 
            min_value=0.0, 
            value=float(bput_default) if bput_default is not None else 18.0, 
            step=0.1,
            key="back_put_iv",
            help="Back-week PUT implied volatility percentage"
        )
    with bcol2:
        bcall_default = st.session_state.auto_data.get("back_call_iv", 19.0) if mode == "Auto (IBKR)" else 19.0
        back_call_iv = st.number_input(
            "CALL IV %", 
            min_value=0.0, 
            value=float(bcall_default) if bcall_default is not None else 19.0, 
            step=0.1,
            key="back_call_iv",
            help="Back-week CALL implied volatility percentage"
        )
    
    # Other market data with improved organization
    st.sidebar.markdown('---')
    st.sidebar.markdown('##### Market Environment')
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        ivrank_default = st.session_state.auto_data.get("iv_rank_pct") if mode == "Auto (IBKR)" else None
        iv_rank_pct = st.number_input(
            "IV Rank (0-100%)", 
            min_value=0.0, 
            max_value=100.0, 
            value=float(ivrank_default) if ivrank_default is not None else 42.0, 
            step=0.1,
            help="Current IV Rank as a percentage (0-100)"
        )
    with col2:
        vix_default = st.session_state.auto_data.get("vix_value") if mode == "Auto (IBKR)" else None
        vix_value = st.number_input(
            "VIX Value", 
            min_value=0.0, 
            value=float(vix_default) if vix_default is not None else 17.5, 
            step=0.1,
            help="Current VIX index value"
        )
        
    days_to_event = st.sidebar.number_input(
        "Days to Major Event", 
        min_value=0, 
        value=4, 
        step=1,
        help="Days until next major market event (CPI/FOMC/tariff announcement)"
    )
    
    # Optional guardrail with better styling
    with st.sidebar.expander("📊 Volatility Guardrail"):
        st.markdown("**ATR-based Risk Control**")
        st.caption("Helps ensure position sizing matches current market volatility")
        atr_default = st.session_state.auto_data.get("atr_points") if mode == "Auto (IBKR)" else None
        atr_points = st.number_input(
            f"{symbol} ATR(5) Daily Points", 
            min_value=0.0, 
            value=float(atr_default) if atr_default is not None else 6.0, 
            step=0.1,
            help="Average True Range over 5 days in points"
        )
        use_atr = st.checkbox(
            "Enable ATR Guardrail", 
            value=False,
            help="Activates additional ATR-based risk control in the decision process"
        )
    
    # Return all inputs as a dictionary for easy access
    return {
        "symbol": symbol,
        "price": price,
        "put_strike": put_strike,
        "call_strike": call_strike,
        "front_put_iv": front_put_iv,
        "front_call_iv": front_call_iv,
        "back_put_iv": back_put_iv,
        "back_call_iv": back_call_iv,
        "iv_rank_pct": iv_rank_pct,
        "days_to_event": days_to_event,
        "vix_value": vix_value,
        "atr_points": atr_points,
        "use_atr": use_atr
    }

def render_metrics(metrics):
    """
    Display computed metrics in the main area with improved formatting and visualization.
    
    Args:
        metrics (dict): Dictionary of computed metrics
    """
    st.markdown('<h2 class="status-header">Computed Metrics</h2>', unsafe_allow_html=True)
    
    # Create a container with custom styling for metrics
    with st.container():
        st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="Position Midpoint", 
                value=f"${metrics['midpoint']:.2f}",
                help="Midpoint between put and call strikes"
            )
            st.metric(
                label="Strike Width", 
                value=f"${metrics['strike_width']:.2f}",
                help="Width between put and call strikes"
            )
            
        with col2:
            # Add delta indicators for IV metrics
            term_delta = metrics['term_gap_pts']
            front_avg = metrics['front_avg_iv']
            back_avg = metrics['back_avg_iv']
            
            st.metric(
                label="Front Avg IV", 
                value=f"{front_avg:.2f}%",
                delta=f"+{term_delta:.2f} pts" if term_delta > 0 else f"{term_delta:.2f} pts",
                delta_color="normal"
            )
            
            st.metric(
                label="Back Avg IV", 
                value=f"{back_avg:.2f}%"
            )
            
        with col3:
            # Calculate percentage distance from price to midpoint
            dist_pct = metrics['dist_from_mid']*100
            
            st.metric(
                label="Price to Midpoint", 
                value=f"{dist_pct:.2f}%",
                delta="Good" if dist_pct <= 1.0 else "Caution" if dist_pct <= 2.0 else "Too Far",
                delta_color="normal" if dist_pct <= 1.0 else "off" if dist_pct <= 2.0 else "inverse"
            )
            
            if metrics['use_atr']:
                st.metric(
                    label="ATR(5) Guardrail", 
                    value=f"${metrics['atr_points']:.2f}",
                    delta="OK" if metrics['atr_ok'] else "Too High",
                    delta_color="normal" if metrics['atr_ok'] else "inverse"
                )
        
        st.markdown('</div>', unsafe_allow_html=True)

def render_status_lights(statuses):
    """
    Render the status lights section with improved visual indicators.
    
    Args:
        statuses (dict): Dictionary of status labels
    """
    st.markdown('<h2 class="status-header">Status Lights</h2>', unsafe_allow_html=True)
    
    # Create status light indicators with better visual styling
    cols = st.columns(len(statuses))
    for i, (name, label) in enumerate(statuses.items()):
        with cols[i]:
            # Add emoji indicators for better visual feedback
            emoji = "🟢" if label == "GREEN" else "🟡" if label == "YELLOW" else "🔴"
            
            st.markdown(f"""
            <div style="text-align: center; padding: 10px; border-radius: 5px; background-color: #F8F9FA;">
                <div style="font-size: 2rem; margin-bottom: 5px;">{emoji}</div>
                <div style="font-weight: bold;">{name}</div>
                <div style="margin-top: 5px;"><span style='{status_color(label)}'>{label}</span></div>
            </div>
            """, unsafe_allow_html=True)

def render_decision(decision):
    """
    Render the final decision section with improved styling.
    
    Args:
        decision (str): Final decision text
    """
    st.markdown("---")
    st.markdown('<h2 class="status-header">Final Decision</h2>', unsafe_allow_html=True)
    
    # Style based on the decision type
    decision_style = ""
    if "ENTER (All green)" in decision:
        decision_style = "background-color: #DCFCE7; color: #166534;"
    elif "ENTER — CAUTION" in decision:
        decision_style = "background-color: #FEF9C3; color: #854D0E;"
    else:  # WAIT
        decision_style = "background-color: #FEE2E2; color: #991B1B;"
    
    st.markdown(f"""
    <div class="decision-container" style="{decision_style}">
        <h2>{decision}</h2>
    </div>
    """, unsafe_allow_html=True)

def render_suggestions(suggestions):
    """
    Render trading strategy suggestions with improved formatting.
    
    Args:
        suggestions (list): List of strategy suggestions
    """
    st.markdown('<h2 class="status-header">Suggested Strategies</h2>', unsafe_allow_html=True)
    
    if suggestions:
        # Create expandable sections for each strategy with explanations
        for i, suggestion in enumerate(suggestions):
            if "Double Calendar" in suggestion:
                with st.expander(f"💼 {suggestion}"):
                    st.markdown("""
                    **Double Calendar Strategy**
                    - **Setup**: Sell front-week options, buy back-week options at same strikes
                    - **Profit From**: Time decay and volatility expansion
                    - **Risk**: Rapid price movement beyond your strikes
                    - **Ideal For**: Current market conditions with good IV term structure
                    """)
            elif "OTM Vertical" in suggestion:
                with st.expander(f"📈 {suggestion}"):
                    st.markdown("""
                    **OTM Vertical Strategy**
                    - **Setup**: Bull/bear credit or debit spread
                    - **Profit From**: Price movement in expected direction
                    - **Risk**: Price moves against your direction
                    - **Ideal For**: Lower IV environments with directional bias
                    """)
            elif "Iron Condor" in suggestion:
                with st.expander(f"🦅 {suggestion}"):
                    st.markdown("""
                    **Iron Condor Strategy**
                    - **Setup**: Sell OTM put spread and OTM call spread
                    - **Profit From**: Price staying within your short strikes
                    - **Risk**: Large price movement in either direction
                    - **Ideal For**: Higher IV environments with range-bound expectations
                    """)
            else:
                with st.expander(f"ℹ️ {suggestion}"):
                    st.write("Follow the recommendation based on current market conditions.")
    else:
        st.info("No specific strategy suggestions available based on current market conditions.")
    
    # Add disclaimer with better styling
    st.markdown('<p class="disclaimer">Educational tool only. Not financial advice.</p>', unsafe_allow_html=True)
