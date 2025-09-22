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
    total_billed = filtered_df_unique[filtered_df_unique["Billable Status"]=="Billed"]["Employee Id"].nunique()
    total_unallocated = filtered_df_unique[filtered_df_unique["Tag"]=="Unallocated"]["Employee Id"].nunique() if "Tag" in filtered_df_unique.columns else 0
    total_snps = filtered_df_unique[filtered_df_unique["Tag"]=="SNP"]["Employee Id"].nunique() if "Tag" in filtered_df_unique.columns else 0

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
