"""
app.py
======
DataSense AI – Intelligent Data Analyst
Main Streamlit application featuring automated data ingestion,
quality inspection, genuine Pandas calculations, interactive Plotly charts,
and Gemini-powered generative AI insights and chatbot.
"""

import os
from typing import Optional
import streamlit as st
import pandas as pd
import plotly.express as px

# Import custom modular engines
from data_engine import (
    load_dataset,
    get_dataset_overview,
    get_missing_values_report,
    get_duplicate_records,
    get_statistical_summary,
    generate_data_context_for_ai,
)
from ai_engine import (
    get_api_key,
    generate_executive_insights,
    answer_data_query,
)

# ---------------------------------------------------------
# Page Configuration & Styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="DataSense AI – Intelligent Data Analyst",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom modern CSS for professional SaaS look
st.markdown("""
<style>
    /* Metric Card Styling */
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px 22px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        margin-bottom: 12px;
    }
    .metric-title {
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 1.85rem;
        font-weight: 700;
        color: #0f172a;
    }
    .metric-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-top: 6px;
    }
    .badge-success { background-color: #dcfce7; color: #15803d; }
    .badge-warning { background-color: #fef9c3; color: #a16207; }
    .badge-danger  { background-color: #fee2e2; color: #b91c1c; }

    /* Clean typography */
    h1, h2, h3, h4 {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Subtle tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# State Initialization
# ---------------------------------------------------------
if "df" not in st.session_state:
    st.session_state.df = None
if "dataset_name" not in st.session_state:
    st.session_state.dataset_name = ""
if "file_source" not in st.session_state:
    st.session_state.file_source = None
if "header_row" not in st.session_state:
    st.session_state.header_row = 0
if "ai_insights" not in st.session_state:
    st.session_state.ai_insights = None
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []


# ---------------------------------------------------------
# Sidebar Navigation & Settings
# ---------------------------------------------------------
with st.sidebar:
    st.title("📊 DataSense AI")
    st.caption("Intelligent Data Analyst & Visualization Assistant")
    st.markdown("---")

    # API Key Configuration
    st.subheader("🔑 Gemini API Settings")
    env_key = get_api_key()
    user_key = st.text_input(
        "API Key (Optional if set in .env)",
        type="password",
        value=env_key if env_key else "",
        placeholder="AIzaSy...",
        help="Get your free Gemini API key from https://aistudio.google.com/app/apikey"
    )
    active_api_key = get_api_key(user_key)
    
    if active_api_key:
        st.success("API Key is ready!", icon="✅")
    else:
        st.warning("No Gemini API key detected. Add to .env or paste above for AI features.", icon="⚠️")

    st.markdown("---")

    # File Ingestion
    st.subheader("📁 Upload Dataset")
    uploaded_file = st.file_uploader(
        "Upload a CSV or Excel file",
        type=["csv", "xlsx", "xls"],
        help="Upload files up to 200MB. Processed securely in memory."
    )

    col_upload_1, col_upload_2 = st.columns(2)
    with col_upload_1:
        load_demo_btn = st.button("🚀 Load Demo CSV", use_container_width=True)
    with col_upload_2:
        reset_btn = st.button("🔄 Reset", use_container_width=True)

    if reset_btn:
        st.session_state.df = None
        st.session_state.dataset_name = ""
        st.session_state.file_source = None
        st.session_state.header_row = 0
        st.session_state.ai_insights = None
        st.session_state.chat_messages = []
        st.rerun()

    # Load Demo Dataset action
    if load_demo_btn:
        demo_path = os.path.join(os.path.dirname(__file__), "sample_sales_data.csv")
        if os.path.exists(demo_path):
            df_loaded, err = load_dataset(demo_path)
            if df_loaded is not None:
                st.session_state.df = df_loaded
                st.session_state.dataset_name = "sample_sales_data.csv (Demo)"
                st.session_state.file_source = demo_path
                st.session_state.header_row = df_loaded.attrs.get("header_row", 0)
                st.session_state.ai_insights = None
                st.session_state.chat_messages = []
                st.success("Loaded demo sales dataset!")
                st.rerun()
            else:
                st.error(err)
        else:
            st.error("Demo dataset file not found on disk.")

    # Process Uploaded File
    if uploaded_file is not None:
        if st.session_state.dataset_name != uploaded_file.name:
            df_loaded, err = load_dataset(uploaded_file)
            if df_loaded is not None:
                st.session_state.df = df_loaded
                st.session_state.dataset_name = uploaded_file.name
                st.session_state.file_source = uploaded_file
                st.session_state.header_row = df_loaded.attrs.get("header_row", 0)
                st.session_state.ai_insights = None
                st.session_state.chat_messages = []
                st.rerun()
            else:
                st.error(err)

    # Header Row Calibration in Sidebar (Active when data is loaded)
    if st.session_state.df is not None:
        st.markdown("---")
        st.subheader("📑 Header Calibration")
        current_h = int(st.session_state.get("header_row", 0))
        detected_h = int(st.session_state.df.attrs.get("header_row", 0))

        header_options = [0, 1, 2, 3, 4]
        selected_header = st.selectbox(
            "Header Row in File:",
            options=header_options,
            index=current_h if current_h in header_options else 0,
            format_func=lambda x: f"Row {x + 1} {'(Detected)' if x == detected_h else ''}".strip(),
            help="Select which row contains the column names (e.g. if Row 1 is a title banner or blank)."
        )

        if selected_header != current_h and st.session_state.get("file_source") is not None:
            df_reloaded, err = load_dataset(st.session_state.file_source, header_row=selected_header)
            if df_reloaded is not None:
                st.session_state.df = df_reloaded
                st.session_state.header_row = selected_header
                st.session_state.ai_insights = None
                st.session_state.chat_messages = []
                st.rerun()
            elif err:
                st.error(err)

    st.markdown("---")
    st.caption("DataSense AI • College Final Year / Mini Project\nBuilt with Streamlit, Pandas, Plotly & Gemini API.")


# ---------------------------------------------------------
# Main Application Content
# ---------------------------------------------------------
df = st.session_state.df

if df is None:
    # Landing / Welcome Page
    st.markdown("""
    # Welcome to **DataSense AI** 
    ### Your Intelligent, Automated Data Analyst 🚀

    DataSense AI bridges the gap between raw datasets and actionable intelligence using genuine Pandas analytics and Google Gemini Generative AI.

    ---
    ### 🌟 Core Capabilities
    1. **Effortless Ingestion**: Upload any `.csv`, `.xlsx`, or `.xls` spreadsheet with one click.
    2. **Automated Quality Checks**: Instantly identify missing cells, duplicate rows, and data types.
    3. **Verified Statistics**: True Pandas calculations (mean, standard deviation, quartiles, counts) with zero fabrication.
    4. **Interactive Plotly Visuals**: Generate dynamic Bar, Line, Pie, Scatter, Histogram, and Box plots with instant filters.
    5. **Executive AI Insights**: Automated professional executive summary powered by Gemini 2.5.
    6. **Natural Language Data Chat**: Ask questions about your dataset in plain English.
    """)

    st.info("👈 **To get started, upload your dataset in the sidebar, or click 'Load Demo Data' for a test run.**")

    # Quick demo buttons right on the main page for convenience
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        if st.button("📊 Try with Sample Sales CSV", use_container_width=True, type="primary"):
            demo_path = os.path.join(os.path.dirname(__file__), "sample_sales_data.csv")
            if os.path.exists(demo_path):
                df_loaded, err = load_dataset(demo_path)
                if df_loaded is not None:
                    st.session_state.df = df_loaded
                    st.session_state.dataset_name = "sample_sales_data.csv (Demo)"
                    st.session_state.file_source = demo_path
                    st.session_state.header_row = df_loaded.attrs.get("header_row", 0)
                    st.session_state.ai_insights = None
                    st.session_state.chat_messages = []
                    st.rerun()

    with col_d2:
        if st.button("📑 Try with Excel (Title Banner in Row 1)", use_container_width=True):
            excel_demo_path = os.path.join(os.path.dirname(__file__), "sample_excel_with_title.xlsx")
            if os.path.exists(excel_demo_path):
                df_loaded, err = load_dataset(excel_demo_path)
                if df_loaded is not None:
                    st.session_state.df = df_loaded
                    st.session_state.dataset_name = "sample_excel_with_title.xlsx (Demo)"
                    st.session_state.file_source = excel_demo_path
                    st.session_state.header_row = df_loaded.attrs.get("header_row", 0)
                    st.session_state.ai_insights = None
                    st.session_state.chat_messages = []
                    st.rerun()

    st.stop()


# ---------------------------------------------------------
# Active Dataset Analysis Header
# ---------------------------------------------------------
overview = get_dataset_overview(df)

col_title, col_status = st.columns([3, 1])
with col_title:
    st.title("📊 DataSense AI Dashboard")
    st.caption(f"Active Dataset: **{st.session_state.dataset_name}** • {overview['memory']} Memory Footprint")
with col_status:
    st.write("")
    st.markdown(
        f"<div style='text-align: right;'><span class='metric-badge badge-success'>● System Active</span></div>",
        unsafe_allow_html=True
    )

# ---------------------------------------------------------
# Key Performance / Metric Cards (Computed by Pandas)
# ---------------------------------------------------------
m_col1, m_col2, m_col3, m_col4 = st.columns(4)

with m_col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Total Records (Rows)</div>
        <div class="metric-value">{overview['rows']:,}</div>
        <span class="metric-badge badge-success">Rows Ingested</span>
    </div>
    """, unsafe_allow_html=True)

with m_col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Features (Columns)</div>
        <div class="metric-value">{overview['cols']:,}</div>
        <span class="metric-badge badge-success">{len(overview['numeric_cols'])} Numeric • {len(overview['categorical_cols'])} Categorical</span>
    </div>
    """, unsafe_allow_html=True)

with m_col3:
    missing_count = overview['missing_cells']
    total_cells = max(overview['rows'] * overview['cols'], 1)
    missing_pct = (missing_count / total_cells) * 100
    badge_cls = "badge-success" if missing_count == 0 else "badge-warning"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Missing Values</div>
        <div class="metric-value">{missing_count:,}</div>
        <span class="metric-badge {badge_cls}">{missing_pct:.2f}% of all cells</span>
    </div>
    """, unsafe_allow_html=True)

with m_col4:
    dup_count = overview['duplicate_rows']
    dup_badge_cls = "badge-success" if dup_count == 0 else "badge-danger"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Duplicate Rows</div>
        <div class="metric-value">{dup_count:,}</div>
        <span class="metric-badge {dup_badge_cls}">{'No Duplicates' if dup_count == 0 else f'{dup_count} Duplicate Found'}</span>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# ---------------------------------------------------------
# Main Tabs Layout
# ---------------------------------------------------------
tab_overview, tab_stats, tab_charts, tab_insights, tab_chat = st.tabs([
    "📋 Overview & Quality",
    "📈 Statistical Analysis",
    "📊 Interactive Charts",
    "🧠 AI Insights",
    "💬 AI Data Chat",
])


# ---------------------------------------------------------
# TAB 1: OVERVIEW & DATA QUALITY
# ---------------------------------------------------------
with tab_overview:
    # Misplaced Header Warning & Inline Calibration
    if overview.get("has_unnamed", False):
        st.warning(
            f"⚠️ **Misplaced Header Warning**: We detected Unnamed column headers (`{', '.join(overview['unnamed_cols'][:3])}`). "
            "This usually happens when an Excel file has report titles or blank rows above the actual table headers. "
            "Select the correct header row below to calibrate your dataset."
        )
        col_cal1, col_cal2 = st.columns([2, 1])
        with col_cal1:
            cal_pick = st.selectbox(
                "Choose True Header Row:",
                options=[0, 1, 2, 3, 4],
                index=int(st.session_state.get("header_row", 0)),
                format_func=lambda x: f"Row {x + 1} (Row #{x + 1})",
                key="tab_header_cal_picker"
            )
        with col_cal2:
            st.write("")
            if st.button("Apply Header Calibration", key="apply_header_tab_btn", use_container_width=True):
                if st.session_state.get("file_source") is not None:
                    df_reloaded, err = load_dataset(st.session_state.file_source, header_row=cal_pick)
                    if df_reloaded is not None:
                        st.session_state.df = df_reloaded
                        st.session_state.header_row = cal_pick
                        st.session_state.ai_insights = None
                        st.session_state.chat_messages = []
                        st.rerun()
    elif overview.get("header_row", 0) > 0:
        st.info(
            f"ℹ️ **Header Calibrated**: Column headers successfully loaded from **Row {overview['header_row'] + 1}**. "
            f"Accurately identified {len(overview['numeric_cols'])} numeric and {len(overview['categorical_cols'])} categorical features."
        )

    st.subheader("🔍 Dataset Preview & Structure")
    
    col_ctrl1, col_ctrl2 = st.columns([1, 3])
    with col_ctrl1:
        preview_rows = st.slider("Rows to Preview", min_value=5, max_value=min(100, len(df)), value=min(10, len(df)), step=5)
    with col_ctrl2:
        col_filter = st.multiselect("Filter Columns to View (Optional)", options=df.columns.tolist(), default=df.columns.tolist()[:10])

    display_cols = col_filter if col_filter else df.columns.tolist()
    st.dataframe(df[display_cols].head(preview_rows), use_container_width=True)

    st.markdown("---")
    st.subheader("🛡️ Data Quality & Integrity Inspection")

    q_col1, q_col2 = st.columns(2)

    with q_col1:
        st.markdown("#### 1. Missing Values Report")
        missing_df = get_missing_values_report(df)
        if missing_df["Missing Count"].sum() > 0:
            st.dataframe(
                missing_df[missing_df["Missing Count"] > 0],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("🎉 Perfect! Zero missing values detected across all columns.")

    with q_col2:
        st.markdown("#### 2. Duplicate Records Inspection")
        duplicates_df = get_duplicate_records(df)
        if not duplicates_df.empty:
            st.warning(f"⚠️ Found {len(duplicates_df)} duplicate rows (including originals):")
            st.dataframe(duplicates_df, use_container_width=True)
        else:
            st.success("🎉 Excellent! All rows in this dataset are unique.")


# ---------------------------------------------------------
# TAB 2: STATISTICAL ANALYSIS
# ---------------------------------------------------------
with tab_stats:
    st.subheader("📐 Descriptive Statistics (Pandas Calculations)")
    
    stats_df = get_statistical_summary(df)
    if stats_df is not None:
        st.dataframe(stats_df, use_container_width=True)
        
        st.markdown("---")
        st.subheader("🎯 Single Feature Deep Dive")
        
        selected_num_col = st.selectbox("Select Numeric Column to Inspect:", options=overview["numeric_cols"])
        if selected_num_col:
            col_series = df[selected_num_col].dropna()
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Mean", f"{col_series.mean():.2f}")
            c2.metric("Median (50%)", f"{col_series.median():.2f}")
            c3.metric("Min", f"{col_series.min():.2f}")
            c4.metric("Max", f"{col_series.max():.2f}")

            # Plot mini distribution
            fig_hist = px.histogram(
                df,
                x=selected_num_col,
                nbins=25,
                title=f"Distribution of '{selected_num_col}'",
                template="plotly_white",
                color_discrete_sequence=["#3b82f6"]
            )
            st.plotly_chart(fig_hist, use_container_width=True)
    else:
        st.info("No numeric columns found in this dataset for descriptive statistics.")

    # Categorical Columns Overview
    if overview["categorical_cols"]:
        st.markdown("---")
        st.subheader("🏷️ Categorical Features Unique Values")
        cat_col = st.selectbox("Select Categorical Column:", options=overview["categorical_cols"])
        if cat_col:
            top_vals = df[cat_col].value_counts().head(10).reset_index()
            top_vals.columns = [cat_col, "Count"]
            st.dataframe(top_vals, use_container_width=True, hide_index=True)


# ---------------------------------------------------------
# TAB 3: INTERACTIVE CHARTS (PLOTLY)
# ---------------------------------------------------------
with tab_charts:
    st.subheader("📊 Interactive Data Visualizer")
    st.caption("Generate publication-ready, interactive charts with customizable dimensions.")

    chart_col_cfg, chart_col_render = st.columns([1, 2.5])

    with chart_col_cfg:
        st.markdown("#### ⚙️ Chart Configuration")
        chart_type = st.selectbox(
            "Select Chart Type",
            ["Bar Chart", "Line Chart", "Pie Chart", "Scatter Plot", "Histogram", "Box Plot"]
        )

        all_cols = df.columns.tolist()
        num_cols = overview["numeric_cols"]
        cat_cols = overview["categorical_cols"]

        x_col = None
        y_col = None
        color_col = None

        if chart_type in ["Bar Chart", "Line Chart"]:
            x_col = st.selectbox("X-Axis (Category or Date)", options=all_cols)
            y_col = st.selectbox("Y-Axis (Numeric Value)", options=num_cols if num_cols else all_cols)
            color_col = st.selectbox("Color / Group By (Optional)", options=["None"] + cat_cols)
        
        elif chart_type == "Pie Chart":
            x_col = st.selectbox("Category Column", options=cat_cols if cat_cols else all_cols)
            y_col = st.selectbox("Values Column (Numeric)", options=num_cols if num_cols else all_cols)
            color_col = None

        elif chart_type == "Scatter Plot":
            x_col = st.selectbox("X-Axis (Numeric)", options=num_cols if num_cols else all_cols)
            y_col = st.selectbox("Y-Axis (Numeric)", options=[c for c in num_cols if c != x_col] if len(num_cols) > 1 else all_cols)
            color_col = st.selectbox("Color Dimension (Optional)", options=["None"] + cat_cols)

        elif chart_type == "Histogram":
            x_col = st.selectbox("Numeric Column", options=num_cols if num_cols else all_cols)
            color_col = st.selectbox("Group By (Optional)", options=["None"] + cat_cols)

        elif chart_type == "Box Plot":
            y_col = st.selectbox("Metric Column (Numeric)", options=num_cols if num_cols else all_cols)
            x_col = st.selectbox("Group By Category (Optional)", options=["None"] + cat_cols)

        chart_title = st.text_input("Chart Title", value=f"{chart_type} of {x_col if x_col else ''} {f'vs {y_col}' if y_col else ''}".strip())

    with chart_col_render:
        try:
            fig = None
            color_arg = None if color_col in [None, "None"] else color_col

            if chart_type == "Bar Chart" and x_col and y_col:
                # Group data cleanly to avoid overplotting if dataset is large
                grouped_df = df.groupby(x_col, as_index=False)[y_col].sum()
                fig = px.bar(
                    grouped_df,
                    x=x_col,
                    y=y_col,
                    title=chart_title,
                    template="plotly_white",
                    color_discrete_sequence=px.colors.qualitative.Prism
                )

            elif chart_type == "Line Chart" and x_col and y_col:
                fig = px.line(
                    df,
                    x=x_col,
                    y=y_col,
                    color=color_arg,
                    title=chart_title,
                    template="plotly_white"
                )

            elif chart_type == "Pie Chart" and x_col and y_col:
                pie_grouped = df.groupby(x_col, as_index=False)[y_col].sum()
                fig = px.pie(
                    pie_grouped,
                    names=x_col,
                    values=y_col,
                    title=chart_title,
                    hole=0.35,  # Modern Donut style
                    template="plotly_white"
                )

            elif chart_type == "Scatter Plot" and x_col and y_col:
                fig = px.scatter(
                    df,
                    x=x_col,
                    y=y_col,
                    color=color_arg,
                    title=chart_title,
                    template="plotly_white"
                )

            elif chart_type == "Histogram" and x_col:
                fig = px.histogram(
                    df,
                    x=x_col,
                    color=color_arg,
                    title=chart_title,
                    template="plotly_white"
                )

            elif chart_type == "Box Plot" and y_col:
                x_arg = None if x_col in [None, "None"] else x_col
                fig = px.box(
                    df,
                    x=x_arg,
                    y=y_col,
                    title=chart_title,
                    template="plotly_white"
                )

            if fig:
                fig.update_layout(
                    margin=dict(l=20, r=20, t=50, b=20),
                    font=dict(family="sans-serif", size=13),
                    hovermode="closest"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Please choose valid column selections to render the chart.")

        except Exception as chart_err:
            st.error(f"Error rendering chart: {str(chart_err)}")


# ---------------------------------------------------------
# TAB 4: AI DATA INSIGHTS (GEMINI API)
# ---------------------------------------------------------
with tab_insights:
    st.subheader("🧠 Automated AI Data Insights")
    st.caption("DataSense AI summarizes high-level patterns, detects statistical trends, and formulates business recommendations based on real Pandas calculations.")

    if not active_api_key:
        st.info("⚠️ Gemini API key not found. Please provide an API key in the sidebar or in your `.env` file to enable AI insights.")
    else:
        col_btn, col_info = st.columns([1, 3])
        with col_btn:
            generate_btn = st.button("✨ Generate AI Insights", type="primary", use_container_width=True)

        if generate_btn:
            with st.spinner("Analyzing dataset metrics and formulating executive summary..."):
                data_context = generate_data_context_for_ai(df)
                insights_text, err = generate_executive_insights(data_context, active_api_key)
                if err:
                    st.error(err)
                else:
                    st.session_state.ai_insights = insights_text

        # Display cached or newly generated insights
        if st.session_state.ai_insights:
            st.markdown("---")
            st.markdown(st.session_state.ai_insights)
            st.download_button(
                label="📥 Download Insights Report (.md)",
                data=st.session_state.ai_insights,
                file_name="datasense_ai_insights.md",
                mime="text/markdown",
            )
        else:
            st.info("Click 'Generate AI Insights' above to produce a complete executive summary.")


# ---------------------------------------------------------
# TAB 5: AI DATA CHAT
# ---------------------------------------------------------
with tab_chat:
    st.subheader("💬 AI Data Analyst Chat")
    st.caption("Ask questions about your dataset. Answers are grounded in actual Pandas calculations and factual statistics.")

    if not active_api_key:
        st.info("⚠️ Gemini API key not found. Please provide an API key in the sidebar or `.env` file to chat with your data.")
    else:
        # Prompt suggestions
        st.markdown("**💡 Quick Question Ideas:**")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            q1 = st.button("What are the key statistics?", use_container_width=True)
        with col_s2:
            q2 = st.button("Are there any data quality issues?", use_container_width=True)
        with col_s3:
            q3 = st.button("What patterns exist in this data?", use_container_width=True)

        # Handle quick suggestion click
        suggested_prompt = None
        if q1:
            suggested_prompt = "What are the key statistics and distribution of the numeric columns?"
        elif q2:
            suggested_prompt = "Can you detail any data quality issues, missing values, or duplicate records found in this dataset?"
        elif q3:
            suggested_prompt = "What notable patterns or business trends do you observe from these metrics?"

        # Display message history
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Input handler
        user_input = st.chat_input("Ask a question about your dataset...")
        prompt_to_send = user_input or suggested_prompt

        if prompt_to_send:
            # 1. Add user message
            st.session_state.chat_messages.append({"role": "user", "content": prompt_to_send})
            with st.chat_message("user"):
                st.markdown(prompt_to_send)

            # 2. Get AI response
            with st.chat_message("assistant"):
                with st.spinner("Analyzing data and generating answer..."):
                    data_context = generate_data_context_for_ai(df)
                    reply, err = answer_data_query(
                        user_query=prompt_to_send,
                        chat_history=st.session_state.chat_messages,
                        data_context=data_context,
                        api_key=active_api_key
                    )
                    if err:
                        st.error(err)
                        st.session_state.chat_messages.append({"role": "assistant", "content": f"⚠️ Error: {err}"})
                    else:
                        st.markdown(reply)
                        st.session_state.chat_messages.append({"role": "assistant", "content": reply})
