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
    ads_df[["Employee Id", "Interested Manager", "Employee to Swap", "Request Id"]] if not ads_df.empty else pd.DataFrame(),
    on="Employee Id",
    how="left"
)

# --- Sidebar Filters ---
st.sidebar.markdown("<br><br>",unsafe_allow_html = True)
st.sidebar.markdown("<br><br>",unsafe_allow_html = True)
st.sidebar.header("⚙️ Filters")
account_filter = st.sidebar.multiselect("Account Name", options=merged_df["Account Name"].dropna().unique())
billability_filter = st.sidebar.multiselect("Billable Status", options=merged_df["Billable Status"].dropna().unique())
tag_filter = st.sidebar.multiselect("Tag", options=merged_df["Tag"].dropna().unique()) if "Tag" in merged_df.columns else []
st.sidebar.markdown("<br><br>",unsafe_allow_html = True)
st.sidebar.header("🔎 Search")
resource_search = st.sidebar.text_input("Search Employee Name or ID")

# --- Main Heading ---
st.markdown("<h1 style='text-align:center'>🧑‍💼 Resource Allocation Board</h2>", unsafe_allow_html=True)

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["📋 Employee Table", "🔄 Swap Requests", "✏️ Employee Swap Form"])

# --- Tab 1: Employee Table & KPIs ---
with tab1:
    st.subheader("📋 Employee Table")
    filtered_df = merged_df.copy()

    # Apply filters
    if account_filter:
        filtered_df = filtered_df[filtered_df["Account Name"].isin(account_filter)]
    if billability_filter:
        filtered_df = filtered_df[filtered_df["Billable Status"].isin(billability_filter)]
    if tag_filter and "Tag" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Tag"].isin(tag_filter)]
    if resource_search:
        filtered_df = filtered_df[
            filtered_df["Employee Name"].str.contains(resource_search, case=False, na=False) |
            filtered_df["Employee Id"].astype(str).str.contains(resource_search, na=False)
        ]

    filtered_df_unique = filtered_df.drop_duplicates(subset=["Employee Id"], keep="first")

    # --- KPI Metrics ---
    total_employees = filtered_df_unique["Employee Id"].nunique()
    total_unbilled = filtered_df_unique[filtered_df_unique["Billable Status"]=="Unbilled"]["Employee Id"].nunique()
    total_unallocated = filtered_df_unique[filtered_df_unique["Tag"]=="Unallocated"]["Employee Id"].nunique() if "Tag" in filtered_df_unique.columns else 0
    total_snps = filtered_df_unique[filtered_df_unique["SNP"]==1]["Employee Id"].nunique() if "SNP" in filtered_df_unique.columns else 0

    # --- KPI Cards Styling ---
    kpi_style = """
    <style>
    .kpi-container { display: flex; gap: 20px; margin-bottom: 20px; flex-wrap: wrap; }
    .kpi-card { flex: 1; background: #B0C4DE; border-radius: 10px; padding: 10px; text-align: center;
                box-shadow: 2px 2px 8px rgba(0,0,0,0.1); min-width: 150px; }
    .kpi-card h3 { margin: 0; font-size: 18px; color: black; }
    .kpi-card p { margin: 5px 0 0 0; font-size: 24px; font-weight: bold; color: black; }
    </style>
    """
    st.markdown(kpi_style, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <h3>Total Employees</h3>
            <p>{total_employees}</p>
        </div>
        <div class="kpi-card">
            <h3>Total Unbilled</h3>
            <p>{total_unbilled}</p>
        </div>
        <div class="kpi-card">
            <h3>Total Unallocated</h3>
            <p>{total_unallocated}</p>
        </div>
        <div class="kpi-card">
            <h3>Total SNPs</h3>
            <p>{total_snps}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Display table
    columns_to_show = ["Employee Id", "Employee Name", "Email", "Designation",
                       "Manager Name", "Account Name", "Current Billability"]
    columns_to_show = [col for col in columns_to_show if col in filtered_df_unique.columns]
    st.dataframe(filtered_df_unique[columns_to_show], use_container_width=True, height=500, hide_index=True)
    
# --- Tab 2: Swap Requests ---
with tab2:
    st.markdown("<br><br>",unsafe_allow_html = True)
    st.subheader("🔄 Swap Requests")
    swap_df = ads_df.copy()

    # Search by Employee Name or ID
    if resource_search and "Employee Name" in swap_df.columns:
        swap_df = swap_df[
            swap_df["Employee Name"].str.contains(resource_search, case=False, na=False) |
            swap_df["Employee Id"].astype(str).str.contains(resource_search, na=False)
        ]

    # Search by Interested Manager
    interested_manager_search = st.text_input(
        "Search by Interested Manager",
        key="interested_manager_search_box"
    )
    if interested_manager_search and "Interested Manager" in swap_df.columns:
        swap_df = swap_df[
            swap_df["Interested Manager"].str.contains(interested_manager_search, case=False, na=False)
        ]

    # Define columns to show
    swap_columns = ["Request Id", "Employee Id", "Employee Name", "Email", "Interested Manager", "Employee to Swap"]
    swap_columns = [col for col in swap_columns if col in swap_df.columns]

    # Filter only rows with Request Id
    swap_df_filtered = swap_df[swap_df["Request Id"].notna()] if "Request Id" in swap_df.columns else pd.DataFrame()

    # Display table
    st.dataframe(swap_df_filtered[swap_columns], use_container_width=True, hide_index=True)

# --- Tab 3: Employee Swap Form ---
with tab3:
    st.markdown("<br><br>",unsafe_allow_html = True)
    st.subheader("🔄 Employee Swap Request")

    # --- Add Swap Request ---
    col1, col2, col3 = st.columns([1, 2, 2])
    with col1:
        user_name_add = st.selectbox(
            "User Name (Add)",
            options=["Select an Option"] + df["Employee Name"].tolist(),
            key="user_name_add"
        )
    with col2:
        interested_employee_add = st.selectbox(
            "Interested Employee (Add)",
            options=["Select an Option"] + (df["Employee Id"].astype(str) + " - " + df["Employee Name"]).tolist(),
            key="interested_employee_add"
        )
    with col3:
        employee_to_swap_add = st.selectbox(
            "Employee to Swap (Add)",
            options = ["Select an Option"] + (df["Employee Id"].astype(str) + " - " + df["Employee Name"]).tolist(),
            key="employee_to_swap_add"
        )

    if st.button("Submit Swap Request", key="submit_add"):
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

                # Generate unique request id
                request_id = f"{user_id}{interested_emp_id}{swap_emp_id}"
                employee_row["Request Id"] = int(request_id)

                ads_df = pd.concat([ads_df, employee_row], ignore_index=True)
                ads_df = ads_df.drop_duplicates(subset=["Employee Id","Interested Manager","Employee to Swap"], keep="last")

                # Update Google Sheet
                set_with_dataframe(ads_sheet, ads_df)

                st.success(f"✅ Swap request added for Employee ID {interested_emp_id}. The Request ID is {request_id}")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("❌ Remove Employee Swap Request")

    request_id_remove = st.selectbox(
        "Enter Request ID to Remove",
        options = ads_df["Request Id"].dropna().astype(int).tolist(),
        key="request_id_remove"
    )

    if st.button("Remove Swap Request", key="submit_remove"):
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
