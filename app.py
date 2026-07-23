import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import io

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
    /* Center align text in all table cells */
    div[data-testid="stDataFrame"] td, div[data-testid="stDataEditor"] td {
        text-align: center !important;
    }
    /* Bold headers and center align */
    div[data-testid="stDataFrame"] th, div[data-testid="stDataEditor"] th {
        text-align: center !important;
        font-weight: bold !important;


    /* Force center alignment for all data cells and headers */
    div[data-testid="stDataFrame"] td, div[data-testid="stDataEditor"] td {
        text-align: center !important;
    }
    div[data-testid="stDataFrame"] th, div[data-testid="stDataEditor"] th {
        text-align: center !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Database Connection ---
def get_db_conn():
    return psycopg2.connect(host="localhost", database="telecom_network_db", user="postgres", password="789456", port="5432")

# --- Professional Secure Login Screen ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return True

    # Render a clean, professional login card
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(
                "<h2 style='text-align: center; margin-bottom: 5px; color:#0F172A;'>📡 CEll HOUR ANALYSIS</h2>"
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
    
    # Modern Sidebar Radio Navigation
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
    
    # Clean Developer Info Panel
    developer_html = (
        "<h4 style='color:#475569; margin-bottom: 5px;'>🔧 Developer Profile</h4>"
        "<p style='margin:0; font-size:0.85rem; color:#64748B;'><strong>Role:</strong> Radio Engineer</p>"
        "<p style='margin:0; font-size:0.85rem; color:#64748B;'><strong>System:</strong> Local DB / PostgreSQL</p>"
        "<p style='margin:0; font-size:0.85rem; color:#64748B;'><strong>Status:</strong> Active Session ✅</p>"
    )
    st.markdown(developer_html, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚪 Sign Out", use_container_width=True, type="secondary"):
        st.session_state["authenticated"] = False
        st.rerun()

# --- Route Views Based on Sidebar Menu Selection ---
if current_tab == "📂 Upload & Process":
    st.markdown("<h1 style='margin-bottom:0px;'>📂 Upload & Validation Pipeline</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#64748B;'>Import daily NOC pro cell down file!</p>", unsafe_allow_html=True)
    st.divider()
    
    uploaded_file = st.file_uploader("Upload CSV/XLSX File", type=["csv", "xlsx"])
    
    if uploaded_file:
        df = pd.read_csv(uploaded_file, skiprows=2) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file, skiprows=2)
        df.columns = df.columns.str.strip()
        
        conn = get_db_conn()
        master_df = pd.read_sql("SELECT * FROM site_master", conn)
        conn.close()
        
        missing_sites = df[~df['Station standard code'].isin(master_df['site_id'])]['Station standard code'].unique()
        
        if len(missing_sites) > 0:
            st.error(f"⚠️ Not include in Site Master: {', '.join(map(str, missing_sites))}")
            conn = get_db_conn()
            cols_info = pd.read_sql("SELECT column_name FROM information_schema.columns WHERE table_name = 'site_master'", conn)
            master_cols = [c for c in cols_info['column_name'] if c != 'site_id']
            conn.close()
            
            new_site_df = pd.DataFrame(index=missing_sites, columns=master_cols)
            new_site_df.index.name = 'site_id'
            
            st.write("### 🛠️ Please insert New site information!")
            edited_new_sites = st.data_editor(new_site_df, use_container_width=True)
            
            if st.button("🚀 Save All New Sites to Master"):
                conn = get_db_conn(); cur = conn.cursor()
                for site_id, row in edited_new_sites.iterrows():
                    cols = ', '.join([f'"{c}"' for c in edited_new_sites.columns])
                    vals = [site_id] + [None if pd.isna(x) else x for x in row.tolist()]
                    placeholders = ', '.join(['%s'] * len(vals))
                    cur.execute(f'INSERT INTO site_master ("site_id", {cols}) VALUES ({placeholders})', vals)
                conn.commit(); cur.close(); conn.close()
                st.success("✅ New data saved to site_master.")
                st.rerun()

        else:
            df = df.merge(master_df, left_on='Station standard code', right_on='site_id', how='left')
            
            conn = get_db_conn()
            history_df = pd.read_sql("SELECT reason_level_1, reason_level_3 FROM total_cell_down", conn)
            conn.close()
            history_df['reason_level_1'] = history_df['reason_level_1'].astype(str).str.replace('nan', '', case=False).str.lower().str.strip()
            history_df = history_df[history_df['reason_level_3'].notna()]
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
                
                if "majeure impact_planned/cr" in reason_1_clean:
                    return "Majeure cause"
                    
                if "loss_power_loss ac of rru extend, small cell" in reason_1_clean:
                    return "Small Cell Down"
                    
                if "tco_low ac, don't charge the battery affect site/cell down" in reason_1_clean:
                    return "Small Cell Down"
                
                if reason_1_clean == "":
                    power_type_val = str(row.get('power_type', '')).strip().lower()
                    if "self power" in power_type_val:
                        return "Mytel Power"
                    elif "share power" in power_type_val:
                        return "Towerco power issue"
                
                if row.get('Cell down_numeric') == 1:
                    return "Cell Down"
                
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
                    conn = get_db_conn(); cur = conn.cursor()
                    try:
                        insert_query = """
                            INSERT INTO total_cell_down (
                                site_id, alarm_name, start_time, end_time, duration_all_time, 
                                reason_level_3, final_cell_hr, reason_level_1, g4_cell_hour, g2_cell_hour
                            ) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT ON CONSTRAINT unique_cell_down_record_v3 DO NOTHING;
                        """
                        
                        inserted_rows = 0
                        for _, row in edited_df.iterrows():
                            cur.execute(insert_query, (
                                row['Station standard code'], row['Alarm name'], row['Start time'], row['End time'], 
                                row['Duration time (hour)'], row['reason_level_3'], row['final_cell_hr'], 
                                row['Reason'], row['4G_cell_hour'], row['2G_cell_hour']
                            ))
                            if cur.rowcount > 0:
                                inserted_rows += 1
                                
                        conn.commit()
                        if inserted_rows > 0:
                            st.success(f"✅ Successfully saved {inserted_rows} new records!")
                        else:
                            st.info("ℹ️ No new records found. All rows already exist.")
                            
                    except Exception as e: 
                        conn.rollback()
                        st.error(f"Error: {e}")
                    finally: 
                        cur.close(); conn.close()

elif current_tab == "📈 Analytics & Trends":
    st.markdown("<h1>📈 Monthly Performance Analytics & Trends</h1>", unsafe_allow_html=True)
    st.divider()
    
    target_val = st.number_input("🎯 Enter Target Cell Hour (Overall):", value=3000, step=100)

    now = datetime.now()
    start_cycle = datetime(now.year, now.month, 21) if now.day >= 21 else (datetime(now.year, now.month, 1) - timedelta(days=1)).replace(day=21)
    
    conn = get_db_conn()
    query = """
        SELECT t.*, m.owner, EXTRACT(DAY FROM end_time) as d, EXTRACT(MONTH FROM end_time) as m, EXTRACT(YEAR FROM end_time) as y 
        FROM total_cell_down t
        LEFT JOIN site_master m ON t.site_id = m.site_id
    """
    df = pd.read_sql(query, conn)
    conn.close()

    if not df.empty:
        df['d'] = df['d'].astype(int)
        
        # --- Correct Cycle Name Logic ---
        def get_cycle_name(row):
            m, y = int(row['m']), int(row['y'])
            if row['d'] >= 21:
                m += 1
                if m > 12:
                    m = 1
                    y += 1
            target_date = datetime(y, m, 1)
            return f"{target_date.strftime('%B')} Cell Hour"

        df['cycle_name'] = df.apply(get_cycle_name, axis=1)
        df['plot_day'] = df['d'].apply(lambda d: d - 20 if d >= 21 else d + 11)

        # --- Dynamic Multiselect for Cycle Filtering ---
        all_cycles = sorted(df['cycle_name'].unique(), reverse=True)
        selected_cycles = st.multiselect(
            "Select Cycle Periods to display:", 
            options=all_cycles, 
            default=all_cycles[:3] if len(all_cycles) >= 3 else all_cycles
        )

        filtered_df = df[df['cycle_name'].isin(selected_cycles)]

        if not filtered_df.empty:
            st.write("### 🌐 Overall Total Cell Hour Trend")
            grouped = filtered_df.groupby(['plot_day', 'cycle_name'])['final_cell_hr'].sum().reset_index()
            
            # --- Updated Plotting Logic for Bold, Clear Labels ---
            fig = px.line(grouped, x='plot_day', y='final_cell_hr', color='cycle_name', 
                          markers=True, color_discrete_sequence=px.colors.qualitative.Alphabet)
            
            # Using textfont to set bold weight and clear sizing
            fig.update_traces(
                mode='lines+markers+text', 
                texttemplate='%{y:.0f}', 
                textposition='top center',
                textfont=dict(
                    weight="bold", 
                    size=11, 
                    color="black"
                )
            )

            fig.add_hline(y=target_val, line_dash="dash", line_color="red", annotation_text=f"Target: {target_val}")
            
            # Keep your existing layout settings
            cycle_labels = [str(i) for i in range(21, 32)] + [str(i) for i in range(1, 21)]
            
            fig.update_layout(
                xaxis=dict(
                    title="Cycle Date (21st to 20th)", 
                    tickmode='array', 
                    tickvals=list(range(1, 32)),
                    ticktext=cycle_labels,
                    tickfont=dict(size=10, color="black")
                ), 
                yaxis_title="Total Cell Hour",
                legend_title="Cycle Period",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

        # --- Current / Selected Cycle Summary ---
        # --- Current / Selected Cycle Summary ---
        st.write(f"### 📅 Cycle Performance Summary (21st - 20th)")
        
        def get_cycle_name(row):
            m, y = int(row['m']), int(row['y'])
            if row['d'] >= 21:
                m += 1
                if m > 12:
                    m = 1
                    y += 1
            target_date = datetime(y, m, 1)
            return f"{target_date.strftime('%B')} Cycle"

        df['cycle_name'] = df.apply(get_cycle_name, axis=1)
        df['dt_obj'] = pd.to_datetime(df['end_time']).dt.normalize()
        df['plot_day'] = df['d'].apply(lambda d: d - 20 if d >= 21 else d + 11)

        all_cycles = sorted(df['cycle_name'].unique(), reverse=True)
        selected_summary_cycles = st.multiselect(
            "Select Cycle Period(s) for Summary:", 
            options=all_cycles, 
            default=all_cycles[0] if all_cycles else None,
            key="summary_cycle_multiselect"
        )

        if selected_summary_cycles:
            curr_df = df[df['cycle_name'].isin(selected_summary_cycles)].copy()
            
            if not curr_df.empty:
                date_mapping = {}
                for _, r in curr_df[['plot_day', 'dt_obj']].drop_duplicates().iterrows():
                    p_day = r['plot_day']
                    d_obj = r['dt_obj']
                    if pd.notna(d_obj):
                        date_mapping[p_day] = d_obj.strftime('%b-%d')

                pivot_df = curr_df.pivot_table(index='reason_level_3', columns='plot_day', values='final_cell_hr', aggfunc='sum', fill_value=0)
                pivot_df = pivot_df.reindex(sorted(pivot_df.columns), axis=1)
                pivot_df = pivot_df.rename(columns=date_mapping)
                
                pivot_df['Total Cell Hour'] = pivot_df.sum(axis=1)
                # Dynamically calculate days_passed based on unique active dates present in the filtered cycle data
                days_passed = curr_df['dt_obj'].nunique()
                # Fallback to 1 to avoid ZeroDivisionError if no days are found
                days_passed = max(days_passed, 1)
                pivot_df['Daily Avg Cell hour'] = pivot_df['Total Cell Hour'] / days_passed
                pivot_df['Daily Avg (%)'] = (pivot_df['Daily Avg Cell hour'] / pivot_df['Daily Avg Cell hour'].sum()) * 100
                
                pivot_df = pivot_df.reset_index().rename(columns={'reason_level_3': 'Reason'})

                m1, m2 = st.columns(2)
                m1.metric("Total Cell Hour", f"{pivot_df['Total Cell Hour'].sum():,.2f}")
                m2.metric("Daily Avg Cell hour", f"{pivot_df['Daily Avg Cell hour'].sum():,.2f}")
                
                summary_fixed_cols = ['Reason', 'Total Cell Hour', 'Daily Avg Cell hour', 'Daily Avg (%)']
                date_cols = [c for c in pivot_df.columns if c not in summary_fixed_cols]
                
                column_config = {
                    "Reason": st.column_config.TextColumn("Reason", width="medium", pinned=True),
                    "Total Cell Hour": st.column_config.NumberColumn("Total Cell Hour", format="%.1f", width="small", pinned=True),
                    "Daily Avg Cell hour": st.column_config.NumberColumn("Daily Avg Cell Hour", format="%.1f", width="small", pinned=True),
                    "Daily Avg (%)": st.column_config.ProgressColumn("Daily Avg (%)", format="%.1f%%", min_value=0, max_value=100, width="small", pinned=True),
                }
                
                for d_col in date_cols:
                    column_config[d_col] = st.column_config.NumberColumn(d_col, format="%.1f", width="small")

                # --- Clear Font & Centralized Alignment Styling ---
                st.markdown("""
                <style>
                    /* Force strict centering and crisp clear typography across dataframe components */
                    div[data-testid="stDataFrame"] div, div[data-testid="stDataEditor"] div {
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
                    }
                    div[data-testid="stDataFrame"] td, div[data-testid="stDataEditor"] td,
                    div[data-testid="stDataFrame"] th, div[data-testid="stDataEditor"] th {
                        text-align: center !important;
                        justify-content: center !important;
                    }
                </style>
                """, unsafe_allow_html=True)

                st.dataframe(
                    pivot_df, 
                    use_container_width=True, 
                    hide_index=True,
                    column_order=summary_fixed_cols + date_cols,
                    column_config=column_config
                )
            else:
                st.info("📊 No data available for the selected cycle(s).")
        else:
            st.warning("⚠️ Please select at least one cycle period.")


        # --- Date-Selectable Daily Summary ---
        # --- Date-Selectable Daily Summary with Integrated Error Alarms ---
        # --- Executive Daily Summary & Error Alarms ---
        # --- Executive Daily Summary & Error Alarms ---
        # --- Executive Daily Summary & Error Alarms ---
        # --- Executive Daily Summary & Error Alarms ---
        st.write("### 📅 Daily Performance & Executive Summary")
        
        # Determine available dates in the dataset to set bounds, defaulting to current date if present
        max_available_date = pd.to_datetime(df['end_time']).dt.date.max()
        default_date = datetime.now().date()
        if pd.isna(max_available_date) or default_date > max_available_date:
            default_date = max_available_date if pd.notna(max_available_date) else datetime.now().date()

        # Date picker control for day-by-day inspection
        selected_summary_date = st.date_input(
            "Select Operational Date:", 
            value=default_date,
            key="daily_summary_date_picker"
        )

        # Filter dataset for the chosen date
        target_date_df = df[pd.to_datetime(df['end_time']).dt.date == selected_summary_date].copy()
        
        # Fetch live error datasets for contextual executive alarm tracking
        try:
            err_conn = get_db_conn()
            err_query = """
                SELECT t.site_id, t.reason_level_1, t.reason_level_3, t.final_cell_hr, t.end_time, m.owner, m.power_type 
                FROM total_cell_down t
                LEFT JOIN site_master m ON t.site_id = m.site_id
            """
            full_err_df = pd.read_sql(err_query, err_conn)
            err_conn.close()
        except Exception:
            full_err_df = pd.DataFrame()

        target_noc_df, target_oce_df = pd.DataFrame(), pd.DataFrame()
        if not full_err_df.empty:
            full_err_df['end_time_dt'] = pd.to_datetime(full_err_df['end_time'])
            
            def get_error_type(row):
                r1 = str(row.get('reason_level_1', '')).lower()
                r3 = str(row.get('reason_level_3', '')).lower()
                power = str(row.get('power_type', '')).strip()
                
                if power == 'Self Power' and ('tco' in r1 or 'towerco' in r1):
                    return "NOC Error"
                
                is_r3_invalid = not row.get('reason_level_3') or str(row.get('reason_level_3')).strip() == ""
                if power == 'Self Power' and ('tco' in r3 or 'tower' in r3 or is_r3_invalid):
                    return "OCE Error"
                return None

            full_err_df['Error_Type'] = full_err_df.apply(get_error_type, axis=1)
            day_err_df = full_err_df[full_err_df['end_time_dt'].dt.date == selected_summary_date]
            target_noc_df = day_err_df[day_err_df['Error_Type'] == "NOC Error"]
            target_oce_df = day_err_df[day_err_df['Error_Type'] == "OCE Error"]

        st.divider()

        # --- Balanced 50/50 Layout for Clean Reporting & Screenshotting ---
        col_table, col_alarms = st.columns(2)

        with col_table:
            st.markdown(f"#### Daily Analysis ({selected_summary_date.strftime('%d %b %Y')})")
            
            day_total_hr = target_date_df['final_cell_hr'].sum() if not target_date_df.empty else 0.0
            st.metric("Total Cell Hour", f"{day_total_hr:,.2f}")

            if not target_date_df.empty:
                df_target_day = target_date_df.groupby('reason_level_3')['final_cell_hr'].sum().reset_index()
                day_total = df_target_day['final_cell_hr'].sum()
                df_target_day['Daily Percent (%)'] = (df_target_day['final_cell_hr'] / day_total) * 100
                df_target_day.columns = ['Reason', 'Cell Hour', 'Daily Percent (%)']
                df_target_day = df_target_day[['Reason', 'Cell Hour', 'Daily Percent (%)']]

                column_config = {
                    "Reason": st.column_config.TextColumn("Reason", width="medium"),
                    "Cell Hour": st.column_config.NumberColumn("Cell Hour", format="%.2f", width="small"),
                    "Daily Percent (%)": st.column_config.ProgressColumn("Daily (%)", format="%.1f%%", min_value=0, max_value=100, width="medium"),
                }

                st.dataframe(
                    df_target_day, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config=column_config
                )
            else:
                st.info(f"No operational downtime recorded for {selected_summary_date.strftime('%d %b %Y')}.")

        with col_alarms:
            st.markdown(f"#### Operation Exceptions ({selected_summary_date.strftime('%d %b %Y')})")
            
            st.metric("Total Exception Count", len(target_noc_df) + len(target_oce_df))

            # Combine exceptions and include power_type alongside site_id, error type, and reason
            combined_exceptions = []
            for _, r in target_noc_df.iterrows():
                combined_exceptions.append({
                    "Site ID": r['site_id'], 
                    "Error Type": "NOC Error", 
                    "Power Type": r.get('power_type', 'N/A'),
                    "Reason": r['reason_level_1']
                })
            for _, r in target_oce_df.iterrows():
                combined_exceptions.append({
                    "Site ID": r['site_id'], 
                    "Error Type": "OCE Error", 
                    "Power Type": r.get('power_type', 'N/A'),
                    "Reason": r['reason_level_3']
                })
            
            exc_df = pd.DataFrame(combined_exceptions)

            if not exc_df.empty:
                st.dataframe(
                    exc_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Site ID": st.column_config.TextColumn("Site ID", width="small"),
                        "Error Type": st.column_config.TextColumn("Error Type", width="small"),
                        "Power Type": st.column_config.TextColumn("Power Type", width="small"),
                        "Reason": st.column_config.TextColumn("Reason", width="medium")
                    }
                )
            else:
                st.success("Operational Status: All sites Correct! (0 Exceptions).")

elif current_tab == "🔬 Site Daily Down Tracking":
    st.markdown("<h1>🔬 Operational Site Daily Breakdown</h1>", unsafe_allow_html=True)
    st.divider()

    # 1. Define cycle naming logic
    def get_cycle_name(dt):
        # May 21st - June 20th is considered the "June" cycle
        if dt.day >= 21:
            return (dt + pd.DateOffset(months=1)).strftime("%B %Y")
        else:
            return dt.strftime("%B %Y")

    # 2. Fetch all required data
    conn = get_db_conn()
    tracking_query = """
        SELECT 
            t.end_time, 
            t.site_id, 
            t.final_cell_hr, 
            t.reason_level_3, 
            m.fot_teams AS team, 
            m.owner 
        FROM total_cell_down t 
        LEFT JOIN site_master m ON t.site_id = m.site_id
    """
    tracking_data_all = pd.read_sql(tracking_query, conn)
    conn.close()

    if not tracking_data_all.empty:
        tracking_data_all['end_time'] = pd.to_datetime(tracking_data_all['end_time'])
        tracking_data_all['Cycle'] = tracking_data_all['end_time'].apply(get_cycle_name)
        tracking_data_all['owner'] = tracking_data_all['owner'].fillna('Unknown Owner').astype(str).str.strip()
        
        #=======================================================================
        # 1. Define cycle selection (ensure this happens before the loop)
        sorted_cycles = sorted(tracking_data_all['Cycle'].unique(), reverse=True)
        selected_cycle_name = st.selectbox("🗓️ Select Cycle:", sorted_cycles)

        # Parse the selected cycle name back into a date (e.g., "June 2026" -> June 1, 2026)
        selected_dt = pd.to_datetime(selected_cycle_name)

        # Define the 21st-to-20th cycle boundaries
        # Start is the 21st of the previous month
        start_cycle = (selected_dt - pd.DateOffset(months=1)).replace(day=21)
        # End is the 20th of the current month
        end_cycle = selected_dt.replace(day=20, hour=23, minute=59, second=59)

        # Calculate days passed
        # If the current date is past the end_cycle, use the full cycle duration
        # Otherwise, use the time elapsed since the start_cycle
        today = datetime.now()
        if today > end_cycle:
            days_passed = (end_cycle - start_cycle).days + 1
        else:
            days_passed = (today - start_cycle).days + 1

        # Now filter your data
        tracking_data = tracking_data_all[tracking_data_all['Cycle'] == selected_cycle_name].copy()


        #====================================================
        tracking_data['Date_Str'] = tracking_data['end_time'].dt.strftime('%d-%b')
        unique_dates_sorted = tracking_data.sort_values(by='end_time')['Date_Str'].unique()
        all_reasons = sorted(tracking_data['reason_level_3'].dropna().unique())
        
        # --- Pinned Table Helper ---
        def display_pinned_table(df, unique_dates):
            pinned_cols = ['team', 'site_id', 'Times down', 'Avg', 'Total', '%']
            col_config = {
                    "team": st.column_config.TextColumn("Team", width="auto", pinned=True),
                    "site_id": st.column_config.TextColumn("Site ID", width="small", pinned=True),
                    "Times down": st.column_config.NumberColumn("Times down", format="%d", width="small", pinned=True),
                    "Avg": st.column_config.NumberColumn("Avg", format="%.1f", width="small", pinned=True),
                    "Total": st.column_config.NumberColumn("Total", format="%.1f", width="small", pinned=True),
                    # Removed alignment="center" from ProgressColumn below:
                    "%": st.column_config.ProgressColumn("%", format="%.1f%%", min_value=0, max_value=100, width="auto", pinned=True),
            }
    
              
            for d_col in unique_dates:
                    col_config[d_col] = st.column_config.NumberColumn(d_col, format="%.1f", width="small", alignment="center")
                
      
    
            st.data_editor(
                df, 
                use_container_width=True, 
                hide_index=True, 
                disabled=True,
                column_order=pinned_cols + list(unique_dates), 
                column_config=col_config
            )

                

        #--------------------------#
    
        # 5. Display breakdown by reason
        for reason in all_reasons:
            reason_filtered_df = tracking_data[tracking_data['reason_level_3'] == reason].copy()
            
            if not reason_filtered_df.empty:
                reason_total_hours = reason_filtered_df['final_cell_hr'].sum()
                
                # --- TOWERCO SPECIAL HANDLING ---
                if reason == "Towerco power issue":
                    days_passed = (datetime.now() - start_cycle).days + 1
                    
                    st.markdown("---")
                    col_h1, col_h2 = st.columns([2, 1])
                    with col_h1:
                        st.markdown(f"## ⚡ Grid Matrix: **Towerco power issue**")
                    with col_h2:
                        st.metric("Total Sites", reason_filtered_df['site_id'].nunique())
                        st.metric("Total Cell*HR", f"{reason_total_hours:,.1f}")

                    st.markdown("### 📋 Cell Hour Impact by Towerco Owner")
                    total_all_owners = reason_filtered_df['final_cell_hr'].sum()
                    
                    summary_df = reason_filtered_df.groupby('owner').agg(
                        Sites=('site_id', 'nunique'),
                        Total_Cell_Hour=('final_cell_hr', 'sum')
                    ).reset_index()
                    
                    summary_df['Avg Cell Hour'] = summary_df['Total_Cell_Hour'] / days_passed 
                    summary_df['Percent'] = (summary_df['Total_Cell_Hour'] / total_all_owners) * 100
                    summary_df = summary_df.sort_values(by='Total_Cell_Hour', ascending=False)
                    
                    st.dataframe(
                        summary_df, 
                        column_config={
                                "owner": st.column_config.TextColumn("Owner", width="small", alignment="center"),
                                "Sites": st.column_config.NumberColumn("Sites", width="small", alignment="center"),
                                "Total_Cell_Hour": st.column_config.NumberColumn("Total Cell*HR", format="%.1f", width="small", alignment="center"),
                                "Avg Cell Hour": st.column_config.NumberColumn("Avg Cell Hour", format="%.1f", width="small", alignment="center"),
                                "Percent": st.column_config.ProgressColumn(
                                    "Percent", 
                                    format="%.1f%%", 
                                    width="medium", 
                                    min_value=0, 
                                    max_value=100
                                ),
                        },
                        use_container_width= True, hide_index=True
                    )
                    
                    unique_owners = sorted(reason_filtered_df['owner'].unique())
                    for owner in unique_owners:
                        owner_df = reason_filtered_df[reason_filtered_df['owner'] == owner].copy()
                        owner_total = owner_df['final_cell_hr'].sum()
                        
                        st.markdown(f"#### 🏢 **Towerco: {owner}** | Sites: {owner_df['site_id'].nunique()} | Total: {owner_total:,.1f} Cell*HR")
                        
                        site_pivot = owner_df.pivot_table(index=['team', 'site_id'], columns='Date_Str', values='final_cell_hr', aggfunc='sum', fill_value=0.0)
                        site_pivot = site_pivot.reindex(columns=unique_dates_sorted, fill_value=0.0)
                        
                        site_pivot['Total'] = site_pivot[unique_dates_sorted].sum(axis=1)
                        site_pivot['Times down'] = (site_pivot[unique_dates_sorted] > 0).sum(axis=1)
                        # Standardized column name to 'Avg' for the helper function
                        site_pivot['Avg'] = site_pivot['Total'] / days_passed 
                        site_pivot['%'] = (site_pivot['Total'] / owner_total) * 100
                        
                        site_pivot_clean = site_pivot.reset_index().sort_values(by='Total', ascending=False)
                        
                        # Use the helper function to display with frozen columns
                        display_pinned_table(site_pivot_clean, unique_dates_sorted)
                
                # --- HANDLING FOR OTHER CATEGORIES ---
                else:
                    site_pivot = reason_filtered_df.pivot_table(
                        index=['team', 'site_id'],
                        columns='Date_Str',
                        values='final_cell_hr',
                        aggfunc='sum',
                        fill_value=0.0
                    )
                    site_pivot = site_pivot.reindex(columns=unique_dates_sorted, fill_value=0.0)
                    
                    site_pivot['Times down'] = (site_pivot[unique_dates_sorted] > 0).sum(axis=1).astype(int)
                    site_pivot['Total'] = site_pivot[unique_dates_sorted].sum(axis=1).astype(float)
                    # Standardized column name to 'Avg' for the helper function
                    site_pivot['Avg'] = site_pivot[unique_dates_sorted].mean(axis=1).astype(float)
                    # Added calculation for % to match the layout
                    site_pivot['%'] = (site_pivot['Total'] / reason_total_hours) * 100
                    
                    site_pivot_clean = site_pivot.reset_index()
                    site_pivot_clean = site_pivot_clean[site_pivot_clean['Times down'] > 0]
                    
                    reason_site_count = site_pivot_clean['site_id'].nunique()
                    
                    st.write("---")
                    st.markdown(
                        f"### 📊 Grid Matrix: **{reason}** "
                        f"<span style='color:#FF4B4B;'>(Sites: {reason_site_count} | Total: {reason_total_hours:,.1f} Cell*HR)</span>", 
                        unsafe_allow_html=True
                    )
                    
                    site_pivot_clean = site_pivot_clean.sort_values(by='Total', ascending=False)
                    
                    if not site_pivot_clean.empty:
                        # Use the helper function to display with frozen columns
                        display_pinned_table(site_pivot_clean, unique_dates_sorted)
    else:
        st.info("ℹ️ No records found.")

elif current_tab == "📥 Export Data":
    st.markdown("<h1>📥 Operational Report Data Extraction</h1>", unsafe_allow_html=True)
    st.divider()
    st.write("Select a date range and a specific downtime reason to extract a custom Excel report.")
    
    col_d1, col_d2, col_r = st.columns(3)
    with col_d1:
        start_date = st.date_input("🗓️ Start Date", value=datetime.now().date() - timedelta(days=30))
    with col_d2:
        end_date = st.date_input("🗓️ End Date", value=datetime.now().date())
    with col_r:
        conn = get_db_conn()
        available_reasons = ["All Reasons"] + list(pd.read_sql("SELECT DISTINCT reason_level_3 FROM total_cell_down WHERE reason_level_3 IS NOT NULL", conn)['reason_level_3'].unique())
        conn.close()
        selected_reason = st.selectbox("🔬 Select Reason Level 3", options=available_reasons)
        
    if st.button("🔍 Generate Excel Report"):
        conn = get_db_conn()
        if selected_reason == "All Reasons":
            export_query = """
                SELECT 
                    site_id AS "Site Code",
                    alarm_name AS "Alarm Name/Cell ID",
                    start_time AS "Start Time",
                    end_time AS "End Time",
                    reason_level_1 AS "Reason Level 1",
                    reason_level_3 AS "Reason Level 3",
                    final_cell_hr AS "Total Cell Hour"
                FROM total_cell_down
                WHERE end_time::date >= %s AND end_time::date <= %s
                ORDER BY end_time DESC
            """
            export_df = pd.read_sql(export_query, conn, params=(start_date, end_date))
        else:
            export_query = """
                SELECT 
                    site_id AS "Site Code",
                    alarm_name AS "Alarm Name/Cell ID",
                    start_time AS "Start Time",
                    end_time AS "End Time",
                    reason_level_1 AS "Reason Level 1",
                    reason_level_3 AS "Reason Level 3",
                    final_cell_hr AS "Total Cell Hour"
                FROM total_cell_down
                WHERE end_time::date >= %s AND end_time::date <= %s AND reason_level_3 = %s
                ORDER BY end_time DESC
            """
            export_df = pd.read_sql(export_query, conn, params=(start_date, end_date, selected_reason))
            
        conn.close()
        
        if not export_df.empty:
            st.success(f"📊 Found {len(export_df)} operational logs matching your criteria.")
            st.dataframe(export_df, use_container_width=True)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                export_df.to_excel(writer, sheet_name='Operational Report', index=False)
            processed_data = output.getvalue()
            
            file_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            sanitized_reason = selected_reason.replace(" ", "_").lower()
            filename = f"network_down_report_{sanitized_reason}_{file_ts}.xlsx"
            
            st.download_button(
                label="📥 Download Excel Report",
                data=processed_data,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("⚠️ No operational records found for the chosen date range and criteria.")

elif current_tab == "⚠️ Error Checking":
    st.markdown("<h1>⚠️ Data Integrity & Error Checking</h1>", unsafe_allow_html=True)
    st.divider()

    conn = get_db_conn()
    query = """
        SELECT t.site_id, t.reason_level_1, t.reason_level_3, t.final_cell_hr, m.owner, m.power_type 
        FROM total_cell_down t
        LEFT JOIN site_master m ON t.site_id = m.site_id
    """
    df = pd.read_sql(query, conn)
    conn.close()

    if not df.empty:
        st.subheader("📋 Configuration Review")

        # --- 1. Owner NOT MyTel (Self Power) ---
        not_mytel_df = df[(df['owner'].str.lower() != 'mytel') & (df['power_type'] == 'Self Power') & (df['reason_level_3'].notna())]
        
        # --- Adjusted Section ---
        st.write("#### 🛡️ Towerco Sites (Power: Self Power)")
        
        # Calculate Stats
        total_not_mytel = not_mytel_df['site_id'].nunique()
        owner_counts_nm = not_mytel_df.groupby('owner')['site_id'].nunique()

        # Create enough columns to fit the number of owners + 1 (for total)
        cols = st.columns(len(owner_counts_nm) + 1)
        
        # Shorten the label to avoid truncation
        cols[0].metric("All Sites", total_not_mytel) 
        
        for i, (owner, count) in enumerate(owner_counts_nm.items()):
            # Using just the owner name keeps the label short
            cols[i+1].metric(f"{owner}", count)
        
        if not not_mytel_df.empty:
            st.dataframe(not_mytel_df, use_container_width=True)
        else:
            st.info("No records found.")

        st.divider()

        # --- 2. Owner MyTel (Share Power) ---
        mytel_share_df = df[(df['owner'].str.lower() == 'mytel') & (df['power_type'] == 'Share Power') & (df['reason_level_3'].notna())]
        
        st.write("#### 📶 MyTel (Power: Share Power)")
        # Calculate Stats
        total_mytel = mytel_share_df['site_id'].nunique()
        
        # Display Metrics
        col1, col2 = st.columns(2)
        col1.metric("Total Sites", total_mytel)
        
        if not mytel_share_df.empty:
            st.dataframe(mytel_share_df, use_container_width=True)
        else:
            st.info("No records found.")

        st.divider()

        # --- 3. NOC & OCE Error Analysis ---
        st.subheader("🔍 Identified Errors")
        def get_error_type(row):
            # Standardize inputs
            r1 = str(row.get('reason_level_1', '')).lower()
            r3 = str(row.get('reason_level_3', '')).lower()
            power = str(row.get('power_type', '')).strip()
            
            # 1. NOC Error Logic
            # Power must be 'Self Power' AND (reason_level_1 must contain 'tco' OR 'towerco')
            if power == 'Self Power' and ('tco' in r1 or 'towerco' in r1):
                return "NOC Error"
                
            # 2. OCE Error Logic
            # Power must be 'Self Power' AND (reason_level_3 contains 'tco' OR 'tower' OR is blank)
            # Note: 'tower' will catch 'towerco' as well
            is_r3_invalid = not row.get('reason_level_3') or str(row.get('reason_level_3')).strip() == ""
            
            if power == 'Self Power' and ('tco' in r3 or 'tower' in r3 or is_r3_invalid):
                return "OCE Error"
                
            return None

        # Apply logic
        df['Error_Type'] = df.apply(get_error_type, axis=1)
        
        # Create separate DataFrames for each error type
        noc_df = df[df['Error_Type'] == "NOC Error"]
        oce_df = df[df['Error_Type'] == "OCE Error"]

        # Display NOC Errors
        st.write("---")
        st.subheader("🔴 NOC Errors")
        st.metric("Total NOC Error Sites", len(noc_df))
        if not noc_df.empty:
            st.dataframe(noc_df, use_container_width=True)
        else:
            st.success("No NOC errors found.")

        # Display OCE Errors
        st.write("---")
        st.subheader("🔵 OCE Errors")
        st.metric("Total OCE Error Sites", len(oce_df))
        if not oce_df.empty:
            st.dataframe(oce_df, use_container_width=True)
        else:
            st.success("No OCE errors found.")
    else:
        st.info("No data available.")

elif current_tab == "🏆 Team Performance":
    st.markdown("<h1>🏆 Team Performance Dashboard</h1>", unsafe_allow_html=True)
    
    conn = get_db_conn()
    # Fetch correctly using 'fot_teams'
    master_df = pd.read_sql("SELECT site_id, fot_teams FROM site_master", conn)
    down_df = pd.read_sql("SELECT final_cell_hr, end_time, site_id FROM total_cell_down", conn)
    conn.close()

    if not master_df.empty:
        # 1. Prepare static team sites (using full master list)
        master_df['fot_teams'] = master_df['fot_teams'].fillna('Unassigned') 
        static_team_sites = master_df.groupby('fot_teams')['site_id'].nunique().reset_index()
        static_team_sites.columns = ['fot_teams', 'Total_Sites']

        # 2. Prepare Downtime Data
        down_df['end_time'] = pd.to_datetime(down_df['end_time'])
        down_df['cycle'] = down_df['end_time'].apply(lambda x: (x + pd.DateOffset(months=1)).strftime("%B %Y") if x.day >= 21 else x.strftime("%B %Y"))
        
        all_cycles = sorted(down_df['cycle'].unique(), reverse=True)
        selected_cycles = st.multiselect("🗓️ Select Cycle Periods:", options=all_cycles, default=all_cycles[0] if all_cycles else None)
        
        if selected_cycles:
            # Filter and add 'fot_teams' to downtime data via merge
            filtered_down = down_df[down_df['cycle'].isin(selected_cycles)]
            merged_down = filtered_down.merge(master_df[['site_id', 'fot_teams']], on='site_id', how='left')
            
            # Aggregate downtime by team
            team_down_agg = merged_down.groupby('fot_teams')['final_cell_hr'].sum().reset_index()
            team_down_agg.columns = ['fot_teams', 'Total_Cell_Hr']
            
            # 3. Merge: Start with static counts, then add downtime data
            team_perf = static_team_sites.merge(team_down_agg, on='fot_teams', how='left').fillna(0)
            
            # 4. Calculate Index (Cell Hr / Fixed Total Sites) and Ranking
            team_perf['Cell_Hr_Per_Site'] = team_perf['Total_Cell_Hr'] / team_perf['Total_Sites']
            team_perf = team_perf.sort_values('Cell_Hr_Per_Site', ascending=True)
            team_perf['Rank'] = range(1, len(team_perf) + 1)
            
            # Display Table
            st.dataframe(
                team_perf[['fot_teams', 'Total_Sites', 'Total_Cell_Hr', 'Cell_Hr_Per_Site', 'Rank']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "fot_teams": st.column_config.TextColumn("Team Name",alignment='center',width='auto'),
                    "Total_Sites": st.column_config.NumberColumn("Total Sites", format="%d",alignment='center',width='auto'),
                    "Total_Cell_Hr": st.column_config.NumberColumn("Total Cell Hr", format="%.1f",alignment='center',width='auto'),
                    "Cell_Hr_Per_Site": st.column_config.ProgressColumn(
                        "Performance Index (Cell Hr / Site)",
                        format="%.2f",
                        min_value=0,
                        max_value=float(team_perf['Cell_Hr_Per_Site'].max()) if team_perf['Cell_Hr_Per_Site'].max() > 0 else 1
                    ),
                    "Rank": st.column_config.NumberColumn("Rank", format="%d",alignment='center',width='auto')
                }
            )
        else:
            st.warning("Please select at least one cycle.")
    else:
        st.info("No data available in master database.")
