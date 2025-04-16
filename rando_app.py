import streamlit as st
import pandas as pd
import datetime
import shutil
import os
import gspread
from google.oauth2.service_account import Credentials

# Load credentials from Streamlit secrets
creds_dict = st.secrets["gcp_service_account"]

# Create credentials object
credentials = Credentials.from_service_account_info(creds_dict)

# Connect to Google Sheets
client = gspread.authorize(credentials)
sheet = client.open_by_key("1Yxa3gzpbx2hGKHyTLduT5JxHJ9Rt3Ll-VqeM0aKOZKI")
worksheet = sheet.worksheet("randomization")

# Load allocation table
data = worksheet.get_all_records()
df = pd.DataFrame(data)

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

            # Assign in table
            df.at[row_idx, 'assigned'] = True
            df.at[row_idx, 'redcap_id'] = study_id

            # Backup allocation table
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_allocation_{timestamp}.csv"
            shutil.copy("RandomizationAllocationTable_1000 NEW SLOTS.csv", backup_filename)

            # Save updated allocation table
            df.to_csv("RandomizationAllocationTable_1000 NEW SLOTS.csv", index=False)

            # Log assignment
            log_data = {
                "study_id": [study_id],
                "insurance_status": [insurance_status],
                "group": [assigned_group],
                "timestamp": [timestamp]
            }

            log_df = pd.DataFrame(log_data)
            log_file = "randomization_log.csv"

            if os.path.exists(log_file):
                log_df.to_csv(log_file, mode='a', header=False, index=False)
            else:
                log_df.to_csv(log_file, index=False)

            # Confirmation
            st.success(f"✅ Study ID {study_id} assigned to: **{assigned_group}**")
            st.info(f"🕒 Logged and backed up at {timestamp}")
        else:
            st.error("❌ No more available slots for this insurance status!")
