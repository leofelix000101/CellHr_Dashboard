from sqlalchemy import text
import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
from datetime import datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import io
from sqlalchemy.dialects.postgresql import insert

# --- Professional Page Config ---
st.set_page_config(
    layout="wide", 
    page_title="Telecom Network Performance Dashboard", 
    page_icon="📡"
)

# --- App Styling Tweaks (Fonts & Hierarchy) ---
st.markdown("""
<style>
    .reportview-container .main .block-container { padding-top: 2rem; }
    h1, h2, h3 { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-weight: 600; color: #1E293B; }
    div[data-testid="stMetricValue"] { font-size: 2rem !important; font-weight: 700; color: #0EA5E9; }
    
    /* Table Appearance Tweaks */
    div[data-testid="stDataFrame"] td, div[data-testid="stDataEditor"] td {
        text-align: center !important;
    }
    div[data-testid="stDataFrame"] th, div[data-testid="stDataEditor"] th {
        text-align: center !important;
        font-weight: bold !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Database Connection with Resilient Pool Settings ---
conn = st.connection(
    "postgresql", 
    type="sql", 
    pool_pre_ping=True, 
    pool_recycle=300
) 

# --- Professional Secure Login Screen ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return True

    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(
                "<h2 style='text-align: center; margin-bottom: 5px; color:#0F172A;'>📡 CELL HOUR ANALYSIS</h2>"
                "<p style='text-align: center; color:#64748B; margin-bottom: 25px;'>Sign in to manage monitoring and cell logs</p>", 
                unsafe_allow_html=True
            )
            user = st.text_input("Username", placeholder="Enter your operator username")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Access Dashboard", use_container_width=True, type="primary"):
                if user == "mytel" and password == "telecom@ops2026":
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("❌ Invalid Username or Password Credentials.")
    return False

if not check_password():
    st.stop()

# --- Modern Sidebar Implementation & Developer Info ---
with st.sidebar:
    st.markdown(
        "<h2 style='margin-bottom: 0px; color:#0F172A;'>Ops Control Room</h2>"
        "<p style='color:#64748B; font-size:0.85rem; margin-bottom: 20px;'>OCE CELL HOUR CALCULATION</p>", 
        unsafe_allow_html=True
    )
    
    current_tab = st.radio(
        "🎛️ Menu",
        options=[
            "📂 Upload & Process", 
            "📈 Analytics & Trends", 
            "🔬 Site Daily Down Tracking", 
            "🏆 Team Performance",
            "📥 Export Data",
            "⚠️ Error Checking"
        ],
        label_visibility="collapsed"
    )
    
    st.markdown("<br>" * 5, unsafe_allow_html=True)
    st.divider()
    
    developer_html = (
        "<h4 style='color:#475569; margin-bottom: 5px;'>🔧 Developer Profile</h4>"
        "<p style='margin:0; font-size:0.85rem; color:#64748B;'><strong>Role:</strong> Radio Engineer</p>"
        "<p style='margin:0; font-size:0.85rem; color:#64748B;'><strong>System:</strong> Streamlit / Superbase</p>"
        "<p style='margin:0; font-size:0.85rem; color:#64748B;'><strong>Status:</strong> Active Session ✅</p>"
    )
    st.markdown(developer_html, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚪 Sign Out", use_container_width=True, type="secondary"):
        st.session_state["authenticated"] = False
        st.rerun()


# ======================================================================================
# --- HIGH PERFORMANCE ON-DEMAND DATA RETRIEVAL ARCHITECTURE ---
# ======================================================================================

@st.cache_data(ttl="12h", show_spinner=False)
def get_available_cycles():
    """Lightweight metadata fetch to populate dropdown options instantly."""
    conn_cache = st.connection("postgresql", type="sql", pool_pre_ping=True, pool_recycle=300)
    query = """
        SELECT DISTINCT 
            CASE 
                WHEN EXTRACT(DAY FROM end_time) >= 21 
                THEN TO_CHAR(end_time + INTERVAL '1 month', 'Month YYYY')
                ELSE TO_CHAR(end_time, 'Month YYYY')
            END AS cycle_name,
            CASE 
                WHEN EXTRACT(DAY FROM end_time) >= 21 
                THEN DATE_TRUNC('month', end_time + INTERVAL '1 month')
                ELSE DATE_TRUNC('month', end_time)
            END AS cycle_date
        FROM total_cell_down 
        WHERE end_time IS NOT NULL 
        ORDER BY cycle_date DESC
    """
    res = conn_cache.query(query, ttl="1h")
    if res.empty:
        return []
    return res['cycle_name'].str.strip().tolist()

def get_cycle_date_bounds(cycle_name_str):
    """Calculates strict start/end timestamps for a given 21st - 20th cycle."""
    dt = datetime.strptime(cycle_name_str.strip(), "%B %Y")
    start_bound = (dt - relativedelta(months=1)).replace(day=21, hour=0, minute=0, second=0)
    end_bound = dt.replace(day=20, hour=23, minute=59, second=59)
    return start_bound, end_bound

@st.cache_data(ttl="1h", show_spinner="Fetching selected cycle analytics...")
def get_analytics_data_for_cycles(selected_cycles):
    """On-demand fetching limited strictly to selected cycle intervals."""
    if not selected_cycles:
        return pd.DataFrame()
        
    conn_cache = st.connection("postgresql", type="sql", pool_pre_ping=True, pool_recycle=300)
    
    all_dfs = []
    for cycle_name in selected_cycles:
        s_bound, e_bound = get_cycle_date_bounds(cycle_name)
        
        query = """
            SELECT t.site_id, t.final_cell_hr, t.end_time, t.reason_level_3, t.reason_level_1, 
                   m.owner, m.power_type,
                   EXTRACT(DAY FROM t.end_time) as d, 
                   EXTRACT(MONTH FROM t.end_time) as m, 
                   EXTRACT(YEAR FROM t.end_time) as y 
            FROM total_cell_down t
            LEFT JOIN site_master m ON t.site_id = m.site_id
            WHERE t.end_time >= :start_bound AND t.end_time <= :end_bound
        """
        
        df = conn_cache.query(query, params={"start_bound": s_bound, "end_bound": e_bound}, ttl="10m")
        if not df.empty:
            df['cycle_name'] = cycle_name
            all_dfs.append(df)
            
    if not all_dfs:
        return pd.DataFrame()
        
    combined_df = pd.concat(all_dfs, ignore_index=True)
    combined_df['final_cell_hr'] = pd.to_numeric(combined_df['final_cell_hr'], errors='coerce').fillna(0.0)
    combined_df['d'] = combined_df['d'].astype(int)
    combined_df['plot_day'] = combined_df['d'].apply(lambda d: d - 20 if d >= 21 else d + 11)
    combined_df['dt_obj'] = pd.to_datetime(combined_df['end_time']).dt.normalize()
    
    return combined_df

@st.cache_data(ttl="1h", show_spinner="Processing Time Buckets on Demand...")
def get_time_buckets_for_cycles(selected_cycles):
    """On-demand dynamic slicing for time bucket breakdown."""
    if not selected_cycles:
        return pd.DataFrame()
        
    conn_cache = st.connection("postgresql", type="sql", pool_pre_ping=True, pool_recycle=300)
    
    all_splits = []
    for cycle_name in selected_cycles:
        s_bound, e_bound = get_cycle_date_bounds(cycle_name)
        
        tb_query = """
            SELECT t.site_id, t.start_time, t.end_time, t.final_cell_hr, 
                   t.reason_level_3, t.reason_level_1, m.fot_teams
            FROM total_cell_down t
            LEFT JOIN site_master m ON t.site_id = m.site_id
            WHERE t.start_time IS NOT NULL AND t.end_time IS NOT NULL 
            AND t.end_time >= :start_bound AND t.end_time <= :end_bound
        """
        tb_df = conn_cache.query(tb_query, params={"start_bound": s_bound, "end_bound": e_bound}, ttl="10m")
        
        if tb_df.empty:
            continue

        tb_df['start_time'] = pd.to_datetime(tb_df['start_time'])
        tb_df['end_time'] = pd.to_datetime(tb_df['end_time'])

        for row in tb_df.itertuples(index=False):
            start, end = row.start_time, row.end_time
            if pd.isna(start) or pd.isna(end) or start >= end: 
                continue
                
            if start.tzinfo is not None: start = start.tz_localize(None)
            if end.tzinfo is not None: end = end.tz_localize(None)

            total_orig_dur = (end - start).total_seconds() / 3600.0
            if total_orig_dur > 1440 or total_orig_dur <= 0: 
                continue 

            orig_hr = float(row.final_cell_hr) if pd.notna(row.final_cell_hr) else 0.0
            op_day = end.date().day
            plot_day = op_day - 20 if op_day >= 21 else op_day + 11

            curr = start
            while curr < end:
                date_curr = curr.date()
                day_start = datetime.combine(date_curr, time(6, 0))
                day_end = datetime.combine(date_curr, time(18, 0))
                night_end = datetime.combine(date_curr, time(23, 0))
                
                if curr < day_start:
                    bucket = "Midnight"
                    b_end = day_start
                elif day_start <= curr < day_end:
                    bucket = "Day"
                    b_end = day_end
                elif day_end <= curr < night_end:
                    bucket = "Night"
                    b_end = night_end
                else:
                    bucket = "Midnight"
                    b_end = datetime.combine(date_curr + timedelta(days=1), time(6, 0))

                segment_end = min(end, b_end)
                duration_hrs = (segment_end - curr).total_seconds() / 3600.0

                if duration_hrs > 0:
                    slice_hr = orig_hr * (duration_hrs / total_orig_dur)
                    all_splits.append({
                        "Teams": row.fot_teams if pd.notna(row.fot_teams) else 'Unassigned',
                        "Site ID": row.site_id,
                        "Start time": curr,
                        "end_time": segment_end,
                        "Reason level 3": row.reason_level_3,
                        "Reason level 1": row.reason_level_1,
                        "duration": round(duration_hrs, 4),
                        "Total Cell Hour": round(slice_hr, 4), 
                        "Bucket": bucket,
                        "plot_day": plot_day,
                        "cycle_name": cycle_name
                    })
                curr = segment_end
                
    return pd.DataFrame(all_splits)

@st.cache_data(ttl="1h", show_spinner="Loading Tracking Data...")
def get_tracking_data_for_cycle(selected_cycle):
    """Targeted SQL fetching for Site Daily Down Tracking."""
    if not selected_cycle:
        return pd.DataFrame()
        
    s_bound, e_bound = get_cycle_date_bounds(selected_cycle)
    conn_cache = st.connection("postgresql", type="sql", pool_pre_ping=True, pool_recycle=300)
    
    query = """
        SELECT t.end_time, t.site_id, t.final_cell_hr, t.reason_level_3, m.fot_teams AS team, m.owner 
        FROM total_cell_down t 
        LEFT JOIN site_master m ON t.site_id = m.site_id
        WHERE t.end_time >= :start_bound AND t.end_time <= :end_bound
    """
    df = conn_cache.query(query, params={"start_bound": s_bound, "end_bound": e_bound}, ttl="10m")
    
    if not df.empty:
        df['final_cell_hr'] = pd.to_numeric(df['final_cell_hr'], errors='coerce').fillna(0.0)
        df['end_time'] = pd.to_datetime(df['end_time'])
        df['owner'] = df['owner'].fillna('Unknown Owner').astype(str).str.strip()
    return df

# ======================================================================================
# --- ROUTE VIEWS ---
# ======================================================================================

if current_tab == "📂 Upload & Process":
    st.markdown("<h1 style='margin-bottom:0px;'>📂 Upload & Validation Pipeline</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#64748B;'>Import daily NOC pro cell down file!</p>", unsafe_allow_html=True)
    st.divider()
    
    uploaded_file = st.file_uploader("Upload CSV/XLSX File", type=["csv", "xlsx"])
    
    if uploaded_file:
        df = pd.read_csv(uploaded_file, skiprows=2) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file, skiprows=2)
        df.columns = df.columns.str.strip()
        
        master_df = conn.query("SELECT site_id FROM site_master", ttl="10m") 
        missing_sites = df[~df['Station standard code'].isin(master_df['site_id'])]['Station standard code'].unique()
        
        if len(missing_sites) > 0:
            st.error(f"⚠️ Not include in Site Master: {', '.join(map(str, missing_sites))}")
            cols_info = conn.query("SELECT column_name FROM information_schema.columns WHERE table_name = 'site_master'", ttl="10m")
            master_cols = [c for c in cols_info['column_name'] if c != 'site_id']
            
            new_site_df = pd.DataFrame(index=missing_sites, columns=master_cols)
            new_site_df.index.name = 'site_id'
            
            st.write("### 🛠️ Please insert New site information!")
            edited_new_sites = st.data_editor(new_site_df, use_container_width=True)
            
            if st.button("🚀 Save All New Sites to Master"): 
                try:
                    # Reset the index so 'site_id' becomes a standard column in the dataframe
                    insert_df = edited_new_sites.reset_index()
                    
                    # Safely bulk-insert the dataframe into the database
                    engine = conn.engine
                    with engine.begin() as connection:
                        insert_df.to_sql(
                            name="site_master", 
                            con=connection, 
                            if_exists="append", 
                            index=False
                        )
                        
                    st.cache_data.clear()
                    st.success("✅ New data saved to site_master.")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"⚠️ Database Error: {e}")
        else: 
            master_full = conn.query("SELECT * FROM site_master", ttl="10m")
            df = df.merge(master_full, left_on='Station standard code', right_on='site_id', how='left')
            history_df = conn.query("SELECT reason_level_1, reason_level_3 FROM total_cell_down WHERE reason_level_3 IS NOT NULL", ttl="10m") 

            history_df['reason_level_1'] = history_df['reason_level_1'].astype(str).str.replace('nan', '', case=False).str.lower().str.strip()
            reason_map = history_df.groupby('reason_level_1')['reason_level_3'].agg(lambda x: x.mode()[0] if not x.mode().empty else 'Unknown').to_dict()

            df['Duration time (hour)'] = pd.to_numeric(df['Duration time (hour)'], errors='coerce').fillna(0)
            df['Cell down_numeric'] = df['Cell down'].apply(lambda x: 1 if str(x).strip().lower() == 'single' else pd.to_numeric(x, errors='coerce')).fillna(0)
            
            def calculate_hours(row):
                duration = row['Duration time (hour)']
                alarm = str(row['Alarm name']).strip()
                cell_down = str(row['Cell down']).strip().lower()
                
                g4_hour = 0
                if cell_down == 'single' and alarm == 'Cell Unavailable': g4_hour = duration * 1
                elif alarm == 'NE Is Disconnected.': g4_hour = duration * row.get('cells_4g', 0)
                
                g2_hour = 0
                if cell_down == 'single' and alarm == 'GSM CELL OUT OF SERVICE': g2_hour = duration * 1
                elif alarm == 'CSL Fault': g2_hour = duration * row.get('cells_2g', 0)
                
                return pd.Series([g4_hour, g2_hour, g4_hour + g2_hour])

            df[['4G_cell_hour', '2G_cell_hour', 'final_cell_hr']] = df.apply(calculate_hours, axis=1)
            
            def determine_reason_level_3(row):
                reason_1_raw = str(row.get('Reason', '')).strip()
                reason_1_clean = reason_1_raw.lower().replace('nan', '')
                
                if "majeure impact_planned/cr" in reason_1_clean: return "Majeure cause"
                if "loss_power_loss ac of rru extend, small cell" in reason_1_clean: return "Small Cell Down"
                if "tco_low ac, don't charge the battery affect site/cell down" in reason_1_clean: return "Small Cell Down"
                
                if reason_1_clean == "":
                    power_type_val = str(row.get('power_type', '')).strip().lower()
                    if "self power" in power_type_val: return "Mytel Power"
                    elif "share power" in power_type_val: return "Towerco power issue"
                
                if row.get('Cell down_numeric') == 1: return "Cell Down"
                return reason_map.get(reason_1_clean, 'Unknown')

            df['reason_level_3'] = df.apply(determine_reason_level_3, axis=1)
            df['End time'] = pd.to_datetime(df['End time'], errors='coerce')
            df['Date'] = df['End time'].dt.date
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(f"📊 Preview ({len(df)} rows uploaded)")
            with col2:
                date_counts = df['Date'].value_counts()
                if not date_counts.empty:
                    most_rows_date = date_counts.idxmax()
                    total_for_most_date = df[df['Date'] == most_rows_date]['final_cell_hr'].sum()
                    st.metric(label=f"📅 Total Cell*HR ({most_rows_date})", value=f"{total_for_most_date:,.2f}")
                else:
                    st.metric(label="Total Cell*HR", value="0.00")

            date_summary = df.groupby('Date')['final_cell_hr'].sum().reset_index()
            if not date_summary.empty:
                st.write("📅 **Daily Breakdown:**")
                st.dataframe(date_summary, use_container_width=True)

            display_cols = ['Station standard code', 'Cell name', 'Alarm name', 'Start time', 'End time', 
                            'Duration time (hour)', 'cells_2g', 'cells_4g', 'power_type', '4G_cell_hour', '2G_cell_hour', 
                            'final_cell_hr', 'Reason', 'reason_level_3']
            
            edited_df = st.data_editor(
                df[display_cols], 
                column_config={
                    "power_type": st.column_config.TextColumn("Power Type", disabled=True),
                    "reason_level_3": st.column_config.SelectboxColumn(
                        "Reason Level 3", 
                        options=["Cell Down", "Towerco power issue", "Small Cell Down", "Transmission", "Operation", "Majeure cause", "Power down at HUB site", "Mytel Power"],
                        required=True
                    )
                }, 
                use_container_width=True,
                key="part2_editor"
            )
            
            crosscheck = st.checkbox("✅ Crosscheck Finished")
            if crosscheck:
                st.divider()
                st.subheader("📋 Reason Summary")
                st.dataframe(edited_df.groupby('reason_level_3', as_index=False)['final_cell_hr'].sum(), use_container_width=True)
                
                if st.button("🚀 Save to Database", key="save_db_btn"):
                    try:
                        db_df = pd.DataFrame({
                            "site_id": edited_df['Station standard code'],
                            "alarm_name": edited_df['Alarm name'],
                            "start_time": edited_df['Start time'],
                            "end_time": edited_df['End time'],
                            "duration_all_time": edited_df['Duration time (hour)'],
                            "reason_level_3": edited_df['reason_level_3'],
                            "final_cell_hr": edited_df['final_cell_hr'],
                            "reason_level_1": edited_df['Reason'],
                            "g4_cell_hour": edited_df['4G_cell_hour'],
                            "g2_cell_hour": edited_df['2G_cell_hour']
                        })

                        def insert_on_conflict_nothing(table, conn, keys, data_iter):
                            data = [dict(zip(keys, row)) for row in data_iter]
                            stmt = insert(table.table).values(data).on_conflict_do_nothing(
                                index_elements=['site_id', 'start_time', 'end_time', 'alarm_name', 'reason_level_3', 'reason_level_1']
                            )
                            result = conn.execute(stmt)
                            return result.rowcount

                        engine = conn.engine
                        with engine.begin() as connection:
                            db_df.to_sql(
                                name="total_cell_down", con=connection, if_exists="append", index=False, method=insert_on_conflict_nothing
                            )
                        
                        st.cache_data.clear() 
                        st.success("✅ Successfully uploaded! Records matching all criteria were safely skipped as duplicates.")

                    except Exception as e: 
                        st.error(f"Error: {e}")

#================================================================================================
elif current_tab == "📈 Analytics & Trends":
    st.markdown("<h1>📈 Monthly Performance Analytics & Trends</h1>", unsafe_allow_html=True)
    st.divider()
    
    available_cycles = get_available_cycles()
    trend_tab, time_bucket_tab = st.tabs(["🌐 Overall Trends & Daily Summary", "🌙 Day / Night / Midnight Analysis"])

    with trend_tab:
        with st.container(): 
            target_val = st.number_input("🎯 Enter Target Cell Hour (Overall):", value=3000, step=100, key="overall_target_input")
            
            selected_cycles = st.multiselect(
                "Select Cycle Periods to display:", 
                options=available_cycles, 
                default=available_cycles[:3] if len(available_cycles) >= 3 else available_cycles, 
                key="overall_cycle_multiselect"
            )

            df = get_analytics_data_for_cycles(selected_cycles)

            if not df.empty:
                st.write("### 🌐 Overall Total Cell Hour Trend")
                grouped = df.groupby(['plot_day', 'cycle_name'])['final_cell_hr'].sum().reset_index()
                
                fig = px.line(grouped, x='plot_day', y='final_cell_hr', color='cycle_name', markers=True, color_discrete_sequence=px.colors.qualitative.Alphabet)
                fig.update_traces(mode='lines+markers+text', texttemplate='%{y:.0f}', textposition='top center', textfont=dict(weight="bold", size=11, color="black"))
                fig.add_hline(y=target_val, line_dash="dash", line_color="red", annotation_text=f"Target: {target_val}")
                cycle_labels = [str(i) for i in range(21, 32)] + [str(i) for i in range(1, 21)]
                fig.update_layout(xaxis=dict(title="Cycle Date (21st to 20th)", tickmode='array', tickvals=list(range(1, 32)), ticktext=cycle_labels, tickfont=dict(size=10, color="black")), yaxis_title="Total Cell Hour", legend_title="Cycle Period", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig, use_container_width=True)

                st.write(f"### 📅 Cycle Performance Summary (21st - 20th)")
                selected_summary_cycles = st.multiselect("Select Cycle Period(s) for Summary:", options=selected_cycles, default=selected_cycles[0] if selected_cycles else None, key="summary_cycle_multiselect")

                if selected_summary_cycles:
                    curr_df = df[df['cycle_name'].isin(selected_summary_cycles)].copy()
                    if not curr_df.empty:
                        date_mapping = {}
                        for _, r in curr_df[['plot_day', 'dt_obj']].drop_duplicates().iterrows():
                            if pd.notna(r['dt_obj']): date_mapping[r['plot_day']] = r['dt_obj'].strftime('%b-%d')

                        pivot_df = curr_df.pivot_table(index='reason_level_3', columns='plot_day', values='final_cell_hr', aggfunc='sum', fill_value=0)
                        pivot_df = pivot_df.reindex(sorted(pivot_df.columns), axis=1).rename(columns=date_mapping)
                        pivot_df['Total Cell Hour'] = pivot_df.sum(axis=1)
                        pivot_df['Daily Avg Cell hour'] = pivot_df['Total Cell Hour'] / max(curr_df['dt_obj'].nunique(), 1)
                        total_sum = pivot_df['Daily Avg Cell hour'].sum()
                        pivot_df['Daily Avg (%)'] = (pivot_df['Daily Avg Cell hour'] / total_sum) * 100 if total_sum > 0 else 0
                        pivot_df = pivot_df.reset_index().rename(columns={'reason_level_3': 'Reason'})

                        m1, m2 = st.columns(2)
                        m1.metric("Total Cell Hour", f"{float(pivot_df['Total Cell Hour'].sum()):,.2f}")
                        m2.metric("Daily Avg Cell hour", f"{float(pivot_df['Daily Avg Cell hour'].sum()):,.2f}")
                        
                        summary_fixed_cols = ['Reason', 'Total Cell Hour', 'Daily Avg Cell hour', 'Daily Avg (%)']
                        date_cols = [c for c in pivot_df.columns if c not in summary_fixed_cols]
                        column_config = {
                            "Reason": st.column_config.TextColumn("Reason", width="medium", pinned=True),
                            "Total Cell Hour": st.column_config.NumberColumn("Total Cell Hour", format="%.1f", width="small", pinned=True),
                            "Daily Avg Cell hour": st.column_config.NumberColumn("Daily Avg Cell Hour", format="%.1f", width="small", pinned=True),
                            "Daily Avg (%)": st.column_config.ProgressColumn("Daily Avg (%)", format="%.1f%%", min_value=0, max_value=100, width="small", pinned=True),
                        }
                        for d_col in date_cols: column_config[d_col] = st.column_config.NumberColumn(d_col, format="%.1f", width="small")

                        st.dataframe(pivot_df, use_container_width=True, hide_index=True, column_order=summary_fixed_cols + date_cols, column_config=column_config)

                st.divider()

                st.write("### 📅 Daily Performance & Executive Summary")
                max_available_date = pd.to_datetime(df['end_time']).dt.date.max()
                default_date = max_available_date if pd.notna(max_available_date) else datetime.now().date()
                selected_summary_date = st.date_input("Select Operational Date:", value=default_date, key="daily_summary_date_picker")
                target_date_df = df[pd.to_datetime(df['end_time']).dt.date == selected_summary_date].copy()
                
                target_noc_df, target_oce_df = pd.DataFrame(), pd.DataFrame()
                if not df.empty:                
                    def get_error_type(row):
                        r1 = str(row.get('reason_level_1', '')).lower()
                        r3 = str(row.get('reason_level_3', '')).lower()
                        power = str(row.get('power_type', '')).strip()
                        
                        if power == 'Self Power' and ('tco' in r1 or 'towerco' in r1): return "NOC Error"
                        is_r3_invalid = not row.get('reason_level_3') or str(row.get('reason_level_3')).strip() == ""
                        if power == 'Self Power' and ('tco' in r3 or 'tower' in r3 or is_r3_invalid): return "OCE Error"
                        return None

                    target_date_df['Error_Type'] = target_date_df.apply(get_error_type, axis=1)
                    target_noc_df = target_date_df[target_date_df['Error_Type'] == "NOC Error"]
                    target_oce_df = target_date_df[target_date_df['Error_Type'] == "OCE Error"]

                st.divider()
                col_table, col_alarms = st.columns(2)

                with col_table:
                    st.markdown(f"#### Daily Analysis ({selected_summary_date.strftime('%d %b %Y')})")
                    day_total_hr = target_date_df['final_cell_hr'].sum() if not target_date_df.empty else 0.0
                    st.metric("Total Cell Hour", f"{float(day_total_hr):,.2f}")

                    if not target_date_df.empty:
                        df_target_day = target_date_df.groupby('reason_level_3')['final_cell_hr'].sum().reset_index()
                        day_total = df_target_day['final_cell_hr'].sum()
                        df_target_day['Daily Percent (%)'] = (df_target_day['final_cell_hr'] / day_total) * 100 if day_total > 0 else 0
                        df_target_day.columns = ['Reason', 'Cell Hour', 'Daily Percent (%)']
                        st.dataframe(df_target_day, use_container_width=True, hide_index=True, column_config={
                            "Reason": st.column_config.TextColumn("Reason", width="medium"),
                            "Cell Hour": st.column_config.NumberColumn("Cell Hour", format="%.2f", width="small"),
                            "Daily Percent (%)": st.column_config.ProgressColumn("Daily (%)", format="%.1f%%", min_value=0, max_value=100, width="medium"),
                        })
                    else:
                        st.info(f"No operational downtime recorded for {selected_summary_date.strftime('%d %b %Y')}.")

                with col_alarms:
                    st.markdown(f"#### Operation Exceptions ({selected_summary_date.strftime('%d %b %Y')})")
                    st.metric("Total Exception Count", len(target_noc_df) + len(target_oce_df))

                    combined_exceptions = []
                    for _, r in target_noc_df.iterrows():
                        combined_exceptions.append({"Site ID": r['site_id'], "Error Type": "NOC Error", "Power Type": r.get('power_type', 'N/A'), "Reason": r['reason_level_1']})
                    for _, r in target_oce_df.iterrows():
                        combined_exceptions.append({"Site ID": r['site_id'], "Error Type": "OCE Error", "Power Type": r.get('power_type', 'N/A'), "Reason": r['reason_level_3']})
                    
                    exc_df = pd.DataFrame(combined_exceptions)
                    if not exc_df.empty:
                        st.dataframe(exc_df, use_container_width=True, hide_index=True, column_config={
                            "Site ID": st.column_config.TextColumn("Site ID", width="small"), "Error Type": st.column_config.TextColumn("Error Type", width="small"),
                            "Power Type": st.column_config.TextColumn("Power Type", width="small"), "Reason": st.column_config.TextColumn("Reason", width="medium")
                        })
                    else:
                        st.success("Operational Status: All sites Correct! (0 Exceptions).")
            else:
                st.info("Select cycle periods to view trend analytics.")

    with time_bucket_tab:
        with st.container(): 
            st.markdown("### 🌙 Day, Night & Midnight Performance Analysis")
            st.markdown("Tracks performance across **Day (06:00 - 18:00)**, **Night (18:00 - 23:00)**, and **Midnight (23:00 - 06:00)** buckets.")
            st.divider()

            selected_tb_cycles = st.multiselect("🗓️ Select Cycle Period(s) for Day/Night/Midnight Analysis:", options=available_cycles, default=available_cycles[:1] if available_cycles else None, key="tb_cycle_multiselect")

            full_splits_df = get_time_buckets_for_cycles(selected_tb_cycles)

            if not full_splits_df.empty:
                st.write("### 📊 Day, Night & Midnight Trend Lines")
                trend_grouped = full_splits_df.groupby(['plot_day', 'Bucket', 'cycle_name'])['Total Cell Hour'].sum().reset_index()

                fig_tb = px.line(trend_grouped, x='plot_day', y='Total Cell Hour', color='Bucket', line_dash='cycle_name', markers=True, color_discrete_sequence=["#2563EB", "#D97706", "#7C3AED"])
                fig_tb.update_traces(mode='lines+markers+text', texttemplate='%{y:.0f}', textposition='top center', textfont=dict(weight="bold", size=10, color="black"))
                cycle_labels = [str(i) for i in range(21, 32)] + [str(i) for i in range(1, 21)]
                fig_tb.update_layout(xaxis=dict(title="Cycle Date (21st to 20th)", tickmode='array', tickvals=list(range(1, 32)), ticktext=cycle_labels, tickfont=dict(size=10, color="black")), yaxis_title="Total Cell Hour", legend_title="Time Bucket / Cycle", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_tb, use_container_width=True)
                st.divider()

                st.write("### 📥 Download Detailed Period Reports")
                for cycle in selected_tb_cycles:
                    st.markdown(f"**Reports for Cycle: {cycle}**")
                    cycle_splits_df = full_splits_df[full_splits_df['cycle_name'] == cycle]
                    col_d, col_n, col_m = st.columns(3)
                    for bucket, col, label in [('Day', col_d, 'Day'), ('Night', col_n, 'Night'), ('Midnight', col_m, 'Midnight')]:
                        with col:
                            data = cycle_splits_df[cycle_splits_df['Bucket'] == bucket][["Teams", "Site ID", "Start time", "end_time", "Reason level 3", "Reason level 1", "duration", "Total Cell Hour"]]
                            st.download_button(
                                label=f"📥 Download {label} Report ({cycle})", 
                                data=data.to_csv(index=False).encode('utf-8'), 
                                file_name=f"{label}_Downtime_{cycle.replace(' ', '_')}.csv", 
                                mime="text/csv", 
                                use_container_width=True, 
                                key=f"dl_{label.lower()}_{cycle}"
                            )
                    st.write("---")
            else:
                st.info("No records available for selected cycle period(s).")

#=================================================================================================
elif current_tab == "🔬 Site Daily Down Tracking":
    st.markdown("<h1>🔬 Operational Site Daily Breakdown</h1>", unsafe_allow_html=True)
    st.divider()

    available_cycles = get_available_cycles()
    if available_cycles:
        selected_cycle_name = st.selectbox("🗓️ Select Cycle:", available_cycles)
        
        tracking_data = get_tracking_data_for_cycle(selected_cycle_name)

        if not tracking_data.empty:
            s_bound, e_bound = get_cycle_date_bounds(selected_cycle_name)
            today = datetime.now()
            days_passed = (e_bound - s_bound).days + 1 if today > e_bound else (today - s_bound).days + 1

            tracking_data['Date_Str'] = tracking_data['end_time'].dt.strftime('%d-%b')
            unique_dates_sorted = tracking_data.sort_values(by='end_time')['Date_Str'].unique()
            all_reasons = sorted(tracking_data['reason_level_3'].dropna().unique())
            
            def display_pinned_table(df, unique_dates):
                pinned_cols = ['team', 'site_id', 'Times down', 'Avg', 'Total', '%']
                col_config = {
                        "team": st.column_config.TextColumn("Team", width="auto", pinned=True),
                        "site_id": st.column_config.TextColumn("Site ID", width="small", pinned=True),
                        "Times down": st.column_config.NumberColumn("Times down", format="%d", width="small", pinned=True),
                        "Avg": st.column_config.NumberColumn("Avg", format="%.1f", width="small", pinned=True),
                        "Total": st.column_config.NumberColumn("Total", format="%.1f", width="small", pinned=True),
                        "%": st.column_config.ProgressColumn("%", format="%.1f%%", min_value=0, max_value=100, width="auto", pinned=True),
                }
                for d_col in unique_dates: col_config[d_col] = st.column_config.NumberColumn(d_col, format="%.1f", width="small", alignment="center")
                st.data_editor(df, use_container_width=True, hide_index=True, disabled=True, column_order=pinned_cols + list(unique_dates), column_config=col_config)

            for reason in all_reasons:
                reason_filtered_df = tracking_data[tracking_data['reason_level_3'] == reason].copy()
                
                if not reason_filtered_df.empty:
                    reason_total_hours = reason_filtered_df['final_cell_hr'].sum()
                    
                    if reason == "Towerco power issue":
                        st.markdown("---")
                        col_h1, col_h2 = st.columns([2, 1])
                        with col_h1: st.markdown(f"## ⚡ Grid Matrix: **Towerco power issue**")
                        with col_h2:
                            st.metric("Total Sites", reason_filtered_df['site_id'].nunique())
                            st.metric("Total Cell*HR", f"{reason_total_hours:,.1f}")

                        st.markdown("### 📋 Cell Hour Impact by Towerco Owner")
                        total_all_owners = reason_filtered_df['final_cell_hr'].sum()
                        
                        summary_df = reason_filtered_df.groupby('owner').agg(Sites=('site_id', 'nunique'), Total_Cell_Hour=('final_cell_hr', 'sum')).reset_index()
                        summary_df['Avg Cell Hour'] = summary_df['Total_Cell_Hour'] / days_passed 
                        summary_df['Percent'] = (summary_df['Total_Cell_Hour'] / total_all_owners) * 100
                        summary_df = summary_df.sort_values(by='Total_Cell_Hour', ascending=False)
                        
                        st.dataframe(summary_df, column_config={"owner": st.column_config.TextColumn("Owner", width="small", alignment="center"), "Sites": st.column_config.NumberColumn("Sites", width="small", alignment="center"), "Total_Cell_Hour": st.column_config.NumberColumn("Total Cell*HR", format="%.1f", width="small", alignment="center"), "Avg Cell Hour": st.column_config.NumberColumn("Avg Cell Hour", format="%.1f", width="small", alignment="center"), "Percent": st.column_config.ProgressColumn("Percent", format="%.1f%%", width="medium", min_value=0, max_value=100)}, use_container_width=True, hide_index=True)
                        
                        for owner in sorted(reason_filtered_df['owner'].unique()):
                            owner_df = reason_filtered_df[reason_filtered_df['owner'] == owner].copy()
                            owner_total = owner_df['final_cell_hr'].sum()
                            st.markdown(f"#### 🏢 **Towerco: {owner}** | Sites: {owner_df['site_id'].nunique()} | Total: {owner_total:,.1f} Cell*HR")
                            
                            site_pivot = owner_df.pivot_table(index=['team', 'site_id'], columns='Date_Str', values='final_cell_hr', aggfunc='sum', fill_value=0.0).reindex(columns=unique_dates_sorted, fill_value=0.0)
                            site_pivot['Total'] = site_pivot[unique_dates_sorted].sum(axis=1)
                            site_pivot['Times down'] = (site_pivot[unique_dates_sorted] > 0).sum(axis=1)
                            site_pivot['Avg'] = site_pivot['Total'] / days_passed 
                            site_pivot['%'] = (site_pivot['Total'] / owner_total) * 100 if owner_total > 0 else 0
                            
                            display_pinned_table(site_pivot.reset_index().sort_values(by='Total', ascending=False), unique_dates_sorted)
                    
                    else:
                        site_pivot = reason_filtered_df.pivot_table(index=['team', 'site_id'], columns='Date_Str', values='final_cell_hr', aggfunc='sum', fill_value=0.0).reindex(columns=unique_dates_sorted, fill_value=0.0)
                        site_pivot['Times down'] = (site_pivot[unique_dates_sorted] > 0).sum(axis=1).astype(int)
                        site_pivot['Total'] = site_pivot[unique_dates_sorted].sum(axis=1).astype(float)
                        site_pivot['Avg'] = site_pivot[unique_dates_sorted].mean(axis=1).astype(float)
                        site_pivot['%'] = (site_pivot['Total'] / reason_total_hours) * 100 if reason_total_hours > 0 else 0
                        
                        site_pivot_clean = site_pivot.reset_index()
                        site_pivot_clean = site_pivot_clean[site_pivot_clean['Times down'] > 0]
                        
                        st.write("---")
                        st.markdown(f"### 📊 Grid Matrix: **{reason}** <span style='color:#FF4B4B;'>(Sites: {site_pivot_clean['site_id'].nunique()} | Total: {reason_total_hours:,.1f} Cell*HR)</span>", unsafe_allow_html=True)
                        if not site_pivot_clean.empty:
                            display_pinned_table(site_pivot_clean.sort_values(by='Total', ascending=False), unique_dates_sorted)
        else:
            st.info("ℹ️ No records found for selected cycle.")

#=================================================================================================
elif current_tab == "📥 Export Data":
    st.markdown("<h1>📥 Operational Report Data Extraction</h1>", unsafe_allow_html=True)
    st.divider()
    st.write("Select a date range and a specific downtime reason to extract a custom Excel report.")
    
    col_d1, col_d2, col_r = st.columns(3)
    with col_d1: start_date = st.date_input("🗓️ Start Date", value=datetime.now().date() - timedelta(days=30), key="export_start_date")
    with col_d2: end_date = st.date_input("🗓️ End Date", value=datetime.now().date(), key="export_end_date")
    with col_r:
        reasons_df = conn.query("SELECT DISTINCT reason_level_3 FROM total_cell_down WHERE reason_level_3 IS NOT NULL", ttl="10m")
        available_reasons = ["All Reasons"] + list(reasons_df['reason_level_3'].unique()) if not reasons_df.empty else ["All Reasons"]
        selected_reason = st.selectbox("🔬 Select Reason Level 3", options=available_reasons, key="export_reason_select")
        
    if st.button("🔍 Generate Excel Report", key="generate_excel_btn"):
        if selected_reason == "All Reasons":
            export_query = """
                SELECT site_id AS "Site Code", alarm_name AS "Alarm Name/Cell ID", start_time AS "Start Time", end_time AS "End Time",
                       reason_level_1 AS "Reason Level 1", reason_level_3 AS "Reason Level 3", final_cell_hr AS "Total Cell Hour"
                FROM total_cell_down WHERE end_time::date >= :start_date AND end_time::date <= :end_date ORDER BY end_time DESC
            """
            export_df = conn.query(export_query, params={"start_date": start_date, "end_date": end_date}, ttl="1m")
        else:
            export_query = """
                SELECT site_id AS "Site Code", alarm_name AS "Alarm Name/Cell ID", start_time AS "Start Time", end_time AS "End Time",
                       reason_level_1 AS "Reason Level 1", reason_level_3 AS "Reason Level 3", final_cell_hr AS "Total Cell Hour"
                FROM total_cell_down WHERE end_time::date >= :start_date AND end_time::date <= :end_date AND reason_level_3 = :reason ORDER BY end_time DESC
            """
            export_df = conn.query(export_query, params={"start_date": start_date, "end_date": end_date, "reason": selected_reason}, ttl="1m")
        
        if not export_df.empty:
            export_df["Total Cell Hour"] = pd.to_numeric(export_df["Total Cell Hour"], errors='coerce').fillna(0.0)
            
            # --- FIX: Strip timezones so Excel doesn't crash ---
            export_df["Start Time"] = pd.to_datetime(export_df["Start Time"]).dt.tz_localize(None)
            export_df["End Time"] = pd.to_datetime(export_df["End Time"]).dt.tz_localize(None)
            
            st.success(f"📊 Found {len(export_df)} operational logs matching your criteria.")
            st.dataframe(export_df, use_container_width=True)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                export_df.to_excel(writer, sheet_name='Operational Report', index=False)
            
            st.download_button(
                label="📥 Download Excel Report", data=output.getvalue(),
                file_name=f"network_down_report_{str(selected_reason).replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="download_excel_report_btn"
            )
        else:
            st.warning("⚠️ No operational records found for the chosen date range and criteria.")

#=================================================================================================
elif current_tab == "⚠️ Error Checking":
    st.markdown("<h1>⚠️ Data Integrity & Error Checking</h1>", unsafe_allow_html=True)
    st.divider()

    available_cycles = get_available_cycles()
    selected_cycle_err = st.selectbox("🗓️ Select Cycle for Error Audit:", available_cycles if available_cycles else ["None"])
    
    if selected_cycle_err != "None":
        s_bound, e_bound = get_cycle_date_bounds(selected_cycle_err)
        query = """
            SELECT t.site_id, t.reason_level_1, t.reason_level_3, t.final_cell_hr, m.owner, m.power_type 
            FROM total_cell_down t
            LEFT JOIN site_master m ON t.site_id = m.site_id
            WHERE t.end_time >= :start_bound AND t.end_time <= :end_bound
        """
        df = conn.query(query, params={"start_bound": s_bound, "end_bound": e_bound}, ttl="10m")

        if not df.empty:
            df['final_cell_hr'] = pd.to_numeric(df['final_cell_hr'], errors='coerce').fillna(0.0)
            st.subheader("📋 Configuration Review")

            not_mytel_df = df[(df['owner'].str.lower() != 'mytel') & (df['power_type'] == 'Self Power') & (df['reason_level_3'].notna())]
            st.write("#### 🛡️ Towerco Sites (Power: Self Power)")
            
            owner_counts_nm = not_mytel_df.groupby('owner')['site_id'].nunique()
            cols = st.columns(len(owner_counts_nm) + 1) if not owner_counts_nm.empty else st.columns(1)
            cols[0].metric("All Sites", not_mytel_df['site_id'].nunique()) 
            for i, (owner, count) in enumerate(owner_counts_nm.items()): cols[i+1].metric(f"{owner}", count)
            
            if not not_mytel_df.empty: st.dataframe(not_mytel_df, use_container_width=True)
            else: st.info("No records found.")
            st.divider()

            mytel_share_df = df[(df['owner'].str.lower() == 'mytel') & (df['power_type'] == 'Share Power') & (df['reason_level_3'].notna())]
            st.write("#### 📶 MyTel (Power: Share Power)")
            col1, col2 = st.columns(2)
            col1.metric("Total Sites", mytel_share_df['site_id'].nunique())
            
            if not mytel_share_df.empty: st.dataframe(mytel_share_df, use_container_width=True)
            else: st.info("No records found.")
            st.divider()

            st.subheader("🔍 Identified Errors")
            def get_error_type(row):
                r1 = str(row.get('reason_level_1', '')).lower()
                r3 = str(row.get('reason_level_3', '')).lower()
                power = str(row.get('power_type', '')).strip()
                
                if power == 'Self Power' and ('tco' in r1 or 'towerco' in r1): return "NOC Error"
                is_r3_invalid = not row.get('reason_level_3') or str(row.get('reason_level_3')).strip() == ""
                if power == 'Self Power' and ('tco' in r3 or 'tower' in r3 or is_r3_invalid): return "OCE Error"
                return None

            df['Error_Type'] = df.apply(get_error_type, axis=1)
            noc_df = df[df['Error_Type'] == "NOC Error"]
            oce_df = df[df['Error_Type'] == "OCE Error"]

            st.write("---")
            st.subheader("🔴 NOC Errors")
            st.metric("Total NOC Error Sites", len(noc_df))
            if not noc_df.empty: st.dataframe(noc_df, use_container_width=True)
            else: st.success("No NOC errors found.")

            st.write("---")
            st.subheader("🔵 OCE Errors")
            st.metric("Total OCE Error Sites", len(oce_df))
            if not oce_df.empty: st.dataframe(oce_df, use_container_width=True)
            else: st.success("No OCE errors found.")
        else:
            st.info("No data available for selected cycle.")

#=================================================================================================
elif current_tab == "🏆 Team Performance":
    st.markdown("<h1>🏆 Team Performance Dashboard</h1>", unsafe_allow_html=True)
    st.divider()
    
    available_cycles = get_available_cycles()
    selected_cycles = st.multiselect("🗓️ Select Cycle Periods:", options=available_cycles, default=available_cycles[:1] if available_cycles else None, key="team_perf_cycles")

    if selected_cycles:
        master_df = conn.query("SELECT site_id, fot_teams FROM site_master", ttl="10m")
        
        all_down = []
        for c in selected_cycles:
            s_b, e_b = get_cycle_date_bounds(c)
            q = "SELECT final_cell_hr, end_time, site_id FROM total_cell_down WHERE end_time >= :s_b AND end_time <= :e_b"
            sub_df = conn.query(q, params={"s_b": s_b, "e_b": e_b}, ttl="10m")
            if not sub_df.empty:
                all_down.append(sub_df)

        down_df = pd.concat(all_down, ignore_index=True) if all_down else pd.DataFrame()

        if not master_df.empty:
            master_df['fot_teams'] = master_df['fot_teams'].fillna('Unassigned') 
            static_team_sites = master_df.groupby('fot_teams')['site_id'].nunique().reset_index()
            static_team_sites.columns = ['fot_teams', 'Total_Sites']

            if not down_df.empty:
                down_df['final_cell_hr'] = pd.to_numeric(down_df['final_cell_hr'], errors='coerce').fillna(0.0)
                merged_down = down_df.merge(master_df[['site_id', 'fot_teams']], on='site_id', how='left')
                team_down_agg = merged_down.groupby('fot_teams')['final_cell_hr'].sum().reset_index()
                team_down_agg.columns = ['fot_teams', 'Total_Cell_Hr']
            else:
                team_down_agg = pd.DataFrame(columns=['fot_teams', 'Total_Cell_Hr'])

            team_perf = static_team_sites.merge(team_down_agg, on='fot_teams', how='left').fillna(0)
            team_perf['Cell_Hr_Per_Site'] = team_perf['Total_Cell_Hr'] / team_perf['Total_Sites']
            team_perf = team_perf.sort_values('Cell_Hr_Per_Site', ascending=True)
            team_perf['Rank'] = range(1, len(team_perf) + 1)
            
            max_cell_hr_per_site = float(team_perf['Cell_Hr_Per_Site'].max()) if not team_perf.empty and team_perf['Cell_Hr_Per_Site'].max() > 0 else 1.0

            st.dataframe(
                team_perf[['fot_teams', 'Total_Sites', 'Total_Cell_Hr', 'Cell_Hr_Per_Site', 'Rank']],
                use_container_width=True, hide_index=True,
                column_config={
                    "fot_teams": st.column_config.TextColumn("Team Name", alignment='center', width='auto'),
                    "Total_Sites": st.column_config.NumberColumn("Total Sites", format="%d", alignment='center', width='auto'),
                    "Total_Cell_Hr": st.column_config.NumberColumn("Total Cell Hr", format="%.1f", alignment='center', width='auto'),
                    "Cell_Hr_Per_Site": st.column_config.ProgressColumn("Performance Index (Cell Hr / Site)", format="%.2f", min_value=0, max_value=max_cell_hr_per_site, width='large'),
                    "Rank": st.column_config.NumberColumn("Rank", format="%d", alignment='center', width='auto')
                }
            )
    else:
        st.warning("⚠️ Please select at least one cycle.")