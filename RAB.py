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
import base64
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

# Define the data
data = {
    "Account": [
        "Bristol-Myers Squibb",
        "J&J",
        "AbbVie",
        "Gilead Sciences  Inc.",
        "Recursion",
        "Novartis",
        "Sanofi",
        "Abbott Laboratories",
        "Loyalty Pacific",
        "Coles"
    ],
    "Delivery Owner": [
        "Riddhi J Katira",
        "Sana Aram",
        "Aneesha Bijju",
        "Aviral Tiwari",
        "Saaketh Ram",
        "Satyananda Palui",
        "Satyananda Palui",
        "Satyananda Palui",
        "Aviral Bhargava",
        "Aviral Bhargava"
    ],
    "P&L Owner Mapping": [
        "Shilpa P Bhat",
        "Rajdeep Roy Choudhury",
        "Nivedhan Narasimhan",
        "Nivedhan Narasimhan",
        "Nivedhan Narasimhan",
        "Shilpa P Bhat",
        "Tanmay Sengupta",
        "Tanmay Sengupta",
        "Shilpa P Bhat",
        "Shilpa P Bhat"
    ]
}
account_df = pd.DataFrame(data)

df = df.merge(
    account_df, 
    how="left",                     # keep all rows from df
    left_on="Account Name",         # column in df
    right_on="Account"              # column in account_df
)

# Drop duplicate Account column from account_df if needed
df = df.drop(columns=["Account"])


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
API_USERNAME = "streamlit_user"
API_PASSWORD = "streamlitadmin@mu-sigma25"
BASE_URL = "https://muerp.mu-sigma.com/dmsRest/getEmployeeImage"

DEFAULT_IMAGE_URL = "https://static.vecteezy.com/system/resources/previews/008/442/086/original/illustration-of-human-icon-user-symbol-icon-modern-design-on-blank-background-free-vector.jpg"
headers = {
    "userid": API_USERNAME, 
    "password": API_PASSWORD
}

@st.cache_data
def fetch_employee_url(emp_id):
    """
    Fetch employee image from API and return a PIL Image object.
    """
    try:
        response = requests.get(BASE_URL, headers=headers, params={"id": emp_id}, timeout=10)
        print(f"Response status for {emp_id}: {response.status_code}")
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))

        else:
            # Fallback to default image from URL
            response = requests.get(DEFAULT_IMAGE_URL)
            img = Image.open(BytesIO(response.content))
            
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{img_base64}"
    
    except Exception as e:
        return DEFAULT_IMAGE_URL
        
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

    # Sidebar Filters
    st.sidebar.header("⚙️ Filters")
    account_filter = st.sidebar.multiselect("Account Name", options=merged_df["Account Name"].dropna().unique())
    delivery_filter = st.sidebar.multiselect("Delivery Owner", options=merged_df["Delivery Owner"].dropna().unique())
    pl_filter = st.sidebar.multiselect("P&L Owner", options=merged_df["P&L Owner Mapping"].dropna().unique())
    
    st.sidebar.header("🔎 Search")
    resource_search = st.sidebar.text_input("Search Employee Name or ID", placeholder="Employee ID/Name")

    st.subheader("📊 Transfer Summary")
    st.markdown("<br>", unsafe_allow_html=True)

    # --- Copy dataframes ---
    employee_df = df.copy()
    request_df = ads_df.copy()

    # --- Filter employees ---
    employee_df = employee_df.drop_duplicates(subset=["Employee Id"], keep="first")
    employee_df = employee_df[~employee_df["Designation"].isin(["AL"])]

    # Current Billability filter
    billable_df = employee_df[
        employee_df["Current Billability"].isin(["PU - Person Unbilled", "-", "PI - Person Investment"])
    ]

    # Tenure filter
    employee_df["Tenure"] = pd.to_numeric(employee_df["Tenure"], errors='coerce')
    tenure_df = employee_df[employee_df["Tenure"] > 35.9]

    # Combine filters
    employee_df = pd.concat([billable_df, tenure_df], ignore_index=True)
    employee_df = employee_df.drop_duplicates(subset=["Employee Id"], keep="first")

    # --- Ensure Status column exists in requests ---
    request_df["Status"] = request_df["Status"].fillna("Pending")

    # --- Merge employee info with requests ---
    merged_summary = employee_df.merge(
        request_df[['Employee Id', 'Request Id', 'Status']],
        on='Employee Id',
        how='left'
    )
    st.write(merged_summary.columns.tolist())

    # Strip spaces in column names to avoid KeyError
    merged_summary.columns = merged_summary.columns.str.strip()

    # --- Group by Account + Delivery Owner + P&L Owner Mapping ---
    grouped_summary = merged_summary.groupby(
        ["Account", "Delivery Owner", "P&L Owner Mapping"], as_index=False
    ).agg(
        Total_Employees=pd.NamedAgg(column="Employee Id", aggfunc=lambda x: x.dropna().nunique()),
        Total_Requests_Raised=pd.NamedAgg(column="Request Id", aggfunc=lambda x: x.dropna().nunique()),
        Total_Approved=pd.NamedAgg(column="Status", aggfunc=lambda x: (x == "Approved").sum()),
        Total_Rejected=pd.NamedAgg(column="Status", aggfunc=lambda x: (x == "Rejected").sum()),
        Total_Pending=pd.NamedAgg(column="Status", aggfunc=lambda x: (x == "Pending").sum())
    )

    # --- Apply sidebar filters ---
    if account_filter:
        grouped_summary = grouped_summary[grouped_summary["Account"].isin(account_filter)]
    if delivery_filter:
        grouped_summary = grouped_summary[grouped_summary["Delivery Owner"].isin(delivery_filter)]
    if pl_filter:
        grouped_summary = grouped_summary[grouped_summary["P&L Owner Mapping"].isin(pl_filter)]

    # --- Optional: search by employee name ---
    if resource_search:
        resource_ids = employee_df[
            employee_df["Employee Name"].str.contains(resource_search, case=False, na=False) |
            employee_df["Employee Id"].astype(str).str.contains(resource_search, na=False)
        ]["Employee Id"].unique()
        grouped_summary = grouped_summary[
            merged_summary[merged_summary["Employee Id"].isin(resource_ids)]
            .groupby(["Account", "Delivery Owner", "P&L Owner Mapping"], as_index=False)
            .size().index
        ]

    # --- Display table ---
    st.dataframe(
        grouped_summary.sort_values(by=["Total_Requests_Raised", "Account"], ascending=[False, True]),
        use_container_width=True,
        hide_index=True,
        height=len(grouped_summary) * 40
    )

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
    unique_skills = [
        "muPDNA",
        "muOBI",
        "Pharma Regulatory Compliance",
        "SAS",
        "Python",
        "Power BI",
        "PowerApps",
        "Azure AI Document Intelligence",
        "Azure",
        "muUniverse",
        "muDSC",
        "Clinical Trials",
        "Qlik Sense",
        "Dataiku",
        "PySpark",
        "SQL",
        "Databricks",
        "Snowflake",
        "Streamlit",
        "Customer Loyalty",
        "Data Engineering",
        "HEOR",
        "Pharma Industry",
        "Demand Forecasting",
        "Sales and Operations Planning",
        "Statistics",
        "Machine Learning",
        "YAML",
        "Jupyter Notebook",
        "Git Concepts",
        "Bitbucket",
        "DevOps",
        "AWS",
        "Kubernetes",
        "ArgoWorkflows",
        "Helm",
        "Jenkins",
        "Jfrog",
        "Docker",
        "Confluence",
        "AWS Redshift",
        "AWS S3",
        "Postgres",
        "MS Excel",
        "Tableau",
        "R",
        "Node JS",
        "Angular JS",
        "React JS",
        "Polars",
        "Communication",
        "Medical Devices Industry",
        "Formulary Development",
        "MS Office",
        "Figma",
        "Bricks and PreFabs",
        "Supply Chain",
        "Knowledge Graphs",
        "Neural Networks",
        "Graph Neural Networks",
        "LLM",
        "Vector DB",
        "RAG",
        "JIRA",
        "Power Automate",
        "MS Sharepoint",
        "MS Powerpoint",
        "Kedro",
        "Dagster",
        "GitHub",
        "Site Selection",
        "Clustering",
        "UI/UX",
        "Cloud Computing",
        "Azure DevOps",
        "AWS EC2",
        "AWS EMR",
        "AWS EKS",
        "Oracle DB",
        "AWS IAM",
        "Spotfire",
        "PyDash",
        "HTML",
        "CSS",
        "Dash",
        "MLOps",
        "Financial Operations",
        "Manufacturing",
        "Azure Data Factory",
        "Power Platform",
        "Azure Blob Storage",
        "Qlikview",
        "MS OneNote",
        "Payments Industry",
        "Media Streaming Device Industry",
        "Probability and Discrete Mathematics",
        "Segmentation"
    ]
    
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
    
    skill_filter = st.sidebar.multiselect(
        "Skills",
        options=unique_skills,
        default=[]  # you can set a default selection if you want
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
    if skill_filter:
        # Convert to lowercase for case-insensitive matching
        selected_skills = [s.lower() for s in skill_filter]
    
        # Ensure "Skillset" column is string and handle nulls
        df_unique = df_unique[
            df_unique["Skillset"].fillna("").apply(
                lambda x: any(skill in x.lower() for skill in selected_skills)
            )
        ]
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
    filtered_df_unique2 = filtered_df_unique[filtered_df_unique["Tenure"] > 35.9]
    filtered_df_unique = pd.concat([filtered_df_unique1, filtered_df_unique2], ignore_index=True)
    filtered_df_unique = filtered_df_unique.drop_duplicates(subset=["Employee Id"], keep="first")
    filtered_df_unique["3+_yr_Tenure_Flag"] = filtered_df_unique["Tenure"].apply(lambda x: "Yes" if x > 3 else "No")
    filtered_df_unique = filtered_df_unique[filtered_df_unique["Final Manager"].notna()]
    filtered_df_unique["Skillset"] = filtered_df_unique["Skillset"].fillna("")
    # Add a new column "Image URL"
    # Ensure the URL column exists in the DataFrame that will be displayed
    
    columns_to_show = ["Manager Name", "Account Name", "Employee Id", "Employee Name", "Designation", "Rank","Final Manager","Skillset"]
    columns_to_show = [col for col in columns_to_show if col in filtered_df_unique.columns]

    # --- Display Employee Cards ---
    if not filtered_df_unique.empty:
        sorted_df = filtered_df_unique[columns_to_show].sort_values(by="Employee Name").reset_index(drop=True)
        n = len(sorted_df)
        # Placeholder for warnings and loading message
        warning_placeholder = st.empty()
        loading_placeholder = st.empty()

        with st.spinner("⏳ Loading employee details..."):
            for i in range(0, n, 2):
                cols = st.columns([1,1])
                for j, col in enumerate(cols):
                    if i + j < n:
                        row = sorted_df.iloc[i + j]
                        emp_id = row['Employee Id']
                        img = fetch_employee_url(emp_id) 
                        html_img_tag = f'<img src="{img}" style="width:110px; height:120px; border-radius:4px; object-fit:cover;">' # get PIL image or default URL
                        with col:
                            with st.container():
                                st.markdown(
                                    f"""
                                    <div style='display:flex; align-items:center; gap:15px; padding:8px; border:3px solid #c0c0c0; border-radius:8px; margin-bottom:5px;'>
                                        <div style='flex-shrink:0;'>
                                            {html_img_tag}
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
                                                <div style='margin-top:4px;'><b>👔 Manager:</b> {row['Final Manager']}</div>
                                                <div style='margin-top:4px;'><b>👨‍💻 Skillset:</b> {row['Skillset']}</div>
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
        loading_placeholder.empty()
        
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
                            ((ads_df["Employee Id"] == emp_id) | (ads_df["Employee to Swap"] == emp_id)) & 
                            (ads_df["Request Id"] != request_id_select) &
                            (ads_df["Status"] == "Pending"),
                            "Status"
                        ] = "Rejected"
    
                        # Reject other pending requests for the same Swap Employee
                        ads_df.loc[
                            ((ads_df["Employee to Swap"] == swap_emp_name) | (ads_df["Employee to Swap"] == swap_emp_name))  &
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
            options=["Select Employee to Swap"] + (df["Employee Id"].astype(str) + " - " + df["Employee Name"]).dropna().tolist(),
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

