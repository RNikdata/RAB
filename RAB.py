import streamlit as st
import pandas as pd
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
    ads_df = pd.DataFrame(columns=["Employee Id", "Interested Manager", "Employee to Swap", "Request Id"])

# --- Merge DataFrames ---
merged_df = df.merge(
    ads_df[["Employee Id", "Interested Manager", "Employee to Swap", "Request Id"]],
    on="Employee Id",
    how="left"
)

# --- Sidebar Filters ---
st.sidebar.header("⚙️ Filters")
account_filter = st.sidebar.multiselect("Account Name", options=merged_df["Account Name"].dropna().unique())
billability_filter = st.sidebar.multiselect("Billable Status", options=merged_df["Billable Status"].dropna().unique())
tag_filter = st.sidebar.multiselect("Tag", options=merged_df["Tag"].dropna().unique()) if "Tag" in merged_df.columns else []

st.sidebar.header("🔎 Search")
resource_search = st.sidebar.text_input("Search Employee Name or ID")

# --- Main Heading ---
st.markdown("<h2 style='text-align:center'>📊 Resource Allocation Board</h2>", unsafe_allow_html=True)

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["📋 Resource Table", "🔄 Swap Requests", "✏️ Employee Swap Form"])

# --- Tab 1: Resource Table ---
with tab1:
    st.subheader("📋 Resource Table")
    filtered_df = merged_df.copy()

    # Apply filters
    if account_filter:
        filtered_df = filtered_df[filtered_df["Account Name"].isin(account_filter)]
    if billability_filter:
        filtered_df = filtered_df[filtered_df["Billable Status"].isin(billability_filter)]
    if tag_filter:
        filtered_df = filtered_df[filtered_df["Tag"].isin(tag_filter)]
    if resource_search:
        filtered_df = filtered_df[
            filtered_df["Employee Name"].str.contains(resource_search, case=False, na=False) |
            filtered_df["Employee Id"].astype(str).str.contains(resource_search, na=False)
        ]

    filtered_df_unique = filtered_df.drop_duplicates(subset=["Employee Id"], keep="first")

    # --- KPIs ---
    total_employees = filtered_df_unique["Employee Id"].nunique()
    total_unbilled = filtered_df_unique[filtered_df_unique["Billable Status"]=="Unbilled"]["Employee Id"].nunique()
    total_unallocated = filtered_df_unique[filtered_df_unique["Tag"]=="Unallocated"]["Employee Id"].nunique() if "Tag" in filtered_df_unique.columns else 0
    total_snps = filtered_df_unique[filtered_df_unique["SNP"]==1]["Employee Id"].nunique() if "Tag" in filtered_df_unique.columns else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Employees", total_employees)
    col2.metric("Total Billed", total_billed)
    col3.metric("Total Unallocated", total_unallocated)
    col4.metric("Total SNPs", total_snps)

    # Display table
    columns_to_show = ["Employee Id", "Employee Name", "Email", "Designation",
                       "Manager Name", "Account Name", "Current Billability"]
    columns_to_show = [col for col in columns_to_show if col in filtered_df_unique.columns]
    st.dataframe(filtered_df_unique[columns_to_show], use_container_width=True)

# --- Tab 2: Swap Requests ---
with tab2:
    st.subheader("🔎 Swap Requests")
    swap_df = ads_df.copy()

    if resource_search:
        swap_df = swap_df[
            swap_df["Employee Id"].astype(str).str.contains(resource_search, na=False) |
            swap_df["Employee to Swap"].str.contains(resource_search, case=False, na=False)
        ]

    interested_manager_search = st.text_input("Search by Interested Manager", key="manager_search")
    if interested_manager_search:
        swap_df = swap_df[swap_df["Interested Manager"].str.contains(interested_manager_search, case=False, na=False)]

    st.dataframe(swap_df, use_container_width=True)

# --- Tab 3: Employee Swap Form ---
with tab3:
    st.subheader("✏️ Employee Swap Form")

    col1, col2, col3 = st.columns([1,2,2])
    with col1:
        user_name_add = st.selectbox("User Name (Add)", options=["Select an Option"] + df["Employee Name"].tolist())
    with col2:
        interested_employee_add = st.selectbox("Interested Employee (Add)", options=["Select an Option"] + (df["Employee Id"].astype(str) + " - " + df["Employee Name"]).tolist())
    with col3:
        employee_to_swap_add = st.selectbox("Employee to Swap (Add)", options=["Select an Option"] + (df["Employee Id"].astype(str) + " - " + df["Employee Name"]).tolist())

    if st.button("Submit Swap Request"):
        if "Select an Option" in [user_name_add, interested_employee_add, employee_to_swap_add]:
            st.warning("⚠️ Please fill all fields before submitting.")
        else:
            try:
                interested_emp_id = interested_employee_add.split(" - ")[0]
                user_id = df[df["Employee Name"]==user_name_add]["Employee Id"].values[0]
                swap_emp_id = employee_to_swap_add.split(" - ")[0]
                swap_emp_name = df[df["Employee Id"].astype(str)==swap_emp_id]["Employee Name"].values[0]

                employee_row = df[df["Employee Id"].astype(str)==interested_emp_id].copy()
                employee_row["Interested Manager"] = user_name_add
                employee_row["Employee to Swap"] = swap_emp_name
                request_id = f"{str(user_id)[-4:]}{str(interested_emp_id)[-4:]}{str(swap_emp_id)[-4:]}"
                employee_row["Request Id"] = request_id

                ads_df = pd.concat([ads_df, employee_row], ignore_index=True)
                ads_df = ads_df.drop_duplicates(subset=["Employee Id","Interested Manager","Employee to Swap","Request Id"], keep="last")

                # Save back to Google Sheet
                ads_sheet.clear()
                set_with_dataframe(ads_sheet, ads_df)

                st.success(f"✅ Swap request added. Request ID: {request_id}")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("---")
    st.subheader("❌ Remove Employee Swap Request")
    request_id_remove = st.selectbox("Select Request ID to Remove", options=ads_df["Request Id"].dropna().tolist())

    if st.button("Remove Swap Request"):
        if request_id_remove not in ads_df["Request Id"].values:
            st.error("❌ Request ID not found.")
        else:
            ads_df = ads_df[ads_df["Request Id"] != request_id_remove]
            ads_sheet.clear()
            set_with_dataframe(ads_sheet, ads_df)
            st.success(f"✅ Swap request with Request ID {request_id_remove} removed.")
            st.experimental_rerun()
