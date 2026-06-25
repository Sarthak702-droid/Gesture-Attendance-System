import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Gesture Attendance System Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark Mode / Custom Aesthetics Styling (Pulse Theme Override)
st.markdown(
    """
    <style>
        :root {
          --bg: #fafaf9; --fg: #1c1b1a; --muted: #6b6964; --border: #e6e4e0;
          --accent: #c96442; --surface: #ffffff; --good: #2f7d4a; --bad: #b53a2a;
        }
        
        /* Set backgrounds & text colors globally */
        .stApp {
            background-color: var(--bg) !important;
            color: var(--fg) !important;
            font-family: -apple-system, system-ui, sans-serif !important;
        }
        
        /* Style main container padding */
        .main .block-container {
            padding-left: 28px !important;
            padding-right: 28px !important;
            padding-top: 24px !important;
            padding-bottom: 56px !important;
            max-width: 100% !important;
        }

        /* Style sidebar */
        [data-testid="stSidebar"] {
            background-color: var(--surface) !important;
            border-right: 1px solid var(--border) !important;
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
            color: var(--fg) !important;
        }
        [data-testid="stSidebar"] [data-testid="stHeader"] {
            background-color: var(--surface) !important;
        }
        
        /* Title and description text styling */
        h1, h2, h3, h4, h5, h6 {
            color: var(--fg) !important;
            font-family: -apple-system, system-ui, sans-serif !important;
            font-weight: 600 !important;
            letter-spacing: -0.01em !important;
            margin-top: 0 !important;
        }
        h1 {
            font-size: 20px !important;
            margin-bottom: 4px !important;
        }
        
        /* Tabs customization to match template nav active state */
        div[data-baseweb="tab-list"] {
            background-color: transparent !important;
            border-bottom: 1px solid var(--border) !important;
            gap: 2px !important;
            margin-bottom: 24px !important;
        }
        button[data-baseweb="tab"] {
            background-color: transparent !important;
            border: none !important;
            color: var(--muted) !important;
            font-size: 14px !important;
            font-weight: 500 !important;
            padding: 7px 10px !important;
            border-radius: 6px !important;
            font-family: -apple-system, system-ui, sans-serif !important;
        }
        button[data-baseweb="tab"]:hover {
            background-color: var(--border) !important;
            color: var(--fg) !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            background-color: var(--surface) !important;
            color: var(--fg) !important;
            border: 1px solid var(--border) !important;
            border-bottom: 1px solid var(--surface) !important;
            font-weight: 500 !important;
        }

        /* KPI Grid matching the Pulse style */
        .kpis {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 28px;
            width: 100%;
        }
        @media (max-width: 900px) {
            .kpis {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        .kpi-card {
            background: var(--surface) !important;
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
            padding: 16px 18px !important;
        }
        .kpi-card .label {
            font-size: 11px !important;
            color: var(--muted) !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            margin-bottom: 8px !important;
            font-weight: 500 !important;
        }
        .kpi-card .value {
            font-size: 28px !important;
            color: var(--fg) !important;
            letter-spacing: -0.02em !important;
            font-weight: 600 !important;
            line-height: 1.1 !important;
        }
        .kpi-card .delta {
            font-size: 12px !important;
            margin-top: 4px !important;
            font-weight: 500 !important;
        }
        .kpi-card .delta.up {
            color: var(--good) !important;
        }
        .kpi-card .delta.down {
            color: var(--bad) !important;
        }

        /* Panel container */
        .panel-container {
            background: var(--surface) !important;
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
            padding: 20px !important;
            margin-bottom: 16px !important;
        }
        .panel-container h3 {
            margin: 0 0 16px 0 !important;
            font-size: 14px !important;
            font-weight: 500 !important;
            color: var(--fg) !important;
            border: none !important;
        }

        /* Row layout */
        .panels-row {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 16px;
            margin-bottom: 16px;
        }
        @media (max-width: 900px) {
            .panels-row {
                grid-template-columns: 1fr;
            }
        }

        /* SVG Chart area */
        .chart {
            height: 240px;
            background: linear-gradient(180deg, rgba(201,100,66,0.06), transparent);
            border-bottom: 1px solid var(--border);
            position: relative;
            overflow: hidden;
            border-radius: 6px;
            padding: 10px;
        }

        /* Clean custom tables */
        table.custom-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 8px;
        }
        table.custom-table th, table.custom-table td {
            text-align: left;
            padding: 10px 6px;
            border-top: 1px solid var(--border);
        }
        table.custom-table th {
            font-size: 11px;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            font-weight: 500;
            border-top: none;
        }
        table.custom-table td {
            font-size: 13px;
            color: var(--fg);
        }

        /* Status Pills */
        .pill {
            display: inline-block;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 999px;
            background: var(--bg);
            border: 1px solid var(--border);
            font-weight: 500;
        }
        .pill.good {
            color: var(--good);
            background-color: rgba(47,125,74,0.06);
            border-color: rgba(47,125,74,0.25);
        }
        .pill.bad {
            color: var(--bad);
            background-color: rgba(181,58,42,0.06);
            border-color: rgba(181,58,42,0.25);
        }
        .pill.warn {
            color: #b45309;
            background-color: rgba(180,83,9,0.06);
            border-color: rgba(180,83,9,0.25);
        }

        /* Standard interactive inputs */
        div[data-baseweb="input"] {
            background-color: var(--surface) !important;
            border: 1px solid var(--border) !important;
            border-radius: 6px !important;
        }
        input {
            color: var(--fg) !important;
            background-color: transparent !important;
        }
        
        /* Button overrides to match design */
        div.stButton > button {
            background-color: transparent !important;
            color: var(--fg) !important;
            border: 1px solid var(--border) !important;
            border-radius: 6px !important;
            padding: 6px 12px !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            transition: background 0.1s ease-in-out !important;
            font-family: inherit !important;
        }
        div.stButton > button:hover {
            background-color: var(--bg) !important;
            border-color: var(--muted) !important;
        }

        /* Primary buttons like "Download" */
        div.stDownloadButton > button {
            background-color: var(--accent) !important;
            color: white !important;
            border: 1px solid var(--accent) !important;
            border-radius: 6px !important;
            padding: 7px 13px !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            transition: background 0.1s ease-in-out !important;
            font-family: inherit !important;
        }
        div.stDownloadButton > button:hover {
            background-color: #b05537 !important;
            border-color: #b05537 !important;
            color: white !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

def parse_duration_to_hours(duration_str):
    if not isinstance(duration_str, str) or not duration_str or duration_str == "N/A":
        return 0.0
    try:
        parts = duration_str.strip().split()
        if len(parts) >= 2:
            val = float(parts[0])
            unit = parts[1].lower()
            if "sec" in unit:
                return val / 3600.0
            elif "min" in unit:
                return val / 60.0
            elif "hour" in unit:
                return val
    except Exception:
        pass
    return 0.0

def generate_svg_chart(daily_stats):
    """
    Generates a clean responsive SVG chart matching the Pulse terracotta theme.
    """
    if daily_stats.empty:
        return '<div style="color: var(--muted); text-align: center; padding: 40px 0;">No trend data available</div>'
        
    dates = [d.strftime('%b %d') for d in daily_stats.index]
    
    # Calculate check-ins
    ins = pd.Series(0, index=daily_stats.index)
    if 'IN' in daily_stats.columns:
        ins = ins + daily_stats['IN']
    if 'PRESENT' in daily_stats.columns:
        ins = ins + daily_stats['PRESENT']
        
    # Calculate check-outs
    outs = pd.Series(0, index=daily_stats.index)
    if 'OUT' in daily_stats.columns:
        outs = outs + daily_stats['OUT']
        
    max_val = max(1, max(ins.max(), outs.max()))
    
    width = 600
    height = 200
    padding_left = 40
    padding_right = 20
    padding_top = 20
    padding_bottom = 30
    
    chart_w = width - padding_left - padding_right
    chart_h = height - padding_top - padding_bottom
    
    num_days = len(dates)
    col_width = chart_w / max(1, num_days)
    
    svg = f'<svg viewBox="0 0 {width} {height}" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" style="font-family: inherit;">'
    
    # Draw Y gridlines
    for i in range(4):
        val = int(max_val * i / 3)
        y = padding_top + chart_h - (val / max_val) * chart_h
        svg += f'<line x1="{padding_left}" y1="{y}" x2="{width - padding_right}" y2="{y}" stroke="var(--border)" stroke-dasharray="2 2" stroke-width="1" />'
        svg += f'<text x="{padding_left - 10}" y="{y + 4}" font-size="10" fill="var(--muted)" text-anchor="end">{val}</text>'
        
    # Draw bars
    for idx, (date, check_in_cnt, check_out_cnt) in enumerate(zip(dates, ins, outs)):
        x_center = padding_left + idx * col_width + col_width / 2
        
        in_h = (check_in_cnt / max_val) * chart_h
        out_h = (check_out_cnt / max_val) * chart_h
        
        # Check-in bar (Terracotta / Accent)
        bar_w = max(4.0, col_width * 0.3)
        x_in = x_center - bar_w - 2
        y_in = padding_top + chart_h - in_h
        if in_h > 0:
            svg += f'<rect x="{x_in}" y="{y_in}" width="{bar_w}" height="{max(1.0, in_h)}" fill="var(--accent)" rx="2" />'
        
        # Check-out bar (Muted)
        x_out = x_center + 2
        y_out = padding_top + chart_h - out_h
        if out_h > 0:
            svg += f'<rect x="{x_out}" y="{y_out}" width="{bar_w}" height="{max(1.0, out_h)}" fill="var(--muted)" rx="2" opacity="0.6" rx="2" />'
        
        # X labels
        if num_days < 10 or idx % (num_days // 5 + 1) == 0:
            svg += f'<text x="{x_center}" y="{height - 8}" font-size="10" fill="var(--muted)" text-anchor="middle">{date}</text>'
            
    svg += '</svg>'
    return svg

def render_custom_table(df_to_render, columns_mapping, pill_column=None, status_classes=None):
    """
    Renders a pandas DataFrame as a clean HTML table matching the Pulse template.
    """
    if df_to_render.empty:
        return "<div style='color: var(--muted); padding: 12px;'>No records found.</div>"
        
    html = '<table class="custom-table"><thead><tr>'
    for col in columns_mapping.keys():
        html += f'<th>{columns_mapping[col]}</th>'
    html += '</tr></thead><tbody>'
    
    for _, row in df_to_render.iterrows():
        html += '<tr>'
        for col in columns_mapping.keys():
            val = row[col]
            if col == pill_column and status_classes:
                css_class = status_classes.get(str(val).upper(), 'pill')
                html += f'<td><span class="{css_class}">{val}</span></td>'
            else:
                html += f'<td>{val}</td>'
        html += '</tr>'
    html += '</tbody></table>'
    return html


CSV_PATH = os.path.join("data", "attendance.csv")
XLSX_PATH = os.path.join("data", "attendance.xlsx")

# Auto-refresh helper using JS
st.html(
    """
    <script>
    setTimeout(function() {
        window.parent.location.reload();
    }, 5000);
    </script>
    """
)

st.sidebar.markdown(
    '''
    <div class="brand" style="font-size: 18px; font-weight: 600; padding: 8px 10px 18px; color: var(--fg); font-family: -apple-system, system-ui, sans-serif;">
      ◐ Pulse Attendance
    </div>
    ''',
    unsafe_allow_html=True
)

# Load Data
if not os.path.exists(CSV_PATH) or os.stat(CSV_PATH).st_size == 0:
    st.info("👋 Welcome! No attendance records found yet.")
    st.warning("Please launch the webcam camera app and register attendance first.")
    
    st.markdown("### How to start:")
    st.code("python src/main.py", language="bash")
else:
    try:
        # Load CSV data
        df = pd.read_csv(CSV_PATH)
        
        # Pre-process dates
        df['Date'] = pd.to_datetime(df['Date'])
        df_sorted = df.sort_values(by=['Date', 'Time'], ascending=[False, False])
        
        # Sidebar Filters
        st.sidebar.header("🔍 Filters")
        
        # Search by name
        search_query = st.sidebar.text_input("Search Student/Employee Name", "")
        
        # Date Filter
        min_date = df['Date'].min().date()
        max_date = df['Date'].max().date()
        
        start_date, end_date = st.sidebar.date_input(
            "Select Date Range",
            value=[min_date, max_date],
            min_value=min_date,
            max_value=max_date
        )
        
        # Apply filters
        filtered_df = df.copy()
        if search_query:
            filtered_df = filtered_df[filtered_df['Name'].str.contains(search_query, case=False, na=False)]
            
        filtered_df = filtered_df[
            (filtered_df['Date'].dt.date >= start_date) & 
            (filtered_df['Date'].dt.date <= end_date)
        ]
        
        # Format Date back to string for clean display
        display_df = filtered_df.copy()
        display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
        
        # Topbar title
        st.markdown(
            f'''
            <div class="topbar" style="padding: 16px 0; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); margin-bottom: 24px;">
              <h1 style="font-size: 20px; margin: 0; letter-spacing: -0.01em; color: var(--fg); font-weight: 600;">Overview &middot; {datetime.now().strftime('%B %Y')}</h1>
              <div class="right" style="color: var(--muted); font-size: 13px; font-weight: 500;">Gesture Control System</div>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        # Create Tabs
        tab1, tab2 = st.tabs(["Overview", "Wages & Payroll"])
        
        with tab1:
            # Metrics Calculations
            total_logs = len(filtered_df)
            present_count = len(filtered_df[filtered_df['Status'].isin(['IN', 'PRESENT', 'URGENT_RETURN'])])
            absent_count = len(filtered_df[filtered_df['Status'].isin(['OUT', 'URGENT_EXIT'])])
            active_employees = len(filtered_df['Name'].unique()) if not filtered_df.empty else 0
            
            # KPI Cards
            st.markdown(
                f'''
                <div class="kpis">
                  <div class="kpi-card">
                    <div class="label">Total Logs</div>
                    <div class="value">{total_logs}</div>
                    <div class="delta up">+{total_logs} logged</div>
                  </div>
                  <div class="kpi-card">
                    <div class="label">Active Employees</div>
                    <div class="value">{active_employees}</div>
                    <div class="delta up">this period</div>
                  </div>
                  <div class="kpi-card">
                    <div class="label">IN / Present</div>
                    <div class="value">{present_count}</div>
                    <div class="delta up">active inside</div>
                  </div>
                  <div class="kpi-card">
                    <div class="label">OUT / Absent</div>
                    <div class="value">{absent_count}</div>
                    <div class="delta down">{absent_count} out/exited</div>
                  </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
            
            # 2. Charts and Data Visualizations (Pulse Style Grid)
            daily_stats = filtered_df.groupby([filtered_df['Date'].dt.date, 'Status']).size().unstack(fill_value=0)
            chart_svg = generate_svg_chart(daily_stats)
            
            # Active status table for the right-hand panel
            latest_logs = filtered_df.sort_values(by='Timestamp').groupby('Name').last().reset_index()
            latest_logs_display = latest_logs[['Name', 'Time', 'Status']].head(4)
            
            status_mapping = {
                'IN': 'pill good',
                'URGENT_RETURN': 'pill good',
                'PRESENT': 'pill good',
                'OUT': 'pill bad',
                'URGENT_EXIT': 'pill bad'
            }
            
            signups_table_html = render_custom_table(
                latest_logs_display,
                {'Name': 'Employee', 'Time': 'Last Time', 'Status': 'Status'},
                pill_column='Status',
                status_classes=status_mapping
            )
            
            # Render Panels Row
            col_chart, col_signups = st.columns([2, 1])
            
            with col_chart:
                st.markdown(
                    f'''
                    <div class="panel-container">
                      <h3>Daily Shifts Attendance Trends</h3>
                      <div class="chart">
                        {chart_svg}
                      </div>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
                
            with col_signups:
                st.markdown(
                    f'''
                    <div class="panel-container" style="height: 100%;">
                      <h3>Last Seen Status</h3>
                      {signups_table_html}
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
     
            # 3. Main Data Table
            st.markdown("---")
            
            # Download buttons
            c_dl1, c_dl2 = st.columns([1, 4])
            with c_dl1:
                if os.path.exists(XLSX_PATH):
                    with open(XLSX_PATH, "rb") as file:
                        st.download_button(
                            label="📥 Download Excel (.xlsx)",
                            data=file,
                            file_name=f"Attendance_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                else:
                    csv_data = display_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download CSV Report",
                        data=csv_data,
                        file_name="Attendance_Report.csv",
                        mime="text/csv"
                    )
            
            table_df = display_df[['Time', 'Name', 'Status', 'Day']].sort_values(by=['Date', 'Time'], ascending=[False, False])
            custom_table_html = render_custom_table(
                table_df,
                {'Time': 'Time', 'Name': 'Employee', 'Status': 'Event', 'Day': 'Day'},
                pill_column='Status',
                status_classes=status_mapping
            )
            
            st.markdown(
                f'''
                <div class="panel-container">
                  <h3>Recent Events Log</h3>
                  {custom_table_html}
                </div>
                ''',
                unsafe_allow_html=True
            )
            
        with tab2:
            st.markdown("### 💰 Estimated Employee Payroll & Wage Calculations")
            st.markdown("Calculate daily and monthly wages based on net hours worked (less break times) and late arrival penalties.")
            
            # Load config defaults
            import config
            default_hourly = float(getattr(config, "HOURLY_RATE", 500.0))
            default_penalty = float(getattr(config, "LATE_PENALTY_RATE", 100.0))
            default_start = getattr(config, "OFFICE_START_TIME", "09:00")
            
            # Config controls in the dashboard tab
            c1, c2, c3 = st.columns(3)
            with c1:
                hourly_rate = st.number_input("Hourly Pay Rate (Rs.)", min_value=0.0, value=default_hourly, step=50.0)
            with c2:
                penalty_rate = st.number_input("Late Penalty Rate (Rs.)", min_value=0.0, value=default_penalty, step=10.0)
            with c3:
                office_start_str = st.text_input("Office Expected Start Time (24h format)", value=default_start)
                
            # Helper to convert HH:MM:SS to minutes from midnight
            def time_to_min(t_str):
                try:
                    parts = [int(x) for x in t_str.split(':')]
                    return parts[0] * 60 + parts[1]
                except Exception:
                    return 0
            
            records = []
            
            # Ensure Date_parsed column is available
            calc_df = filtered_df.copy()
            if not calc_df.empty:
                calc_df['Date_parsed'] = pd.to_datetime(calc_df['Date'])
                df_grouped = calc_df.groupby(['Name', calc_df['Date_parsed'].dt.date])
                
                for (name, date_val), group in df_grouped:
                    group = group.sort_values(by='Timestamp')
                    
                    # IN / OUT logs
                    in_logs = group[group['Status'] == 'IN']
                    out_logs = group[group['Status'] == 'OUT']
                    present_logs = group[group['Status'] == 'PRESENT']
                    
                    earliest_in_row = None
                    latest_out_row = None
                    
                    if not in_logs.empty:
                        earliest_in_row = in_logs.iloc[0]
                    elif not present_logs.empty:
                        earliest_in_row = present_logs.iloc[0]
                        
                    if not out_logs.empty:
                        latest_out_row = out_logs.iloc[-1]
                        
                    # Calculate break duration
                    break_hours = 0.0
                    return_logs = group[group['Status'] == 'URGENT_RETURN']
                    for _, row in return_logs.iterrows():
                        break_hours += parse_duration_to_hours(row.get('Duration', ''))
                        
                    late_arrival = False
                    late_min = 0
                    raw_hours = 0.0
                    net_hours = 0.0
                    penalty = 0.0
                    wage = 0.0
                    status_text = "Incomplete Shift"
                    
                    if earliest_in_row is not None:
                        check_in_time = earliest_in_row['Time']
                        in_min = time_to_min(check_in_time)
                        start_min = time_to_min(office_start_str)
                        
                        if in_min > start_min:
                            late_arrival = True
                            late_min = in_min - start_min
                            penalty += penalty_rate
                            
                        if latest_out_row is not None:
                            ts_in = earliest_in_row['Timestamp']
                            ts_out = latest_out_row['Timestamp']
                            raw_hours = max(0.0, (ts_out - ts_in) / 3600.0)
                            net_hours = max(0.0, raw_hours - break_hours)
                            wage = max(0.0, net_hours * hourly_rate - penalty)
                            status_text = "Completed"
                        else:
                            status_text = "Checked In / Active"
                    else:
                        if latest_out_row is not None:
                            status_text = "Missing Check-In"
                            
                    records.append({
                        "Employee Name": name,
                        "Date": date_val.strftime('%Y-%m-%d'),
                        "Check-In": earliest_in_row['Time'] if earliest_in_row is not None else "N/A",
                        "Check-Out": latest_out_row['Time'] if latest_out_row is not None else "N/A",
                        "Status": status_text,
                        "Raw Hours": round(raw_hours, 2),
                        "Break Hours": round(break_hours, 2),
                        "Net Hours": round(net_hours, 2),
                        "Late?": "Yes" if late_arrival else "No",
                        "Late Mins": late_min,
                        "Penalty (Rs)": penalty,
                        "Estimated Wage (Rs)": round(wage, 2)
                    })
            
            if records:
                payroll_df = pd.DataFrame(records)
                
                # Overall Summary Metrics
                completed_df = payroll_df[payroll_df['Status'] == 'Completed']
                total_wages = completed_df['Estimated Wage (Rs)'].sum()
                total_net_hours = completed_df['Net Hours'].sum()
                total_penalties = payroll_df['Penalty (Rs)'].sum()
                total_lates = len(payroll_df[payroll_df['Late?'] == 'Yes'])
                
                # KPI Grid
                st.markdown(
                    f'''
                    <div class="kpis">
                      <div class="kpi-card">
                        <div class="label">Total Wages Paid</div>
                        <div class="value">Rs. {total_wages:,.2f}</div>
                        <div class="delta up">total payouts</div>
                      </div>
                      <div class="kpi-card">
                        <div class="label">Total Net Hours</div>
                        <div class="value">{total_net_hours:.2f} hrs</div>
                        <div class="delta up">work duration</div>
                      </div>
                      <div class="kpi-card">
                        <div class="label">Total Penalties</div>
                        <div class="value">Rs. {total_penalties:,.2f}</div>
                        <div class="delta down">arrival deductions</div>
                      </div>
                      <div class="kpi-card">
                        <div class="label">Late Arrivals</div>
                        <div class="value">{total_lates}</div>
                        <div class="delta down">lateness counts</div>
                      </div>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
                
                st.markdown("### 📋 Daily Payroll & Shift Logs")
                
                # Excel/CSV download for payroll report
                csv_payroll = payroll_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Payroll CSV Report",
                    data=csv_payroll,
                    file_name=f"Payroll_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
                
                # Renders custom table for payroll
                payroll_status_mapping = {
                    'COMPLETED': 'pill good',
                    'CHECKED IN / ACTIVE': 'pill warn',
                    'INCOMPLETE SHIFT': 'pill bad',
                    'MISSING CHECK-IN': 'pill bad'
                }
                
                payroll_table_html = render_custom_table(
                    payroll_df,
                    {
                        'Employee Name': 'Employee',
                        'Date': 'Date',
                        'Check-In': 'IN',
                        'Check-Out': 'OUT',
                        'Break Hours': 'Breaks',
                        'Net Hours': 'Net Hrs',
                        'Late?': 'Late',
                        'Penalty (Rs)': 'Penalty',
                        'Estimated Wage (Rs)': 'Wage',
                        'Status': 'Status'
                    },
                    pill_column='Status',
                    status_classes=payroll_status_mapping
                )
                
                st.markdown(
                    f'''
                    <div class="panel-container">
                      <h3>Daily Wages Breakdowns</h3>
                      {payroll_table_html}
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
            else:
                st.info("No logs found for payroll calculations in this range.")
        
    except Exception as e:
        st.error(f"Error parsing attendance files: {e}")
        st.info("The attendance file might be empty or locked. Try logging a check-in.")
