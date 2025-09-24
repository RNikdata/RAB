import streamlit as st
import pandas as pd
import numpy as np
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from google.oauth2.service_account import Credentials
import time

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
#billability_filter = st.sidebar.multiselect("Billable Status", options=merged_df["Billable Status"].dropna().unique())
#tag_filter = st.sidebar.multiselect("Tag", options=merged_df["Tag"].dropna().unique()) if "Tag" in merged_df.columns else []
st.sidebar.markdown("<br><br>",unsafe_allow_html = True)
st.sidebar.header("🔎 Search")
resource_search = st.sidebar.text_input("Search Employee Name or ID",placeholder = "Employe ID/Name")

# --- Main Heading ---
st.markdown("<h1 style='text-align:center'>🧑‍💼 Resource Transfer Board</h2>", unsafe_allow_html=True)

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["📝 Supply Pool", "🔄 Transfer Requests", "✏️ Employee Transfer Form"])

# --- Tab 1: Employee Table & KPIs ---
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
    filtered_df_unique1 = filtered_df_unique[filtered_df_unique["Current Billability"].isin(["PU - Person Unbilled", "-", "PI - Person Investment"])]
    filtered_df_unique["Tenure"] = pd.to_numeric(filtered_df_unique["Tenure"], errors='coerce')
    filtered_df_unique2 = filtered_df_unique[filtered_df_unique["Tenure"] > 3]
    filtered_df_unique = pd.concat([filtered_df_unique1, filtered_df_unique2], ignore_index=True)
    filtered_df_unique = filtered_df_unique.drop_duplicates(subset=["Employee Id"], keep="first")
    filtered_df_unique["3+_yr_Tenure_Flag"] = filtered_df_unique["Tenure"].apply(lambda x: "Yes" if x > 3 else "No")
        
    # --- KPI Metrics ---
    total_requests = filtered_df["Request Id"].notna().sum()
    total_approved = filtered_df["Status"].eq("Approved").sum()
    total_rejected = filtered_df["Status"].eq("Rejected").sum()
    total_pending = filtered_df["Status"].eq("Pending").sum()
    
    kpi_style = """
        <style>
        .kpi-container { 
            display: flex; 
            gap: 15px; 
            margin-bottom: 20px; 
            flex-wrap: wrap; 
        }
        .kpi-card { 
            flex: 1; 
            background: #B0C4DE; /* Aluminum grey / light blue */ 
            border-radius: 8px; 
            padding: 10px 15px; 
            text-align: center; 
            box-shadow: 1px 1px 5px rgba(0,0,0,0.1); 
            min-width: 120px; 
        }
        .kpi-card h3 { 
            margin: 0; 
            font-size: 14px; 
            color: black; 
            text-align: center; 
        }
        .kpi-card p { 
            margin: 1px 0 0 0; 
            font-size: 32px; 
            font-weight: bold; 
            color: black; 
            text-align: center; 
        }
        </style>
    """
    st.markdown(kpi_style, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <h3>Total Requests Raised</h3>
            <p>{total_requests}</p>
        </div>
        <div class="kpi-card">
            <h3>Total Approved Requests</h3>
            <p>{total_approved}</p>
        </div>
        <div class="kpi-card">
            <h3>Total Rejected Requests</h3>
            <p>{total_rejected}</p>
        </div>
        <div class="kpi-card">
            <h3>Total Pending Requests</h3>
            <p>{total_pending}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Display table
    columns_to_show = ["Manager Name","Account Name","Employee Id", "Employee Name", "Designation"]
    columns_to_show = [col for col in columns_to_show if col in filtered_df_unique.columns]
    # Apply filters
    if account_filter:
        filtered_df = filtered_df[filtered_df["Account Name"].isin(account_filter)]
    if manager_filter:
        filtered_df = filtered_df[
        (filtered_df["Manager Name"].isin(manager_filter))
    ] 
    if resource_search:
        filtered_df = filtered_df[
            filtered_df["Employee Name"].str.contains(resource_search, case=False, na=False) |
            filtered_df["Employee Id"].astype(str).str.contains(resource_search, na=False)
        ]
    st.dataframe(filtered_df_unique[columns_to_show], use_container_width=True, height=500, hide_index=True)
    
# --- Tab 2: Swap Requests ---
with tab2:
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
    if not swap_df.empty:
        col1, col2 = st.columns([2, 2])
        with col1:
            request_id_options = swap_df["Request Id"].dropna().unique().astype(int).tolist()
            request_id_select = st.selectbox(
                "Select Request ID",
                options=request_id_options,
                key="request_id_select_tab2",
                index=None
            )
        with col2:
            decision = st.radio(
                "Action",
                options=["Approve", "Reject"],
                horizontal=True,
                key="decision_radio"
            )

        # --- Message placeholder below submit ---
        msg_placeholder = st.empty()

        # Submit button
        if st.button("Submit", key="submit_decision"):
            if request_id_select == "Select Request ID...":
                msg_placeholder.warning("⚠️ Please select a Request ID before submitting.")
            else:
                current_status = ads_df.loc[ads_df["Request Id"] == request_id_select, "Status"].values[0]

                # Logic: Approved cannot be rejected, Rejected can be approved
                if current_status == "Approved" and decision == "Reject":
                    msg_placeholder.error(f"❌ Request ID {request_id_select} is already Approved and cannot be Rejected.")
                    time.sleep(1)
                    st.rerun()
                else:
                    try:
                        status_value = "Approved" if decision == "Approve" else "Rejected"
                        # Update local dataframe
                        ads_df.loc[ads_df["Request Id"] == request_id_select, "Status"] = status_value
                        # Update Google Sheet
                        set_with_dataframe(ads_sheet, ads_df, include_index=False, resize=True)
                        msg_placeholder.success(f"✅ Request ID {request_id_select} marked as {status_value}")
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

    swap_columns = ["Request Id", "Employee Id", "Employee Name", "Email", 
                    "Interested Manager", "Employee to Swap", "Status"]
    swap_columns = [col for col in swap_columns if col in swap_df.columns]

    swap_df_filtered = swap_df[swap_df["Request Id"].notna()] if "Request Id" in swap_df.columns else pd.DataFrame()
    if not swap_df_filtered.empty:
        swap_df_filtered["Request Id"] = swap_df_filtered["Request Id"].astype(int)
        styled_swap_df = swap_df_filtered[swap_columns].style.applymap(color_status, subset=["Status"])
        st.dataframe(styled_swap_df, use_container_width=True, hide_index=True)

# --- Tab 3: Employee Swap Form ---
with tab3:
    st.markdown("<br><br>",unsafe_allow_html = True)
    st.subheader("🔄 Employee Transfer Request")

    # --- Add Swap Request ---
    col1, col2, col3 = st.columns([1, 2, 2])
    with col1:
        user_name_add = st.selectbox(
            "User Name",
            options=["Select Your Name"] + df["Employee Name"].tolist(),
            key="user_name_add"
        )
    with col2:
        interested_employee_add = st.selectbox(
            "Interested Employee",
            options=["Select Interested Employee"] + (df["Employee Id"].astype(str) + " - " + df["Employee Name"]).tolist(),
            key="interested_employee_add"
        )
    with col3:
        employee_to_swap_add = st.selectbox(
            "Employee to Transfer",
            options = ["Select Employee to Swap"] + (df["Employee Id"].astype(str) + " - " + df["Employee Name"]).tolist(),
            key="employee_to_swap_add"
        )

    if st.button("Submit Transfer Request", key="submit_add"):
        if not user_name_add or not interested_employee_add or not employee_to_swap_add:
            st.warning("⚠️ Please fill all fields before submitting.")
        else:
            try:
                interested_emp_id = interested_employee_add.split(" - ")[0]
                user_id = df[df["Employee Name"] == user_name_add]["Employee Id"].values[0]
                swap_emp_id = employee_to_swap_add.split(" - ")[0]
                swap_emp_name = df[df["Employee Id"].astype(str) == swap_emp_id]["Employee Name"].values[0]

                employee_row = df[df["Employee Id"].astype(str) == interested_emp_id].copy()
                employee_row["Interested Manager"] = user_name_add
                employee_row["Employee to Swap"] = swap_emp_name
                employee_row["Status"] = "Pending"

                # Generate unique request id
                request_id = f"{user_id}{interested_emp_id}{swap_emp_id}"
                employee_row["Request Id"] = int(request_id)

                ads_df = pd.concat([ads_df, employee_row], ignore_index=True)
                ads_df = ads_df.drop_duplicates(subset=["Employee Id","Interested Manager","Employee to Swap"], keep="last")

                # Update Google Sheet
                set_with_dataframe(ads_sheet, ads_df)

                st.success(f"✅ Transfer request added for Employee ID {interested_emp_id}. The Request ID is {request_id}")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("❌ Remove Employee Transfer Request")

    request_id_remove = st.selectbox(
        "Enter Request ID to Remove",
        options = ads_df["Request Id"].dropna().astype(int).tolist(),
        key="request_id_remove",
        index = None
    )

    if st.button("Remove Transfer Request", key="submit_remove"):
        if not request_id_remove:
            st.warning("⚠️ Please enter a Request ID before submitting.")
        else:
            if request_id_remove in ads_df["Request Id"].values:
                ads_df = ads_df[ads_df["Request Id"] != request_id_remove]
                # Update Google Sheet
                ads_sheet.clear()
                set_with_dataframe(ads_sheet, ads_df)
                st.success(f"✅ Swap request with Request ID {request_id_remove} has been removed.")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"❌ Request ID {request_id_remove} not found.")
