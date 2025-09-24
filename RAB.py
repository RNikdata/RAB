import streamlit as st
import pandas as pd
import numpy as np
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from google.oauth2.service_account import Credentials
import time
import hashlib

st.set_page_config(layout="wide")

# --- Connect to Google Sheets using Streamlit secrets ---
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

# --- Sidebar: Logo & Company Name ---
#st.sidebar.image("logo.jpeg", width=150)
st.sidebar.markdown(
    """
    <div style='text-align: left; margin-left: 43px;'>
        <img src="https://upload.wikimedia.org/wikipedia/en/0/0c/Mu_Sigma_Logo.jpg" width="100">
    </div>
    """,
    unsafe_allow_html=True
)

# --- Sidebar Filters ---
st.sidebar.markdown("<br><br>",unsafe_allow_html = True)
st.sidebar.markdown("<br><br>",unsafe_allow_html = True)
st.sidebar.header("⚙️ Filters")
account_filter = st.sidebar.multiselect("Account Name", options=merged_df["Account Name"].dropna().unique())
manager_filter = st.sidebar.multiselect("Manager Name", options=merged_df["Manager Name"].dropna().unique())
designation_filter = st.sidebar.multiselect("Designation", options=merged_df["Designation"].dropna().unique())
#billability_filter = st.sidebar.multiselect("Billable Status", options=merged_df["Billable Status"].dropna().unique())
#tag_filter = st.sidebar.multiselect("Tag", options=merged_df["Tag"].dropna().unique()) if "Tag" in merged_df.columns else []
st.sidebar.markdown("<br><br>",unsafe_allow_html = True)
st.sidebar.header("🔎 Search")
resource_search = st.sidebar.text_input("Search Employee Name or ID",placeholder = "Employe ID/Name")

# --- Main Heading with Refresh Button ---
col_title, col_refresh = st.columns([9, 1])  # Title + refresh button
with col_title:
    st.markdown("<h1 style='text-align:center'>🧑‍💼 Resource Transfer Board</h1>", unsafe_allow_html=True)
with col_refresh:
    if st.button("🔄 Refresh"):
        st.rerun()

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Transfer Summary","📝 Supply Pool", "🔄 Transfer Requests", "✏️ Employee Transfer Form"])

# --- Tab 1: Manager-wise Summary ---
with tab1:
    st.subheader("📊 Manager Transfer Summary")
    st.markdown("<br>", unsafe_allow_html=True)
    summary_df = ads_df.copy()

    # Remove invalid manager rows
    summary_df = summary_df[summary_df["Manager Name"].notna()]
    summary_df = summary_df[summary_df["Manager Name"].str.strip() != "- - -"]


    # Ensure Status column exists
    summary_df["Status"] = summary_df["Status"].fillna("Pending")

    # List of all managers for summary
    all_managers = pd.concat([summary_df["Manager Name"], summary_df["Interested Manager"]]).dropna().unique()

    # Prepare summary table
    summary_list = []
    for mgr in all_managers:
        temp_df = summary_df[
            (summary_df["Manager Name"] == mgr) | 
            (summary_df["Interested Manager"] == mgr)
        ]
        
        total_requests = temp_df["Request Id"].dropna().nunique()
        # Total Approved (unique Request Ids with status Approved)
        total_approved = (
            temp_df[temp_df["Status"].notna() & (temp_df["Status"] == "Approved")]["Request Id"]
            .dropna()
            .nunique()
        )
        # Total Rejected (unique Request Ids with status Approved)
        total_rejected = (
            temp_df[temp_df["Status"].notna() & (temp_df["Status"] == "Rejected")]["Request Id"]
            .dropna()
            .nunique()
        )
        # Total Pending (unique Request Ids with status Pending)
        total_pending = (
            temp_df[temp_df["Status"].notna() & (temp_df["Status"] == "Pending")]["Request Id"]
            .dropna()
            .nunique()
        )
        
        summary_list.append({
            "Manager Name": mgr,
            "Total Requests Raised": total_requests,
            "Total Approved": total_approved,
            "Total Rejected": total_rejected,
            "Total Pending": total_pending
        })

    grouped_summary = pd.DataFrame(summary_list)

    # Apply sidebar filters
    if manager_filter:
        grouped_summary = grouped_summary[
            (grouped_summary["Manager Name"].isin(manager_filter))
        ]

    # Display summary table
    st.dataframe(
        grouped_summary.sort_values(
            by=["Total Requests Raised", "Manager Name"], 
            ascending=[False, True]   # Requests Descending, then Manager Ascending
        ),
        use_container_width=True,
        hide_index=True,
        height=500
    )

    # --- Note Section ---
    st.markdown(
        """
        <p style='margin-top:15px; color:#b0b0b0; font-size:14px; font-style:italic;'>
            Note: "Account Name" and "Designation" filters are not applicable for this Manager Summary view.
        </p>
        """,
        unsafe_allow_html=True
    )


# --- Tab 2: Employee Table & KPIs ---
with tab2:
    st.subheader("📝 Supply Pool")
    st.sidebar.markdown("<br>",unsafe_allow_html = True)
    filtered_df = merged_df.copy()

    # Apply filters
    if account_filter:
        filtered_df = filtered_df[filtered_df["Account Name"].isin(account_filter)]
    if manager_filter:
        filtered_df = filtered_df[
        (filtered_df["Manager Name"].isin(manager_filter)) |
        (filtered_df["Interested Manager"].isin(manager_filter)) 
    ]
    if designation_filter:
        filtered_df = filtered_df[filtered_df["Designation"].isin(designation_filter)]
    if resource_search:
        filtered_df = filtered_df[
            filtered_df["Employee Name"].str.contains(resource_search, case=False, na=False) |
            filtered_df["Employee Id"].astype(str).str.contains(resource_search, na=False)
        ]
    filtered_df2 = filtered_df.copy()

    filtered_df_unique = filtered_df.drop_duplicates(subset=["Employee Id"], keep="first")
    filtered_df_unique = filtered_df_unique[~filtered_df_unique["Designation"].isin(["AL"])]
    filtered_df_unique1 = filtered_df_unique[filtered_df_unique["Current Billability"].isin(["PU - Person Unbilled", "-", "PI - Person Investment"])]
    filtered_df_unique["Tenure"] = pd.to_numeric(filtered_df_unique["Tenure"], errors='coerce')
    filtered_df_unique2 = filtered_df_unique[filtered_df_unique["Tenure"] > 3]
    filtered_df_unique = pd.concat([filtered_df_unique1, filtered_df_unique2], ignore_index=True)
    filtered_df_unique = filtered_df_unique.drop_duplicates(subset=["Employee Id"], keep="first")
    filtered_df_unique["3+_yr_Tenure_Flag"] = filtered_df_unique["Tenure"].apply(lambda x: "Yes" if x > 3 else "No")


    # Display table
    columns_to_show = ["Manager Name","Account Name","Employee Id", "Employee Name", "Designation","Tag","Billable Status","3+_yr_Tenure_Flag"]
    columns_to_show = [col for col in columns_to_show if col in filtered_df_unique.columns]
    # Apply filters
    if account_filter:
        filtered_df_unique = filtered_df_unique[filtered_df_unique["Account Name"].isin(account_filter)]
    if manager_filter:
        filtered_df_unique = filtered_df_unique[
        (filtered_df_unique["Manager Name"].isin(manager_filter))
    ]
    if designation_filter:
        filtered_df = filtered_df[filtered_df["Designation"].isin(designation_filter)]
    if resource_search:
        filtered_df_unique = filtered_df_unique[
            filtered_df_unique["Employee Name"].str.contains(resource_search, case=False, na=False) |
            filtered_df_unique["Employee Id"].astype(str).str.contains(resource_search, na=False)
        ]

    st.dataframe(filtered_df_unique[columns_to_show], use_container_width=True, height=500, hide_index=True)
    
with tab3:
    st.subheader("🔄 Transfer Requests")
    
    swap_df = ads_df.copy()

    # Ensure Status column exists and default to Pending
    if "Status" not in swap_df.columns:
        swap_df["Status"] = "Pending"
    else:
        swap_df["Status"] = swap_df["Status"].fillna("Pending")

    # --- Row 1: Filters ---
    col1, col2 = st.columns([2, 2])
    with col1:
        interested_manager_search = st.text_input(
            "Search by Interested Manager",
            key="interested_manager_search_box",
            placeholder="Type manager name..."
        )
    with col2:
        status_filter = st.selectbox(
            "Filter by Status",
            options=["All", "Pending", "Approved", "Rejected"],
            key="status_filter_box"
        )

    # Apply filters
    if interested_manager_search and "Interested Manager" in swap_df.columns:
        swap_df = swap_df[
            swap_df["Interested Manager"].str.contains(interested_manager_search, case=False, na=False)
        ]
    if status_filter != "All" and "Status" in swap_df.columns:
        swap_df = swap_df[swap_df["Status"] == status_filter]
    st.markdown("---")

    # --- Row 2: Approve/Reject Form ---
    # Pending requests **after search**
    pending_swap_df_filtered = swap_df[swap_df["Status"] == "Pending"]
    
    col1, col2 = st.columns([2, 2])
    
    with col1:
        if not pending_swap_df_filtered.empty:
            request_id_options = pending_swap_df_filtered["Request Id"].dropna().unique().astype(int).tolist()
        else:
            request_id_options = []
        request_id_select = st.selectbox(
            "Select Request ID",
            options=request_id_options,
            key="request_id_select_tab2",
            index = None
        )

    with col2:
        decision = st.radio(
            "Action",
            options=["Approve", "Reject"],
            horizontal=True,
            key="decision_radio"
        )

    # --- Message placeholder ---
    msg_placeholder = st.empty()

    # Submit button
    if st.button("Submit", key="submit_decision"):
        if request_id_select not in pending_swap_df_filtered["Request Id"].values:
            msg_placeholder.warning("⚠️ Please select a valid pending Request ID.")
        else:
            current_status = ads_df.loc[ads_df["Request Id"] == request_id_select, "Status"].values[0]
            if current_status == "Approved" and decision == "Reject":
                msg_placeholder.error(f"❌ Request ID {request_id_select} is already Approved and cannot be Rejected.")
            else:
                try:
                    status_value = "Approved" if decision == "Approve" else "Rejected"
                    # Update local dataframe
                    ads_df.loc[ads_df["Request Id"] == request_id_select, "Status"] = status_value
                    # Update Google Sheet
                    set_with_dataframe(ads_sheet, ads_df, include_index=False, resize=True)
                    msg_placeholder.success(f"✅ Request ID {request_id_select} marked as {status_value}")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    msg_placeholder.error(f"❌ Error updating request: {e}")

    # --- Colored Status Table ---
    def color_status(val):
        if val == "Approved":
            return "color: green; font-weight: bold;"
        elif val == "Rejected":
            return "color: red; font-weight: bold;"
        else:  # Pending
            return "color: orange; font-weight: bold;"

    swap_columns = ["Request Id", "Employee Id", "Employee Name", "Manager Name","Account Name", "Designation", 
                    "Interested Manager", "Employee to Swap", "Status"]
    swap_columns = [col for col in swap_columns if col in swap_df.columns]

    swap_df_filtered = swap_df[swap_df["Request Id"].notna()] if "Request Id" in swap_df.columns else pd.DataFrame()
    if not swap_df_filtered.empty:
        swap_df_filtered["Request Id"] = swap_df_filtered["Request Id"].astype(int)
        styled_swap_df = swap_df_filtered[swap_columns].style.applymap(color_status, subset=["Status"])
        st.dataframe(styled_swap_df, use_container_width=True, hide_index=True)

# --- Tab 3: Employee Transfer Form ---
with tab4:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.subheader("🔄 Employee Transfer Request")

    # Get list of approved employees (either as Interested Employee or Employee to Swap)
    approved_requests = ads_df[ads_df["Status"] == "Approved"]
    approved_interested = approved_requests["Employee Id"].astype(str).tolist()  # Employees who are Interested
    approved_swap = approved_requests["Employee to Swap"].tolist()                 # Employees already swapped

    # Prepare available employees excluding approved ones
    available_employees = df[~df["Employee Id"].astype(str).isin(approved_interested) & 
                             ~df["Employee Name"].isin(approved_swap)]
    options_interested = ["Select Interested Employee"] + (available_employees["Employee Id"].astype(str) + " - " + available_employees["Employee Name"]).tolist()
    options_swap = ["Select Employee to Swap"] + (available_employees["Employee Id"].astype(str) + " - " + available_employees["Employee Name"]).tolist()

    # Pre-fill if selected from Tab 1
    preselected = st.session_state.get("preselect_interested_employee", None)
    default_idx = options_interested.index(preselected) if preselected in options_interested else 0

    # --- Form in a single row (3 columns) ---
    col1, col2, col3 = st.columns([1, 2, 2])

    with col1:
        user_name_add = st.selectbox(
            "User Name",
            options=["Select Your Name"] + df["Manager Name"].dropna().unique().tolist(),
            key="user_name_add"
        )

    with col2:
        interested_employee_add = st.selectbox(
            "Interested Employee",
            options=options_interested,
            index=default_idx,
            key="interested_employee_add"
        )

    with col3:
        employee_to_swap_add = st.selectbox(
            "Employee to Transfer",
            options=options_swap,
            key="employee_to_swap_add"
        )

    # Clear session state after prefill
    if "preselect_interested_employee" in st.session_state:
        del st.session_state["preselect_interested_employee"]

    # --- Submit Transfer Request ---
    if st.button("Submit Transfer Request", key="submit_add"):
        if not user_name_add or not interested_employee_add or not employee_to_swap_add:
            st.warning("⚠️ Please fill all fields before submitting.")
        else:
            try:
                interested_emp_id = interested_employee_add.split(" - ")[0]
                swap_emp_id = employee_to_swap_add.split(" - ")[0]
                swap_emp_name = df[df["Employee Id"].astype(str) == swap_emp_id]["Employee Name"].values[0]

                # Determine user ID
                if user_name_add in df["Employee Name"].values:
                    user_id = df.loc[df["Employee Name"] == user_name_add, "Employee Id"].values[0]
                else:
                    hash_val = int(hashlib.sha256(user_name_add.encode()).hexdigest(), 16)
                    user_id = str(hash_val % 9000 + 1000)

                # Create new request row
                employee_row = df[df["Employee Id"].astype(str) == interested_emp_id].copy()
                employee_row["Interested Manager"] = user_name_add
                employee_row["Employee to Swap"] = swap_emp_name
                employee_row["Status"] = "Pending"

                # Generate unique Request ID
                request_id = f"{user_id}{interested_emp_id}{swap_emp_id}"
                employee_row["Request Id"] = int(request_id)

                # Add to ADS dataframe
                ads_df = pd.concat([ads_df, employee_row], ignore_index=True)
                ads_df = ads_df.drop_duplicates(subset=["Employee Id","Interested Manager","Employee to Swap"], keep="last")

                # Update Google Sheet
                set_with_dataframe(ads_sheet, ads_df)

                st.success(f"✅ Transfer request added for Employee ID {interested_emp_id}. The Request ID is {request_id}")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    # --- Remove Transfer Request ---
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
                ads_sheet.clear()
                set_with_dataframe(ads_sheet, ads_df)
                st.success(f"✅ Swap request with Request ID {request_id_remove} has been removed.")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"❌ Request ID {request_id_remove} not found.")
