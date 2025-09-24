import streamlit as st
import pandas as pd
import numpy as np
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from google.oauth2.service_account import Credentials
import time
import hashlib

st.set_page_config(layout="wide")

# --- Initialize session state for pre-selecting interested employee ---
if "preselect_interested_employee" not in st.session_state:
    st.session_state.preselect_interested_employee = None

# --- Connect to Google Sheets ---
service_account_info = st.secrets["google_service_account"]
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
gc = gspread.authorize(credentials)

SHEET_ID = "1yagvN3JhJtml0CMX4Lch7_LdPeUzvPcl1VEfyy8RvC4"
EMPLOYEE_SHEET_NAME = "Employee Data"
ADS_SHEET_NAME = "Employee ADS"

employee_sheet = gc.open_by_key(SHEET_ID).worksheet(EMPLOYEE_SHEET_NAME)
ads_sheet = gc.open_by_key(SHEET_ID).worksheet(ADS_SHEET_NAME)

# --- Load Data ---
df = get_as_dataframe(employee_sheet, evaluate_formulas=True).dropna(how="all")
ads_df = get_as_dataframe(ads_sheet, evaluate_formulas=True).dropna(how="all")
if ads_df.empty:
    ads_df = pd.DataFrame(columns=["Employee Id", "Interested Manager", "Employee to Swap", "Request Id", "Status"])

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
resource_search = st.sidebar.text_input("Search Employee Name or ID", placeholder="Employee ID/Name")

# --- Main Heading + Refresh ---
col_title, col_refresh = st.columns([9, 1])
with col_title:
    st.markdown("<h1 style='text-align:center'>🧑‍💼 Resource Transfer Board</h1>", unsafe_allow_html=True)
with col_refresh:
    if st.button("🔄 Refresh"):
        st.experimental_rerun()

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["📝 Supply Pool", "🔄 Transfer Requests", "✏️ Employee Transfer Form"])

# --- Tab 1: Supply Pool ---
with tab1:
    st.subheader("📝 Supply Pool")
    filtered_df = merged_df.copy()
    # Apply filters
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

    # Add clickable "Select" buttons for each employee
    st.write("Click on Employee Name to prefill Interested Employee in Transfer Form:")
    for i, row in filtered_df_unique.iterrows():
        emp_display = f"{row['Employee Name']} ({row['Employee Id']})"
        if st.button(emp_display, key=f"select_{row['Employee Id']}"):
            st.session_state.preselect_interested_employee = f"{row['Employee Id']} - {row['Employee Name']}"
            st.experimental_rerun()

    columns_to_show = ["Manager Name","Account Name","Employee Id", "Employee Name", "Designation"]
    columns_to_show = [col for col in columns_to_show if col in filtered_df_unique.columns]
    st.dataframe(filtered_df_unique[columns_to_show], use_container_width=True, height=500, hide_index=True)

# --- Tab 2: Transfer Requests ---
with tab2:
    st.subheader("🔄 Transfer Requests")
    swap_df = ads_df.copy()
    if "Status" not in swap_df.columns:
        swap_df["Status"] = "Pending"
    else:
        swap_df["Status"] = swap_df["Status"].fillna("Pending")

    col1, col2 = st.columns([2,2])
    with col1:
        interested_manager_search = st.text_input("Search by Interested Manager", key="search_mgr_tab2")
    with col2:
        status_filter = st.selectbox("Filter by Status", ["All","Pending","Approved","Rejected"], key="status_tab2")

    if interested_manager_search:
        swap_df = swap_df[swap_df["Interested Manager"].str.contains(interested_manager_search, case=False, na=False)]
    if status_filter != "All":
        swap_df = swap_df[swap_df["Status"]==status_filter]

    st.markdown("---")

    # Approve/Reject Section
    pending_swap_df = swap_df[swap_df["Status"]=="Pending"]
    col1, col2 = st.columns([2,2])
    with col1:
        request_id_options = pending_swap_df["Request Id"].dropna().unique().astype(int).tolist() if not pending_swap_df.empty else []
        request_id_select = st.selectbox("Select Request ID", options=request_id_options, key="request_id_select_tab2")
    with col2:
        decision = st.radio("Action", ["Approve","Reject"], horizontal=True, key="decision_radio")

    msg_placeholder = st.empty()
    if st.button("Submit", key="submit_decision"):
        if request_id_select not in pending_swap_df["Request Id"].values:
            msg_placeholder.warning("⚠️ Please select a valid pending Request ID.")
        else:
            current_status = ads_df.loc[ads_df["Request Id"]==request_id_select, "Status"].values[0]
            if current_status=="Approved" and decision=="Reject":
                msg_placeholder.error(f"❌ Request ID {request_id_select} is already Approved and cannot be Rejected.")
            else:
                try:
                    status_value = "Approved" if decision=="Approve" else "Rejected"
                    ads_df.loc[ads_df["Request Id"]==request_id_select, "Status"] = status_value
                    set_with_dataframe(ads_sheet, ads_df, include_index=False, resize=True)
                    msg_placeholder.success(f"✅ Request ID {request_id_select} marked as {status_value}")
                    time.sleep(1)
                    st.experimental_rerun()
                except Exception as e:
                    msg_placeholder.error(f"❌ Error updating request: {e}")

    # Colored status table
    def color_status(val):
        if val=="Approved":
            return "color: green; font-weight: bold;"
        elif val=="Rejected":
            return "color: red; font-weight: bold;"
        else:
            return "color: orange; font-weight: bold;"

    swap_columns = ["Request Id", "Employee Id", "Employee Name", "Email", "Interested Manager", "Employee to Swap", "Status"]
    swap_columns = [col for col in swap_columns if col in swap_df.columns]

    if not swap_df.empty:
        swap_df_filtered = swap_df[swap_columns].copy()
        swap_df_filtered["Request Id"] = swap_df_filtered["Request Id"].astype(int)
        styled_df = swap_df_filtered.style.applymap(color_status, subset=["Status"])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

# --- Tab 3: Employee Transfer Form ---
with tab3:
    st.subheader("✏️ Employee Transfer Request")
    col1, col2, col3 = st.columns([1,2,2])
    with col1:
        user_name_add = st.selectbox("User Name", options=["Select Your Name"]+df["Manager Name"].dropna().unique().tolist(), key="user_name_add")
    with col2:
        default_interested = st.session_state.preselect_interested_employee or "Select Interested Employee"
        interested_employee_add = st.selectbox(
            "Interested Employee",
            options=[default_interested] + (df["Employee Id"].astype(str)+" - "+df["Employee Name"]).tolist(),
            key="interested_employee_add"
        )
    with col3:
        employee_to_swap_add = st.selectbox(
            "Employee to Transfer",
            options=["Select Employee to Swap"] + (df["Employee Id"].astype(str)+" - "+df["Employee Name"]).tolist(),
            key="employee_to_swap_add"
        )

    if st.button("Submit Transfer Request", key="submit_add"):
        if not user_name_add or not interested_employee_add or not employee_to_swap_add:
            st.warning("⚠️ Please fill all fields before submitting.")
        else:
            try:
                interested_emp_id = interested_employee_add.split(" - ")[0]
                if user_name_add in df["Employee Name"].values:
                    user_id = df.loc[df["Employee Name"]==user_name_add,"Employee Id"].values[0]
                else:
                    hash_val = int(hashlib.sha256(user_name_add.encode()).hexdigest(),16)
                    user_id = str(hash_val%9000 + 1000)
                swap_emp_id = employee_to_swap_add.split(" - ")[0]
                swap_emp_name = df
                swap_emp_name = df[df["Employee Id"].astype(str) == swap_emp_id]["Employee Name"].values[0]

                # Create new row for ADS
                employee_row = df[df["Employee Id"].astype(str) == interested_emp_id].copy()
                employee_row["Interested Manager"] = user_name_add
                employee_row["Employee to Swap"] = swap_emp_name
                employee_row["Status"] = "Pending"

                # Generate unique Request ID
                request_id = f"{user_id}{interested_emp_id}{swap_emp_id}"
                employee_row["Request Id"] = int(request_id)

                # Append to ADS DataFrame
                ads_df = pd.concat([ads_df, employee_row], ignore_index=True)
                ads_df = ads_df.drop_duplicates(subset=["Employee Id", "Interested Manager", "Employee to Swap"], keep="last")

                # Update Google Sheet
                set_with_dataframe(ads_sheet, ads_df, include_index=False, resize=True)

                st.success(f"✅ Transfer request added for Employee ID {interested_emp_id}. The Request ID is {request_id}")
                # Clear preselect after submission
                st.session_state.preselect_interested_employee = None
                time.sleep(1)
                st.experimental_rerun()
            except Exception as e:
                st.error(f"❌ Error: {e}")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("❌ Remove Employee Transfer Request")
    request_id_remove = st.selectbox(
        "Enter Request ID to Remove",
        options=ads_df["Request Id"].dropna().astype(int).tolist(),
        key="request_id_remove",
        index=None
    )

    if st.button("Remove Transfer Request", key="submit_remove"):
        if not request_id_remove:
            st.warning("⚠️ Please enter a Request ID before submitting.")
        else:
            if request_id_remove in ads_df["Request Id"].values:
                ads_df = ads_df[ads_df["Request Id"] != request_id_remove]
                # Update Google Sheet
                ads_sheet.clear()
                set_with_dataframe(ads_sheet, ads_df, include_index=False, resize=True)
                st.success(f"✅ Swap request with Request ID {request_id_remove} has been removed.")
                time.sleep(1)
                st.experimental_rerun()
            else:
                st.error(f"❌ Request ID {request_id_remove} not found.")

