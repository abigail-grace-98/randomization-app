import streamlit as st
import pandas as pd
import datetime
import shutil
import os
import gspread
from google.oauth2.service_account import Credentials

# Load credentials and Google Sheet
creds_dict = st.secrets["gcp_service_account"]
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)

client = gspread.authorize(credentials)
sheet = client.open_by_key(st.secrets["settings"]["spreadsheet_id"])

# Load worksheets
template_ws = sheet.worksheet("randomization")
log_ws = sheet.worksheet("log")

# Load allocation table
template_data = template_ws.get_all_records()
df = pd.DataFrame(template_data)

# Clean ID function
def clean_id(val):
    try:
        return str(int(float(val))).strip()
    except:
        return str(val).strip()

df['redcap_id'] = df['redcap_id'].apply(clean_id)
df['assigned'] = df['assigned'].apply(lambda x: x == 'TRUE' or x == True)

st.title("📋 Randomization Tool")

study_id_input = st.text_input("Enter Study ID:")
insurance_status = st.selectbox("Select Insurance Status:", ["Insured", "Uninsured"])

# Normalize stratum value
insurance_status = insurance_status.lower()

if st.button("🎯 Assign Group"):
    study_id = clean_id(study_id_input)

    if study_id in df['redcap_id'].values:
        # Already assigned
        assigned_row = df[df['redcap_id'] == study_id]
        assigned_group = "Control" if assigned_row['group'].values[0] == 1 else "Intervention"
        st.warning(f"⚠️ Study ID {study_id} has already been assigned to: **{assigned_group}**")
    else:
        # Look for available slot
        available = df[(df['assigned'] == False) & (df['stratum'] == insurance_status)]

        if not available.empty:
            row_idx = available.index[0]
            group_value = df.loc[row_idx, 'group']
            assigned_group = "Control" if group_value == 1 else "Intervention"

            # Update local DataFrame
            df.at[row_idx, 'assigned'] = True
            df.at[row_idx, 'redcap_id'] = study_id

            # Overwrite the Google Sheet with updated df
            updated_data = df.values.tolist()
            header = df.columns.tolist()
            template_ws.update([header] + updated_data)

            # Log assignment
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_ws.append_row([timestamp, study_id, insurance_status, assigned_group])

            # Confirmation
            st.success(f"✅ Study ID {study_id} assigned to: **{assigned_group}**")
            st.info(f"🕒 Logged assignment at {timestamp}")
        else:
            st.error("❌ No more available slots for this insurance status!")
