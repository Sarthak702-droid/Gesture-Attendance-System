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

# Dark Mode / Custom Aesthetics Styling
st.markdown(
    """
    <style>
    .metric-card {
        background-color: #1E293B;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #06B6D4;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        margin-bottom: 20px;
    }
    .metric-title {
        font-size: 14px;
        color: #94A3B8;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 5px;
    }
    .metric-value {
        font-size: 28px;
        color: #F8FAFC;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True
)

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

st.title("📊 Gesture Controlled Attendance Dashboard")
st.markdown("Real-time check-in logs and visual analytics (reloads automatically every 5s)")

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
        
        # Metrics Calculations
        total_logs = len(filtered_df)
        present_count = len(filtered_df[filtered_df['Status'] == 'PRESENT'])
        absent_count = len(filtered_df[filtered_df['Status'] == 'ABSENT'])
        
        # 1. Metric Row Display
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(
                f'<div class="metric-card" style="border-left-color: #06B6D4;">'
                f'<div class="metric-title">Total Logs</div>'
                f'<div class="metric-value">{total_logs}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            
        with col2:
            st.markdown(
                f'<div class="metric-card" style="border-left-color: #10B981;">'
                f'<div class="metric-title">Present Count</div>'
                f'<div class="metric-value">{present_count}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            
        with col3:
            st.markdown(
                f'<div class="metric-card" style="border-left-color: #EF4444;">'
                f'<div class="metric-title">Absent Count</div>'
                f'<div class="metric-value">{absent_count}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            
        # 2. Charts and Data Visualizations
        st.markdown("### 📈 Visual Analysis")
        chart_col1, chart_col2 = st.columns([2, 1])
        
        with chart_col1:
            # Bar chart of attendance by date
            daily_stats = filtered_df.groupby([filtered_df['Date'].dt.date, 'Status']).size().unstack(fill_value=0)
            if not daily_stats.empty:
                st.markdown("**Daily Attendance Trends**")
                st.bar_chart(daily_stats)
            else:
                st.write("No trend data available for this range.")
                
        with chart_col2:
            # Present vs Absent ratio
            st.markdown("**Status Breakdown**")
            if total_logs > 0:
                pie_data = pd.DataFrame({
                    "Count": [present_count, absent_count],
                    "Status": ["Present", "Absent"]
                }).set_index("Status")
                st.bar_chart(pie_data)
            else:
                st.write("No breakdown data.")

        # 3. Main Data Table
        st.markdown("---")
        st.markdown("### 📋 Attendance Records")
        
        # Download Excel button
        if os.path.exists(XLSX_PATH):
            with open(XLSX_PATH, "rb") as file:
                btn = st.download_button(
                    label="📥 Download Formatted Excel (.xlsx)",
                    data=file,
                    file_name=f"Attendance_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            # Fallback to CSV download if Excel not synced yet
            csv_data = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV Report",
                data=csv_data,
                file_name="Attendance_Report.csv",
                mime="text/csv"
            )
            
        # Display table sorted recently
        st.dataframe(
            display_df[['Name', 'Status', 'Date', 'Time']].sort_values(by=['Date', 'Time'], ascending=[False, False]),
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"Error parsing attendance files: {e}")
        st.info("The attendance file might be empty or locked. Try logging a check-in.")
