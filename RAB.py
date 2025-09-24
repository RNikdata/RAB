import streamlit as st
import pandas as pd
import numpy as np
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from google.oauth2.service_account import Credentials
import time
import hashlib

st.set_page_config(layout="wide")

# --- Connect to Google Sheets ---
service_account_info = st.secrets["google_service_account"]
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
gc = gspread.authorize(credentials)

# --- Google Sheet ID & Sheet Names ---
SHEET_ID = "1yagvN3JhJtml0CMX4Lch7_LdPeUzvPcl1VEfyy8RvC4"
EMPLOYEE_SHEET_NAME = "Employee Data"
ADS_SHEET_NAME = "Employee ADS"

employee_sheet = gc.open_by_key(SHEET_ID).worksheet(EMPLOYEE_SHEET_NAME)
ads_sheet = gc.open_by_key(SHEET_ID).worksheet(ADS_SHEET_NAME)

# --- Load Data ---
df = get_as_dataframe(employee_sheet, evaluate_formulas=True).dropna(how="all")
ads_df = get_as_dataframe(ads_sheet, evaluate_formulas=True).dropna(how="all")
if ads_df.empty:
    ads_df = pd.DataFrame(columns=["Employee Id", "Interested Manager", "Employee to Swap", "Request Id","Status"])

# --- Merge DataFrames ---
merged_df = df.merge(
    ads_df[["Employee Id", "Interested Manager", "Employee to Swap", "Request Id","Status"]] if not ads_df.empty else pd.DataFrame(),
    on="Employee Id",
    how="left"
)

# --- Sidebar ---
st.sidebar.markdown(
    """
    <div style='text-align: left; margin-left: 43px;'>
        <img src="https://upload.wikimedia.org/wikipedia/en/0/0c/Mu_Sigma_Logo.jpg" width="100">
    </div>
    """, unsafe_allow_html=True
)
st.sidebar.header("⚙️ Filters")
account_filter = st.sidebar.multiselect("Account Name", options=merged_df["Account Name"].dropna().unique())
manager_filter = st.sidebar.multiselect("Manager Name", options=merged_df["Manager Name"].dropna().unique())
st.sidebar.header("🔎 Search")
resource_search = st.sidebar.text_input("Search Employee Name or ID", placeholder = "Employee ID/Name")

# --- Main Heading ---
col_title, col_refresh = st.columns([9, 1])
with col_title:
    st.markdown("<h1 style='text-align:center'>🧑‍💼 Resource Transfer Board</h1>", unsafe_allow_html=True)
with col_refresh:
    if st.button("🔄 Refresh"):
        st.rerun()

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["📝 Supply Pool", "🔄 Transfer Requests", "✏️ Employee Transfer Form"])

# --- TAB 1: Supply Pool with clickable buttons ---
with tab1:
    st.subheader("📝 Supply Pool")
    filtered_df = merged_df.copy()

    # Filters
    if account_filter:
        filtered_df = filtered_df[filtered_df["Account Name"].isin(account_filter)]
    if manager_filter:
        filtered_df = filtered_df[
            (filtered_df["Manager Name"].isin(manager_filter)) |
            (filtered_df["Interested Manager"].isin(manager_filter))
        ]
    if resource_search:
        filtered_df = filtered_df[
            filtered_df["Employee Name"].str.contains(resource_search, case=False, na=False) |
            filtered_df["Employee Id"].astype(str).str.contains(resource_search, na=False)
        ]

    filtered_df_unique = filtered_df.drop_duplicates(subset=["Employee Id"], keep="first")

    st.markdown("### Employees (Click 'Select' to Transfer)")
    for idx, row in filtered_df_unique.iterrows():
        col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 2, 1])
        with col1:
            st.write(row["Employee Id"])
        with col2:
            st.write(row["Employee Name"])
        with col3:
            st.write(row["Account Name"])
        with col4:
            st.write(row["Manager Name"])
        with col5:
            btn_key = f"select_{row['Employee Id']}"
            if st.button("Select", key=btn_key):
                # Store selected employee in session_state
                st.session_state["preselect_interested_employee"] = f"{row['Employee Id']} - {row['Employee Name']}"
                st.session_state["switch_to_tab3"] = True
                st.experimental_rerun()

# --- TAB 2: Transfer Requests ---
with tab2:
    st.subheader("🔄 Transfer Requests")
    swap_df = ads_df.copy()
    swap_df["Status"] = swap_df.get("Status", "Pending").fillna("Pending")

    col1, col2 = st.columns([2, 2])
    with col1:
        interested_manager_search = st.text_input("Search by Interested Manager", key="interested_manager_search_box")
    with col2:
        status_filter = st.selectbox("Filter by Status", options=["All", "Pending", "Approved", "Rejected"], key="status_filter_box")

    # Apply filters
    if interested_manager_search and "Interested Manager" in swap_df.columns:
        swap_df = swap_df[swap_df["Interested Manager"].str.contains(interested_manager_search, case=False, na=False)]
    if status_filter != "All":
        swap_df = swap_df[swap_df["Status"] == status_filter]

    st.markdown("---")

    pending_swap_df_filtered = swap_df[swap_df["Status"]=="Pending"]
    col1, col2 = st.columns([2,2])
    with col1:
        request_id_options = pending_swap_df_filtered["Request Id"].dropna().unique().astype(int).tolist() if not pending_swap_df_filtered.empty else []
        request_id_select = st.selectbox("Select Request ID", options=request_id_options, key="request_id_select_tab2")
    with col2:
        decision = st.radio("Action", options=["Approve", "Reject"], horizontal=True, key="decision_radio")

    msg_placeholder = st.empty()
    if st.button("Submit", key="submit_decision"):
        if request_id_select not in pending_swap_df_filtered["Request Id"].values:
            msg_placeholder.warning("⚠️ Please select a valid pending Request ID.")
        else:
            current_status = ads_df.loc[ads_df["Request Id"]==request_id_select, "Status"].values[0]
            if current_status=="Approved" and decision=="Reject":
                msg_placeholder.error(f"❌ Request ID {request_id_select} is already Approved and cannot be Rejected.")
            else:
                try:
                    status_value = "Approved" if decision=="Approve" else "Rejected"
                    ads_df.loc[ads_df["Request Id"]==request_id_select,"Status"]=status_value
                    set_with_dataframe(ads_sheet, ads_df, include_index=False, resize=True)
                    msg_placeholder.success(f"✅ Request ID {request_id_select} marked as {status_value}")
                    time.sleep(1)
                    st.experimental_rerun()
                except Exception as e:
                    msg_placeholder.error(f"❌ Error updating request: {e}")

    # Colored status table
    def color_status(val):
        if val=="Approved": return "color: green; font-weight: bold;"
        elif val=="Rejected": return "color: red; font-weight: bold;"
        else: return "color: orange; font-weight: bold;"

    swap_columns = ["Request Id", "Employee Id", "Employee Name", "Email", "Interested Manager", "Employee to Swap", "Status"]
    swap_columns = [c for c in swap_columns if c in swap_df.columns]
    swap_df_filtered = swap_df[swap_df["Request Id"].notna()] if "Request Id" in swap_df.columns else pd.DataFrame()
    if not swap_df_filtered.empty:
        swap_df_filtered["Request Id"]=swap_df_filtered["Request Id"].astype(int)
        styled_swap_df = swap_df_filtered[swap_columns].style.applymap(color_status, subset=["Status"])
        st.dataframe(styled_swap_df, use_container_width=True, hide_index=True)

# --- TAB 3: Employee Transfer Form ---
with tab3:
    st.subheader("🔄 Employee Transfer Request")
    options_interested = ["Select Interested Employee"] + (df["Employee Id"].astype(str) + " - " + df["Employee Name"]).tolist()

    preselected = st.session_state.get("preselect_interested_employee", None)
    default_idx = options_interested.index(preselected) if preselected in options_interested else 0
    interested_employee_add = st.selectbox("Interested Employee", options=options_interested, index=default_idx, key="interested_employee_add")

    # Clear session state after prefill
    if "preselect_interested_employee" in st.session_state:
        del st.session_state["preselect_interested_employee"]
