"""
NSE Options Trading Analysis - Streamlit Web App
Strategy 1: Short Straddle Analysis
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from collections import defaultdict
from time import sleep
from nse_api import NSEDataFetcher

# Page configuration
st.set_page_config(
    page_title="NSE Profitinator",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Preferences file path
PREFERENCES_FILE = "cache/preferences.json"

# Default preferences
DEFAULT_PREFERENCES = {
    "stock_list": ["PNB", "BHEL", "NTPC", "BEL", "IOC", "TATASTEEL"],
    "chosenmonths": ["Dec"],
    "sort_by": "ROI",
    "atm_range_lower": 0.98,
    "atm_range_upper": 1.05,
    "margin": 0.25,
    "auto_refresh": True
}

# All F&O stocks (common ones - can be expanded)
ALL_FO_STOCKS = [
    "AARTIIND", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ACC", "ADANIENT", "ADANIPORTS", 
    "ALKEM", "AMBUJACEM", "APOLLOHOSP", "APOLLOTYRE", "ASHOKLEY", "ASIANPAINT", "ASTRAL",
    "ATUL", "AUBANK", "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE",
    "BALKRISIND", "BALRAMCHIN", "BANDHANBNK", "BANKBARODA", "BATAINDIA", "BEL", "BERGEPAINT",
    "BHARATFORG", "BHARTIARTL", "BHEL", "BIOCON", "BOSCHLTD", "BPCL", "BRITANNIA", "BSOFT",
    "CANBK", "CANFINHOME", "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA", "COFORGE", "COLPAL",
    "CONCOR", "COROMANDEL", "CROMPTON", "CUB", "CUMMINSIND", "DABUR", "DALBHARAT", "DEEPAKNTR",
    "DELTACORP", "DIVISLAB", "DIXON", "DLF", "DRREDDY", "EICHERMOT", "ESCORTS", "EXIDEIND",
    "FEDERALBNK", "GAIL", "GLENMARK", "GMRINFRA", "GNFC", "GODREJCP", "GODREJPROP", "GRANULES",
    "GRASIM", "GUJGASLTD", "HAL", "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE",
    "HEROMOTOCO", "HINDALCO", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "ICICIBANK", "ICICIGI",
    "ICICIPRULI", "IDEA", "IDFC", "IDFCFIRSTB", "IEX", "IGL", "INDHOTEL", "INDIACEM", "INDIAMART",
    "INDIGO", "INDUSINDBK", "INDUSTOWER", "INFY", "IOC", "IPCALAB", "IRCTC", "ITC", "JINDALSTEL",
    "JKCEMENT", "JSWSTEEL", "JUBLFOOD", "KOTAKBANK", "L&TFH", "LALPATHLAB", "LAURUSLABS", "LICHSGFIN",
    "LT", "LTI", "LTTS", "LUPIN", "M&M", "M&MFIN", "MANAPPURAM", "MARICO", "MARUTI", "MCDOWELL-N",
    "MCX", "METROPOLIS", "MFSL", "MGL", "MOTHERSON", "MPHASIS", "MRF", "MUTHOOTFIN", "NATIONALUM",
    "NAUKRI", "NAVINFLUOR", "NESTLEIND", "NMDC", "NTPC", "OBEROIRLTY", "OFSS", "ONGC", "PAGEIND",
    "PEL", "PERSISTENT", "PETRONET", "PFC", "PIDILITIND", "PIIND", "PNB", "POLYCAB", "POWERGRID",
    "PVRINOX", "RAMCOCEM", "RBLBANK", "RECLTD", "RELIANCE", "SAIL", "SBICARD", "SBILIFE", "SBIN",
    "SHREECEM", "SIEMENS", "SRF", "SUNPHARMA", "SUNTV", "SYNGENE", "TATACHEM", "TATACOMM",
    "TATACONSUM", "TATAMOTORS", "TATAPOWER", "TATASTEEL", "TCS", "TECHM", "TITAN", "TORNTPHARM",
    "TRENT", "TVSMOTOR", "UBL", "ULTRACEMCO", "UPL", "VEDL", "VOLTAS", "WIPRO", "ZEEL", "ZYDUSLIFE"
]

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def load_preferences():
    """Load preferences from JSON file"""
    if os.path.exists(PREFERENCES_FILE):
        try:
            with open(PREFERENCES_FILE, 'r') as f:
                return json.load(f)
        except:
            return DEFAULT_PREFERENCES.copy()
    return DEFAULT_PREFERENCES.copy()

def save_preferences(prefs):
    """Save preferences to JSON file"""
    with open(PREFERENCES_FILE, 'w') as f:
        json.dump(prefs, f, indent=2)

# Load preferences
if 'preferences' not in st.session_state:
    st.session_state.preferences = load_preferences()

# Initialize NSE fetcher (cached)
@st.cache_resource
def get_fetcher():
    return NSEDataFetcher()

# Sidebar configuration
st.sidebar.title("⚙️ Configuration")

# Stock selection
selected_stocks = st.sidebar.multiselect(
    "Select Stocks",
    options=sorted(ALL_FO_STOCKS),
    default=st.session_state.preferences.get("stock_list", DEFAULT_PREFERENCES["stock_list"]),
    help="Choose one or more stocks to analyze"
)

# Month selection
selected_months = st.sidebar.multiselect(
    "Expiry Months",
    options=MONTHS,
    default=st.session_state.preferences.get("chosenmonths", DEFAULT_PREFERENCES["chosenmonths"]),
    help="Select expiry months to analyze"
)

# ATM range
st.sidebar.subheader("ATM Range")
atm_lower = st.sidebar.number_input(
    "Lower Bound (%)",
    min_value=0.50,
    max_value=1.00,
    value=st.session_state.preferences.get("atm_range_lower", DEFAULT_PREFERENCES["atm_range_lower"]),
    step=0.01,
    format="%.2f",
    help="Lower bound of ATM range (e.g., 0.98 = 98% of current price)"
)

atm_upper = st.sidebar.number_input(
    "Upper Bound (%)",
    min_value=1.00,
    max_value=2.00,
    value=st.session_state.preferences.get("atm_range_upper", DEFAULT_PREFERENCES["atm_range_upper"]),
    step=0.01,
    format="%.2f",
    help="Upper bound of ATM range (e.g., 1.05 = 105% of current price)"
)

# Margin requirement
st.sidebar.subheader("Margin")
margin = st.sidebar.number_input(
    "Margin Required",
    min_value=0.10,
    max_value=1.00,
    value=st.session_state.preferences.get("margin", DEFAULT_PREFERENCES["margin"]),
    step=0.05,
    format="%.2f",
    help="Margin required to sell a CALL/PUT (0.25 = 25%)."
)

# Sort by
sort_by = st.sidebar.selectbox(
    "Sort By",
    options=["ROI", "Normal"],
    index=0 if st.session_state.preferences.get("sort_by", "ROI") == "ROI" else 1,
    help="Sort opportunities by ROI or normal order"
)

# Auto-refresh toggle
auto_refresh = st.sidebar.checkbox(
    "Auto-refresh (30s)",
    value=st.session_state.preferences.get("auto_refresh", True),
    help="Automatically refresh data every 30 seconds"
)

# Save preferences button here
if st.sidebar.button("💾 Save Preferences"):
    new_prefs = {
        "stock_list": selected_stocks,
        "chosenmonths": selected_months,
        "sort_by": sort_by,
        "atm_range_lower": atm_lower,
        "atm_range_upper": atm_upper,
        "margin": margin,
        "auto_refresh": auto_refresh
    }
    save_preferences(new_prefs)
    st.session_state.preferences = new_prefs
    st.sidebar.success("✓ Preferences saved!")

# Main content
st.title("📈 NSE Options Trading Analysis")

# Info section
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Stocks", len(selected_stocks))
with col2:
    st.metric("Months", len(selected_months))
with col3:
    st.metric("ATM Range", f"{atm_lower*100:.0f}%-{atm_upper*100:.0f}%")
with col4:
    st.metric("Last Update", datetime.now().strftime('%H:%M:%S'))

st.divider()

st.subheader("Strategy 1: Short Straddle")
st.markdown("Sell a CALL and a PUT at the same strike price.")
st.markdown("Ideal for Low Volatility.")

# Validation
if not selected_stocks:
    st.warning("⚠️ Please select at least one stock from the sidebar.")
    st.stop()

if not selected_months:
    st.warning("⚠️ Please select at least one expiry month from the sidebar.")
    st.stop()

# Placeholder for data
data_placeholder = st.empty()
status_placeholder = st.empty()

# Fetch and display data
try:
    fetcher = get_fetcher()
    all_opportunities = []
    
    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Fetch data for each stock
    for idx, symbol in enumerate(selected_stocks):
        status_text.text(f"Processing {symbol}... ({idx+1}/{len(selected_stocks)})")
        progress_bar.progress((idx + 1) / len(selected_stocks))
        
        try:
            # Get current price and options
            current_price = fetcher.get_stock_price(symbol)
            lot_size = fetcher.get_lot_size(symbol)
            
            if current_price == 0:
                continue
            
            # Get options for chosen months
            for month in selected_months:
                options = fetcher.get_options_data(symbol, expiry_month=month)
                
                # Group options by strike price
                strikes = defaultdict(lambda: {'CE': None, 'PE': None})
                
                for opt in options:
                    strike = opt['strike']
                    opt_type = opt['option_type']
                    
                    # Only consider strikes within ATM range
                    if (atm_lower * current_price) <= strike <= (atm_upper * current_price):
                        strikes[strike][opt_type] = opt
                
                # Find strikes with both CALL (CE) and PUT (PE)
                for strike, options_pair in strikes.items():
                    ce_opt = options_pair['CE']
                    pe_opt = options_pair['PE']
                    
                    # Skip if either option is missing
                    if not ce_opt or not pe_opt:
                        continue
                    
                    # Extract data
                    call_premium = ce_opt['last_price']
                    put_premium = pe_opt['last_price']
                    call_volume = ce_opt['volume']
                    put_volume = pe_opt['volume']
                    expiry_full = ce_opt['expiry_date']
                    
                    # Format expiry date
                    expiry = '-'.join(expiry_full.split('-')[:2]) if expiry_full else ''
                    
                    # Skip if premiums are zero
                    if call_premium == 0 or put_premium == 0:
                        continue
                    
                    # Calculate metrics
                    combined_premium = call_premium + put_premium
                    investment = margin * 2 * lot_size * current_price
                    max_profit = combined_premium * lot_size
                    max_roi = (max_profit / investment) * 100
                    
                    # Safety ranges
                    short_safety = strike - combined_premium
                    long_safety = strike + combined_premium
                    
                    all_opportunities.append({
                        'Symbol': symbol,
                        'Current': current_price,
                        'Strike': strike,
                        'Expiry': expiry,
                        'CALL': call_premium,
                        'PUT': put_premium,
                        'C+P': round(combined_premium, 2),
                        'Investment': int(investment),
                        'MAX Profit': int(max_profit),
                        'MAX ROI %': round(max_roi, 2),
                        'Short Safety': round(short_safety, 2),
                        'Long Safety': round(long_safety, 2),
                        'CALL Vol': call_volume,
                        'PUT Vol': put_volume
                    })
        
        except Exception as e:
            status_placeholder.warning(f"⚠️ Error processing {symbol}: {e}")
    
    # Clear progress indicators
    progress_bar.empty()
    status_text.empty()
    
    # Display results
    if all_opportunities:
        df = pd.DataFrame(all_opportunities)
        
        # Sort by ROI or normal
        if sort_by == 'ROI':
            df = df.sort_values('MAX ROI %', ascending=False)
        else:
            df = df.sort_values(['Symbol', 'Strike'])
        
        df = df.reset_index(drop=True)
        
        # Display dataframe with formatting
        st.success(f"✓ Found {len(df)} opportunities")
        
        # Format dataframe for display
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=False,
            column_config={
                "Symbol": st.column_config.TextColumn("Symbol", width="small"),
                "Current": st.column_config.NumberColumn("Current", format="₹ %.2f"),
                "Strike": st.column_config.NumberColumn("Strike", format="₹ %.2f"),
                "CALL": st.column_config.NumberColumn("CALL", format="₹ %.2f"),
                "PUT": st.column_config.NumberColumn("PUT", format="₹ %.2f"),
                "C+P": st.column_config.NumberColumn("C+P", format="₹ %.2f"),
                "Investment": st.column_config.NumberColumn("Investment", format="₹ %d"),
                "MAX Profit": st.column_config.NumberColumn("MAX Profit", format="₹%d"),
                "MAX ROI %": st.column_config.NumberColumn("MAX ROI %", format="%.2f%%"),
                "Short Safety": st.column_config.NumberColumn("Short Safety", format="₹ %.2f"),
                "Long Safety": st.column_config.NumberColumn("Long Safety", format="₹ %.2f"),
            }
        )
        
        # Summary statistics
        st.subheader("📊 Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Avg ROI", f"{df['MAX ROI %'].mean():.2f}%")
        with col2:
            st.metric("Max ROI", f"{df['MAX ROI %'].max():.2f}%")
        with col3:
            st.metric("Avg Investment", f"₹{df['Investment'].mean():,.0f}")
    
    else:
        st.warning("⚠️ No opportunities found. Market may be closed or no suitable strikes available.")

except Exception as e:
    st.error(f"❌ Error: {e}")

# Strategy 2: Covered Call
st.divider()
st.subheader("Strategy 2: Covered Call")
st.markdown("Sell a CALL option while holding the underlying stock (i.e. buy the underlying stock).")
st.markdown("Ideal for Moderate Bullish Outlook.")

# Placeholder for Strategy 2 data
data_placeholder2 = st.empty()
status_placeholder2 = st.empty()

# Fetch and display Strategy 2 data
try:
    fetcher2 = get_fetcher()
    all_opportunities2 = []
    
    # Progress bar
    progress_bar2 = st.progress(0)
    status_text2 = st.empty()
    
    # Fetch data for each stock
    for idx, symbol in enumerate(selected_stocks):
        status_text2.text(f"Processing {symbol} for Covered Call... ({idx+1}/{len(selected_stocks)})")
        progress_bar2.progress((idx + 1) / len(selected_stocks))
        
        try:
            # Get current price and options
            current_price = fetcher2.get_stock_price(symbol)
            lot_size = fetcher2.get_lot_size(symbol)
            
            if current_price == 0:
                continue
            
            # Get options for chosen months
            for month in selected_months:
                options = fetcher2.get_options_data(symbol, expiry_month=month)
                
                # Only look at CALL options
                for opt in options:
                    if opt['option_type'] != 'CE':
                        continue
                    
                    strike = opt['strike']
                    
                    # Only consider strikes at or above current price (OTM/ATM calls)
                    if not (0.999 * current_price <= strike <= atm_upper * current_price):
                        continue
                    
                    # Extract data
                    call_premium = opt['last_price']
                    call_volume = opt['volume']
                    expiry_full = opt['expiry_date']
                    
                    # Format expiry date
                    expiry = '-'.join(expiry_full.split('-')[:2]) if expiry_full else ''
                    
                    # Skip if premium is zero
                    if call_premium == 0:
                        continue
                    
                    # Calculate metrics for covered call
                    # Investment = stock purchase cost (with margin)
                    investment = int(margin * lot_size * current_price)
                    interest = round(0.01 * margin * lot_size * current_price, 2)  # Holding cost
                    
                    # Max Profit: if stock rises to strike + premium collected - interest
                    max_profit = int(((strike - current_price + call_premium) * lot_size) - interest)
                    max_roi = round(100 * (((strike - current_price + call_premium) * lot_size) - interest) / investment, 2)
                    
                    # Safety Point: price at which you break even
                    safety_point = round((1.003 * current_price) - call_premium, 2)
                    safety_pct = round(((call_premium - (0.003 * current_price)) / current_price * 100), 2)
                    
                    all_opportunities2.append({
                        'Symbol': symbol,
                        'Current': current_price,
                        'Strike': strike,
                        'Expiry': expiry,
                        'CALL': call_premium,
                        'Investment': investment,
                        'MAX Profit': max_profit,
                        'MAX ROI %': max_roi,
                        'Safety Point': safety_point,
                        'Safety %': safety_pct,
                        'CALL Vol': call_volume
                    })
        
        except Exception as e:
            status_placeholder2.warning(f"⚠️ Error processing {symbol}: {e}")
    
    # Clear progress indicators
    progress_bar2.empty()
    status_text2.empty()
    
    # Display results
    if all_opportunities2:
        df2 = pd.DataFrame(all_opportunities2)
        
        # Sort by ROI
        df2 = df2.sort_values('MAX ROI %', ascending=False)
        df2 = df2.reset_index(drop=True)
        
        # Display dataframe with formatting
        st.success(f"✓ Found {len(df2)} covered call opportunities")
        
        # Format dataframe for display
        st.dataframe(
            df2,
            use_container_width=True,
            hide_index=False,
            column_config={
                "Symbol": st.column_config.TextColumn("Symbol", width="small"),
                "Expiry": st.column_config.TextColumn("Expiry", width="small"),
                "Current": st.column_config.NumberColumn("Current", format="₹ %.2f"),
                "Strike": st.column_config.NumberColumn("Strike", format="₹ %.2f"),
                "Safety Point": st.column_config.NumberColumn("Safety Point", format="₹ %.2f"),
                "Safety %": st.column_config.NumberColumn("Safety %", format="%.2f%%"),
                "CALL": st.column_config.NumberColumn("CALL", format="₹ %.2f"),
                "Investment": st.column_config.NumberColumn("Investment", format="₹ %d", help=f"This includes a margin of {margin*100:.0f}% and the interest"),
                "MAX Profit": st.column_config.NumberColumn("MAX Profit", format="₹ %d"),
                "MAX ROI %": st.column_config.NumberColumn("MAX ROI %", format="%.2f%%"),
                "CALL Vol": st.column_config.NumberColumn("CALL Vol", format="%d"),
            }
        )
        
        # Summary statistics
        st.divider()
        st.subheader("📊 Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Avg ROI", f"{df2['MAX ROI %'].mean():.2f}%")
        with col2:
            st.metric("Max ROI", f"{df2['MAX ROI %'].max():.2f}%")
        with col3:
            st.metric("Avg Investment", f"₹{df2['Investment'].mean():,.0f}")
    
    else:
        st.warning("⚠️ No covered call opportunities found.")

except Exception as e:
    st.error(f"❌ Error: {e}")

# Auto-refresh logic
if auto_refresh:
    sleep(30)
    st.rerun()
