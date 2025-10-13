import streamlit as st
import pandas as pd
import numpy as np
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from google.oauth2.service_account import Credentials
import time
import hashlib
import os
import requests
from PIL import Image
from io import BytesIO


st.set_page_config(
    page_title="Resource Transfer Board",  # <-- Browser tab name
    page_icon="🧑‍💼",                            # <-- Favicon in browser tab
    layout="wide"                              # optional
)

#######################################
# --- Google Sheets Connection ---
#######################################

# --- Connect to Google Sheets using Streamlit secrets ---
service_account_info = st.secrets["google_service_account"]
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
gc = gspread.authorize(credentials)

# # --- Google Sheet ID & Sheet Names ---
SHEET_ID = "1yagvN3JhJtml0CMX4Lch7_LdPeUzvPcl1VEfyy8RvC4"
EMPLOYEE_SHEET_NAME = "Employee Data"
ADS_SHEET_NAME = "Employee ADS"

employee_sheet = gc.open_by_key(SHEET_ID).worksheet(EMPLOYEE_SHEET_NAME)
ads_sheet = gc.open_by_key(SHEET_ID).worksheet(ADS_SHEET_NAME)

# --- Load Data ---
df = get_as_dataframe(employee_sheet, evaluate_formulas=True).dropna(how="all")
ads_df = get_as_dataframe(ads_sheet, evaluate_formulas=True).dropna(how="all")

########################################

# --- Load Data --- (for local testing & development)
#df = pd.read_excel(r"C:\Users\nikhil.r\OneDrive - Mu Sigma Business Solutions Pvt. Ltd\Desktop\Jupyter\Employee Data.xlsx")
#ads_df = pd.read_excel(r"C:\Users\nikhil.r\OneDrive - Mu Sigma Business Solutions Pvt. Ltd\Desktop\Jupyter\Employee ADS.xlsx")

if ads_df.empty:
    ads_df = pd.DataFrame(columns=["Employee Id", "Interested Manager", "Employee to Swap", "Request Id","Status"])

# --- Merge DataFrames ---
merged_df = df.merge(
    ads_df[["Employee Id", "Interested Manager", "Employee to Swap", "Request Id","Status"]] if not ads_df.empty else pd.DataFrame(),
    on="Employee Id",
    how="left"
)

#######################################
# --- API Authentication ---
#######################################
API_USERNAME = st.secrets.get("api_auth", {}).get("username", "streamlit_user")
API_PASSWORD = st.secrets.get("api_auth", {}).get("password", "streamlitadmin@mu-sigma25")
BASE_URL = st.secrets.get("api_auth", {}).get("base_url", "https://muerp.mu-sigma.com/dmsRest/getEmployeeImage")

def get_employee_image(employee_id):
    """Fetch employee image from API and return PIL image or default image."""
    url = BASE_URL
    headers = {
        "userid": API_USERNAME,
        "password": API_PASSWORD
    }
    params = {"id": employee_id}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        if response.status_code == 200:
            # Return image object for Streamlit
            img = Image.open(BytesIO(response.content))
            return img
        else:
            st.warning(f"⚠️ API returned status code: {response.status_code} for Employee ID {employee_id}")
            return Image.open(BytesIO(requests.get(
                "https://static.vecteezy.com/system/resources/previews/008/442/086/original/illustration-of-human-icon-user-symbol-icon-modern-design-on-blank-background-free-vector.jpg"
            ).content))
    except Exception as e:
        st.error(f"❌ Error fetching image for Employee ID {employee_id}: {e}")
        return Image.open(BytesIO(requests.get(
            "https://static.vecteezy.com/system/resources/previews/008/442/086/original/illustration-of-human-icon-user-symbol-icon-modern-design-on-blank-background-free-vector.jpg"
        ).content))
#######################################
# --- Page Navigation Setup ---
#######################################
if "active_page" not in st.session_state:
    st.session_state["active_page"] = "Transfer Summary"

# --- Common Title & Refresh ---
header_col1, header_col2 = st.columns([6, 1])

with header_col1:
    st.markdown("<h1 style='text-align:center'>🧑‍💼 Resource Transfer Board</h1>", unsafe_allow_html=True)

with header_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Refresh"):
        st.rerun()
        

# --- Top Navigation Buttons (Navbar Style) ---
nav_cols = st.columns([1, 1, 1, 1])  # equal spacing for 4 buttons

with nav_cols[0]:
    if st.button("📊 Transfer Summary", use_container_width=True):
        st.session_state["active_page"] = "Transfer Summary"

with nav_cols[1]:
    if st.button("📝 Supply Pool", use_container_width=True):
        st.session_state["active_page"] = "Supply Pool"

with nav_cols[2]:
    if st.button("🔁 Transfer Requests", use_container_width=True):
        st.session_state["active_page"] = "Transfer Requests"

with nav_cols[3]:
    if st.button("✏️ Employee Transfer Form", use_container_width=True):
        st.session_state["active_page"] = "Employee Transfer Form"
st.markdown("---")
# --- Tab 1: Manager-wise Summary ---
            
if st.session_state["active_page"] == "Transfer Summary":

    # --- Sidebar: Logo & Company Name ---
    st.sidebar.markdown(
        """
        <div style='text-align: left; margin-left: 43px;'>
            <img src="https://upload.wikimedia.org/wikipedia/en/0/0c/Mu_Sigma_Logo.jpg" width="100">
        </div>
        """,
        unsafe_allow_html=True
    )

    top_managers = [
        "Nivedhan Narasimhan",
        "Rajdeep Roy Choudhury",
        "Riyas Mohammed Abdul Razak",
        "Sabyasachi Mondal",
        "Satyananda Palui",
        "Shilpa P Bhat",
        "Siddharth Chhottray",
        "Tanmay Sengupta",
        "Samanvitha A Bhagavath",
        "Aviral Bhargava"
    ]
    # designation = ["TDS1","TDS2","TDS3","TDS4","-"]
    
    # --- Sidebar Filters ---
    st.sidebar.markdown("<br><br>",unsafe_allow_html = True)
    st.sidebar.markdown("<br><br>",unsafe_allow_html = True)
    st.sidebar.header("⚙️ Filters")
    # account_filter = st.sidebar.multiselect("Account Name", options=merged_df["Account Name"].dropna().unique())
    manager_filter = st.sidebar.multiselect(
        "Manager Name",
        options=[mgr for mgr in merged_df["Manager Name"].dropna().unique() if mgr in top_managers]
    )
    # designation_filter = st.sidebar.multiselect(
    #     "Designation",
    #     options=[d for d in merged_df["Designation"].dropna().unique() if d in designation]
    # )
    st.sidebar.header("🔎 Search")
    resource_search = st.sidebar.text_input("Search Employee Name or ID",placeholder = "Employe ID/Name")
    st.subheader("📊 Manager Transfer Summary")
    st.markdown("<br>", unsafe_allow_html=True)
    summary_df = ads_df.copy()
    summary_df1 = df.copy()

    # Dictionary to store manager: [list of employee names]
    manager_employees = {}
    
    for mgr in top_managers:
        # Filter employees under this manager
        emp_names = summary_df.loc[
            summary_df["Manager Name"] == mgr, "Employee Name"
        ].dropna().unique().tolist()
        
        # Store in dictionary
        manager_employees[mgr] = emp_names

    mgr_to_mgr = dict(zip(summary_df["Employee Name"], summary_df["Manager Name"]))
    
    summary_df1 = summary_df1.drop_duplicates(subset=["Employee Id"], keep="first")
    summary_df1 = summary_df1[~summary_df1["Designation"].isin(["AL"])]
    summary_df11 = summary_df1[summary_df1["Current Billability"].isin(["PU - Person Unbilled", "-", "PI - Person Investment"])]
    summary_df1["Tenure"] = pd.to_numeric(summary_df1["Tenure"], errors='coerce')
    summary_df12 = summary_df1[summary_df1["Tenure"] > 3]
    summary_df1 = pd.concat([summary_df11, summary_df12], ignore_index=True)
    summary_df1 = summary_df1.drop_duplicates(subset=["Employee Id"], keep="first")
    
    # Remove invalid manager rows
    summary_df = summary_df[summary_df["Manager Name"].notna()]
    summary_df = summary_df[summary_df["Manager Name"].str.strip() != "- - -"]

    # Ensure Status column exists
    summary_df["Status"] = summary_df["Status"].fillna("Pending")

    # Build manager-to-manager map
    #display(mgr_to_mgr)
    
    # Recursive lookup for top-level manager
    def get_final_manager(mgr_name):
        a=mgr_name
        visited = set()
        while mgr_name and mgr_name not in top_managers:
            if mgr_name in visited:
                return None
            visited.add(mgr_name)
            mgr_name = mgr_to_mgr.get(mgr_name)
        return mgr_name if mgr_name in top_managers else None
    
    # Create Final Manager column
    summary_df["Final Manager"] = summary_df["Manager Name"].apply(
        lambda x: x if x in top_managers else get_final_manager(x)
    )

    # List of all managers for summary
    all_managers = pd.concat([summary_df["Manager Name"], summary_df["Interested Manager"]]).dropna().unique()
    
    no_of_managers = len(top_managers)
    
    # all_managers is a NumPy array — so filter it using np.isin
    all_managers = [mgr for mgr in all_managers if mgr in top_managers]

    summary_df1 = summary_df1.merge(
        summary_df[["Employee Id", "Final Manager"]] if not summary_df.empty else pd.DataFrame(),
        on="Employee Id",
        how="left"
    )
    
    # Prepare summary table
    summary_list = []
    for mgr in all_managers:
        temp_df = summary_df[
            (summary_df["Final Manager"] == mgr) | 
            (summary_df["Interested Manager"] == mgr)
        ]
        temp_df1 = summary_df1[summary_df1["Final Manager"] == mgr]
        
        total_requests = temp_df["Request Id"].dropna().nunique()
        total_approved = (temp_df[temp_df["Status"] == "Approved"]["Request Id"].dropna().nunique())
        total_rejected = (temp_df[temp_df["Status"] == "Rejected"]["Request Id"].dropna().nunique())
        total_pending = (temp_df[temp_df["Status"] == "Pending"]["Request Id"].dropna().nunique())

        unique_employees = temp_df1["Employee Id"].astype(str).dropna().unique()
        total_employees = len(unique_employees)
        
        summary_list.append({
            "Manager Name": mgr,
            "Total Available Employee": total_employees,
            "Total Requests Raised": total_requests,
            "Total Approved": total_approved,
            "Total Rejected": total_rejected,
            "Total Pending": total_pending
        })

    grouped_summary = pd.DataFrame(summary_list)

    if manager_filter:
        grouped_summary = grouped_summary[grouped_summary["Final Manager"].isin(manager_filter)]

    st.dataframe(
        grouped_summary.sort_values(
            by=["Total Requests Raised", "Manager Name"], 
            ascending=[False, True]
        ),
        use_container_width=True,
        hide_index=True,
        height=no_of_managers*35
    )

    # st.markdown(
    #     "<p style='margin-top:15px; color:#b0b0b0; font-size:14px; font-style:italic;'>"
    #     'Note: "Account Name" and "Designation" filters are not applicable for this Manager Summary view.'
    #     "</p>",
    #     unsafe_allow_html=True
    # )

elif st.session_state["active_page"] == "Supply Pool":

    # --- Sidebar: Logo & Company Name ---
    st.sidebar.markdown(
        """
        <div style='text-align: left; margin-left: 43px;'>
            <img src="https://upload.wikimedia.org/wikipedia/en/0/0c/Mu_Sigma_Logo.jpg" width="100">
        </div>
        """,
        unsafe_allow_html=True
    )
    top_managers = [
        "Nivedhan Narasimhan",
        "Rajdeep Roy Choudhury",
        "Riyas Mohammed Abdul Razak",
        "Sabyasachi Mondal",
        "Satyananda Palui",
        "Shilpa P Bhat",
        "Siddharth Chhottray",
        "Tanmay Sengupta",
        "Samanvitha A Bhagavath",
        "Aviral Bhargava"
    ]
    
    designation = [
        "TDS1",
        "TDS2",
        "TDS3",
        "TDS4",
        "-"
    ]
    
    # --- Sidebar Filters ---
    st.sidebar.markdown("<br><br>",unsafe_allow_html = True)
    st.sidebar.markdown("<br><br>",unsafe_allow_html = True)
    st.sidebar.header("⚙️ Filters")
    account_filter = st.sidebar.multiselect("Account Name", options=merged_df["Account Name"].dropna().unique())
    manager_filter = st.sidebar.multiselect(
        "Manager Name",
        options=[mgr for mgr in merged_df["Manager Name"].dropna().unique() if mgr in top_managers]
    )
    designation_filter = st.sidebar.multiselect(
        "Designation",
        options=[d for d in merged_df["Designation"].dropna().unique() if d in designation]
    )
    st.sidebar.markdown("<br><br>",unsafe_allow_html = True)
    st.sidebar.header("🔎 Search")
    resource_search = st.sidebar.text_input("Search Employee Name or ID",placeholder = "Employe ID/Name")
    st.subheader("📝 Supply Pool")
    st.markdown("<br>", unsafe_allow_html=True)
    warning_placeholder = st.empty()
    df_unique = df.drop_duplicates(subset=["Employee Id"]).copy()

    # Dictionary to store manager: [list of employee names]
    manager_employees = {}
    
    for mgr in top_managers:
        # Filter employees under this manager
        emp_names = df_unique.loc[
            df_unique["Manager Name"] == mgr, "Employee Name"
        ].dropna().unique().tolist()
        
        # Store in dictionary
        manager_employees[mgr] = emp_names

    mgr_to_mgr = dict(zip(df_unique["Employee Name"], df_unique["Manager Name"]))

    def get_final_manager(mgr_name):
        visited = set()
        while mgr_name and mgr_name not in top_managers:
            if mgr_name in visited:
                return None
            visited.add(mgr_name)
            mgr_name = mgr_to_mgr.get(mgr_name)
        return mgr_name if mgr_name in top_managers else None
    
    # Create Final Manager column
    df_unique["Final Manager"] = df_unique["Manager Name"].apply(
        lambda x: x if x in top_managers else get_final_manager(x)
    )

    # --- Filter DataFrame based on filters ---
    if account_filter:
        df_unique = df_unique[df_unique["Account Name"].isin(account_filter)]
    if manager_filter:
        df_unique = df_unique[df_unique["Final Manager"].isin(manager_filter)]
    if designation_filter:
        df_unique = df_unique[df_unique["Designation"].isin(designation_filter)]
    if resource_search:
        df_unique = df_unique[
            df_unique["Employee Name"].str.contains(resource_search, case=False, na=False) |
            df_unique["Employee Id"].astype(str).str.contains(resource_search, na=False)
        ]

    # --- Tenure & Billability filters ---
    filtered_df_unique = df_unique.drop_duplicates(subset=["Employee Id"], keep="first")
    filtered_df_unique = filtered_df_unique[~filtered_df_unique["Designation"].isin(["AL"])]
    filtered_df_unique1 = filtered_df_unique[filtered_df_unique["Current Billability"].isin(["PU - Person Unbilled", "-", "PI - Person Investment"])]
    filtered_df_unique["Tenure"] = pd.to_numeric(filtered_df_unique["Tenure"], errors='coerce')
    filtered_df_unique2 = filtered_df_unique[filtered_df_unique["Tenure"] > 3]
    filtered_df_unique = pd.concat([filtered_df_unique1, filtered_df_unique2], ignore_index=True)
    filtered_df_unique = filtered_df_unique.drop_duplicates(subset=["Employee Id"], keep="first")
    filtered_df_unique["3+_yr_Tenure_Flag"] = filtered_df_unique["Tenure"].apply(lambda x: "Yes" if x > 3 else "No")
    filtered_df_unique = filtered_df_unique[filtered_df_unique["Final Manager"].notna()]
    filtered_df_unique["Image URL"] = filtered_df_unique["Employee Id"].apply(get_employee_image)

    
    columns_to_show = ["Manager Name", "Account Name", "Employee Id", "Employee Name", "Designation", "Rank","Final Manager"]
    columns_to_show = [col for col in columns_to_show if col in filtered_df_unique.columns]

    # --- Display Employee Cards ---
    if not filtered_df_unique.empty:
        sorted_df = filtered_df_unique[columns_to_show].sort_values(by="Employee Name").reset_index(drop=True)
        n = len(sorted_df)
        for i in range(0, n, 2):
            cols = st.columns([1,1])
            for j, col in enumerate(cols):
                if i + j < n:
                    row = sorted_df.iloc[i + j]
                    img_url = get_emloyee_image(row['Employee Id'])
                    with col:
                        with st.container():
                            st.markdown(
                                f"""
                                <div style='display:flex; align-items:center; gap:15px; padding:8px; border:3px solid #e0e0e0; border-radius:8px; margin-bottom:5px;'>
                                    <div style='flex-shrink:0;'>
                                        <img src= "{img_url}" style='width:110px; height:120px; border-radius:4px; object-fit:cover;'>
                                    </div>
                                    <div style='flex-grow:1;'>
                                        <div style='font-size:20px; font-weight:bold;'>{row['Employee Name']}</div>
                                        <div style='font-size:14px; margin-top:5px; line-height:1.6;'>
                                            <div style='display:flex;'>
                                                <div style='width:33%;'><b>👤 ID:</b> {row['Employee Id']}</div>
                                                <div style='width:33%;'><b>📌 Band:</b> {row['Designation']}</div>
                                                <div style='width:33%;'><b>🏷️ Rank:</b> {row['Rank']}</div>
                                            </div>
                                            <div style='display:flex;'>
                                                <div style='margin-top:4px;'><b>📂 Account:</b> {row['Account Name']}</div>
                                            </div>
                                            <div style='margin-top:4px;'><b>🧑‍💼 Mapped to:</b> {row['Manager Name']}</div>
                                            <div style='margin-top:4px;'><b>🧑‍💼 Manager:</b> {row['Final Manager']}</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                            dum_ads_df = ads_df.copy()
                            dum_ads_df = dum_ads_df[dum_ads_df["Request Id"].notna()]
                            
                            if st.button("Interested in Employee", key=f"interested_{row['Employee Id']}"):
                                emp_name = row['Employee Name']
                                
                                if {"Employee Name", "Employee to Swap", "Status"}.issubset(dum_ads_df.columns):
                                    approved_check = dum_ads_df[dum_ads_df["Status"] == "Approved"]
                                    approved_check = approved_check[
                                        (approved_check["Employee Name"] == emp_name) | 
                                        (approved_check["Employee to Swap"] == emp_name)
                                    ]
                                else:
                                    approved_check = pd.DataFrame()
                                
                                if approved_check.empty:  # Go to form only if NOT in approved requests
                                    st.session_state["preselect_interested_employee"] = f"{row['Employee Id']} - {row['Employee Name']}"
                                    st.session_state["active_page"] = "Employee Transfer Form"  
                                    st.rerun()
                                else:
                                    warning_placeholder.warning(f"⚠️ The employee {row['Employee Name']} is already involved in an approved transfer request.")
                                    

                                    
                            st.markdown("<hr style='margin-top:1px; margin-bottom:5px; border:0; solid #d3d3d3;'>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ No employees found for the selected filters.")


# --- Tab 3: Transfer Requests ---
elif st.session_state["active_page"] == "Transfer Requests":

    # --- Sidebar: Logo & Company Name ---
    st.sidebar.markdown(
        """
        <div style='text-align: left; margin-left: 43px;'>
            <img src="https://upload.wikimedia.org/wikipedia/en/0/0c/Mu_Sigma_Logo.jpg" width="100">
        </div>
        """,
        unsafe_allow_html=True
    )
    
    top_managers = [
        "Nivedhan Narasimhan",
        "Rajdeep Roy Choudhury",
        "Riyas Mohammed Abdul Razak",
        "Sabyasachi Mondal",
        "Satyananda Palui",
        "Shilpa P Bhat",
        "Siddharth Chhottray",
        "Tanmay Sengupta",
        "Samanvitha A Bhagavath",
        "Aviral Bhargava"
    ]
    
    designation = [
        "TDS1",
        "TDS2",
        "TDS3",
        "TDS4",
        "-"
    ]
    
    # --- Sidebar Filters ---
    st.sidebar.markdown("<br><br>",unsafe_allow_html = True)
    st.sidebar.markdown("<br><br>",unsafe_allow_html = True)
    st.sidebar.header("⚙️ Filters")
    account_filter = st.sidebar.multiselect("Account Name", options=merged_df["Account Name"].dropna().unique())
    manager_filter = st.sidebar.multiselect(
        "Manager Name",
        options=[mgr for mgr in merged_df["Manager Name"].dropna().unique() if mgr in top_managers]
    )
    designation_filter = st.sidebar.multiselect(
        "Designation",
        options=[d for d in merged_df["Designation"].dropna().unique() if d in designation]
    )
    st.sidebar.markdown("<br><br>",unsafe_allow_html = True)
    st.sidebar.header("🔎 Search")
    resource_search = st.sidebar.text_input("Search Employee Name or ID",placeholder = "Employe ID/Name")
    st.subheader("🔁 Transfer Requests")
    
    swap_df = ads_df.copy()

    if "Status" not in swap_df.columns:
        swap_df["Status"] = "Pending"
    else:
        swap_df["Status"] = swap_df["Status"].fillna("Pending")

    # --- Filters ---
    col1, col2 = st.columns([2, 2])
    with col1:
        interested_manager_search = st.selectbox(
            "Search by Interested Manager",
            options=swap_df["Manager Name"].dropna().unique().tolist(),
            key="interested_manager_search_box",
            index = None
        )
    with col2:
        status_filter = st.selectbox(
            "Filter by Status",
            options=["All", "Pending", "Approved", "Rejected"],
            key="status_filter_box"
        )
    if interested_manager_search and "Interested Manager" in swap_df.columns:
        swap_df = swap_df[
            swap_df["Interested Manager"].str.contains(interested_manager_search, case=False, na=False)
        ]
    if status_filter != "All" and "Status" in swap_df.columns:
        swap_df = swap_df[swap_df["Status"] == status_filter]

    st.markdown("<hr style='margin-top:5px; margin-bottom:2px; border:0; solid #d3d3d3;'>", unsafe_allow_html=True)

    # --- Approve/Reject Form ---
    pending_swap_df_filtered = swap_df[swap_df["Status"] == "Pending"]
    col1, col4, col2, col3= st.columns([2,0.2, 1, 2])
    
    with col1:
        request_id_options = pending_swap_df_filtered["Request Id"].dropna().unique().astype(int).tolist() if not pending_swap_df_filtered.empty else []
        request_id_select = st.selectbox(
            "Select Request ID",
            options=request_id_options,
            key="request_id_select_tab2",
            index = None
        )
    with col4:
        pass
    with col2:
        decision = st.radio(
            "Action",
            options=["Approve", "Reject"],
            horizontal=True,
            key="decision_radio"
        )
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        submit_clicked = st.button("Submit", key="submit_decision")

    msg_placeholder = st.empty()
    if submit_clicked:
        if request_id_select not in pending_swap_df_filtered["Request Id"].values:
            msg_placeholder.warning("⚠️ Please select a valid pending Request ID.")
        else:
            current_status = ads_df.loc[ads_df["Request Id"] == request_id_select, "Status"].values[0]
            if current_status == "Approved" and decision == "Reject":
                msg_placeholder.error(f"❌ Request ID {request_id_select} is already Approved and cannot be Rejected.")
            else:
                try:
                    status_value = "Approved" if decision == "Approve" else "Rejected"
                    
                    # Update the selected request
                    ads_df.loc[ads_df["Request Id"] == request_id_select, "Status"] = status_value
    
                    # If approved, reject all other pending requests for the same Employee or Swap Employee
                    if status_value == "Approved":
                        approved_row = ads_df[ads_df["Request Id"] == request_id_select].iloc[0]
                        emp_id = approved_row["Employee Id"]
                        swap_emp_name = approved_row["Employee to Swap"]
    
                        # Reject other pending requests for the same Employee
                        ads_df.loc[
                            (ads_df["Employee Id"] == emp_id) & 
                            (ads_df["Request Id"] != request_id_select) &
                            (ads_df["Status"] == "Pending"),
                            "Status"
                        ] = "Rejected"
    
                        # Reject other pending requests for the same Swap Employee
                        ads_df.loc[
                            (ads_df["Employee to Swap"] == swap_emp_name) &
                            (ads_df["Request Id"] != request_id_select) &
                            (ads_df["Status"] == "Pending"),
                            "Status"
                        ] = "Rejected"
    
                    # Save updates to Google Sheet
                    set_with_dataframe(ads_sheet, ads_df, include_index=False, resize=True)
                    msg_placeholder.success(f"✅ Request ID {request_id_select} marked as {status_value}, related pending requests updated accordingly.")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    msg_placeholder.error(f"❌ Error updating request: {e}")

    # --- Status Table ---
    def color_status(val):
        if val == "Approved":
            return "color: green; font-weight: bold;"
        elif val == "Rejected":
            return "color: red; font-weight: bold;"
        else:
            return "color: orange; font-weight: bold;"

    swap_columns = ["Request Id", "Employee Id", "Employee Name", "Manager Name","Account Name", "Designation", 
                    "Interested Manager", "Employee to Swap", "Status"]
    swap_columns = [col for col in swap_columns if col in swap_df.columns]

    swap_df_filtered = swap_df[swap_df["Request Id"].notna()] if "Request Id" in swap_df.columns else pd.DataFrame()
    
    if account_filter:
        swap_df_filtered = swap_df_filtered[swap_df_filtered["Account Name"].isin(account_filter)]
    if manager_filter:
        swap_df_filtered = swap_df_filtered[swap_df_filtered["Manager Name"].isin(manager_filter)]
    if designation_filter:
        swap_df_filtered = swap_df_filtered[swap_df_filtered["Designation"].isin(designation_filter)]
    if resource_search:
        swap_df_filtered = swap_df_filtered[
            swap_df_filtered["Employee Name"].str.contains(resource_search, case=False, na=False) |
            swap_df_filtered["Employee Id"].astype(str).str.contains(resource_search, na=False)
        ]

    # Ensure empty table still has columns
    if swap_df_filtered.empty:
        swap_df_filtered = pd.DataFrame(columns=swap_columns)
    # Convert Request Id to int if column exists
    if "Request Id" in swap_df_filtered.columns and not swap_df_filtered.empty:
        swap_df_filtered["Request Id"] = swap_df_filtered["Request Id"].astype(int)
    # Display the table
    styled_swap_df = swap_df_filtered[swap_columns].style.applymap(color_status, subset=["Status"])
    st.dataframe(styled_swap_df, use_container_width=True, hide_index=True)

elif st.session_state["active_page"] == "Employee Transfer Form":
     # --- Sidebar: Logo & Company Name ---
    st.sidebar.markdown(
        """
        <div style='text-align: left; margin-left: 43px;'>
            <img src="https://upload.wikimedia.org/wikipedia/en/0/0c/Mu_Sigma_Logo.jpg" width="100">
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🔄 Employee Transfer Request")

    # --- Compute approved requests ---
    approved_requests = ads_df[ads_df["Status"] == "Approved"]
    approved_interested = approved_requests["Employee Id"].astype(str).tolist()
    approved_swap = approved_requests["Employee to Swap"].tolist()

    # --- Base available employees (exclude unbilled/unallocated and ALs) ---
    available_employees = df[
        (~df["Employee Id"].astype(str).isin(approved_interested)) &
        (~df["Employee Name"].isin(approved_swap)) &
        (df["Current Billability"].isin(["PU - Person Unbilled", "-", "PI - Person Investment"])) &
        (~df["Designation"].isin(["AL"]))
    ].copy()
    
    options_interested = ["Select Interested Employee"] + (available_employees["Employee Id"].astype(str) + " - " + available_employees["Employee Name"]).tolist()
    # Create options for swap, removing the preselected employee
    options_swap = ["Select Employee to Swap"] + (available_employees["Employee Id"].astype(str) + " - " + available_employees["Employee Name"]).tolist()
       
    # Pre-fill if selected from Tab 1
    preselected = st.session_state.get("preselect_interested_employee", None)
    default_idx = options_interested.index(preselected) if preselected in options_interested else 0

    # --- Handle session state for dropdowns ---
    if "interested_employee_add" not in st.session_state:
        st.session_state["interested_employee_add"] = preselected if preselected else "Select Interested Employee"
    if "employee_to_swap_add" not in st.session_state:
        st.session_state["employee_to_swap_add"] = "Select Employee to Swap"   

    # --- Dropdowns ---
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
            options=["Select Interested Employee"] + (available_employees["Employee Id"].astype(str) + " - " + available_employees["Employee Name"]).dropna().tolist(),
            key="interested_employee_add",
            index = default_idx
        )
    with col3:
        employee_to_swap_add = st.selectbox(
            "Employee to Transfer",
            options=["Select Employee to Swap"] + (available_employees["Employee Id"].astype(str) + " - " + available_employees["Employee Name"]).dropna().tolist(),
            key="employee_to_swap_add"
        )

    # Remove session_state preselection after use
    if "preselect_interested_employee" in st.session_state:
        del st.session_state["preselect_interested_employee"]

    # --- Submit Transfer Request ---
    if st.button("Submit Transfer Request", key="submit_add"):
        if (user_name_add == "Select Your Name" or 
            interested_employee_add == "Select Interested Employee" or 
            employee_to_swap_add == "Select Employee to Swap"):
            st.warning("⚠️ Please fill all fields before submitting.")
        else:
            try:
                interested_emp_id = interested_employee_add.split(" - ")[0]
                swap_emp_id = employee_to_swap_add.split(" - ")[0]
                swap_emp_name = df[df["Employee Id"].astype(str) == swap_emp_id]["Employee Name"].values[0]

                if user_name_add in df["Employee Name"].values:
                    user_id = df.loc[df["Employee Name"] == user_name_add, "Employee Id"].values[0]
                else:
                    hash_val = int(hashlib.sha256(user_name_add.encode()).hexdigest(), 16)
                    user_id = str(hash_val % 9000 + 1000)

                # Check if request already exists
                existing_request = ads_df[
                    (ads_df["Employee Id"].astype(str) == interested_emp_id) &
                    (ads_df["Interested Manager"] == user_name_add) &
                    (ads_df["Employee to Swap"] == swap_emp_name)
                ]

                if not existing_request.empty:
                    st.warning(f"⚠️ Transfer request for Employee ID {interested_emp_id} with this combination already exists!")
                else:
                    employee_row = df[df["Employee Id"].astype(str) == interested_emp_id].copy()
                    employee_row["Interested Manager"] = user_name_add
                    employee_row["Employee to Swap"] = swap_emp_name
                    employee_row["Status"] = "Pending"

                    request_id = f"{user_id}{interested_emp_id}{swap_emp_id}"
                    employee_row["Request Id"] = int(request_id)

                    ads_df = pd.concat([ads_df, employee_row], ignore_index=True)
                    ads_df = ads_df.drop_duplicates(subset=["Employee Id","Interested Manager","Employee to Swap"], keep="last")

                    set_with_dataframe(ads_sheet, ads_df)

                    # Preselect this employee on rerun
                    st.session_state["preselect_interested_employee"] = f"{interested_emp_id} - {interested_employee_add.split(' - ')[1]}"

                    st.success(f"✅ Transfer request added for Employee ID {interested_emp_id}. The Request ID is {request_id}")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    # --- Remove Transfer Request ---
    st.markdown("<hr style='margin-top:20px; margin-bottom:5px; border:0; solid #d3d3d3;'>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
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

    st.markdown(
        "<p style='margin-top:15px; color:#b0b0b0; font-size:14px; font-style:italic;'>"
        "Note: Sidebar filters do not apply for this view."
        "</p>",
        unsafe_allow_html=True
    )

