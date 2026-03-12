import pandas as pd
import datetime

# --- CONFIGURATION ---
# Change this to the exact name of your legacy excel file
input_excel = "P2913_Survey DPR_V02.xlsx" 
output_csv = "migration_preview.csv"

print(f"Loading {input_excel}...")
# We use header=1 to skip the "SURVEY DPR REGISTER" title row
df = pd.read_excel(input_excel, sheet_name='Master', header=1)
df = df.fillna('')

output_data = []

for index, row in df.iterrows():
    if not str(row.get('From Date', '')) and not str(row.get('Description of Survey Daily activities', '')):
        continue
        
    date_val = row.get('From Date', '')
    if pd.api.types.is_datetime64_any_dtype(date_val):
        start_date = date_val
    else:
        try: start_date = pd.to_datetime(date_val)
        except: start_date = datetime.datetime.utcnow()

    req = str(row.get('Requestor', '')).strip()
    pic = str(row.get('PIC / Assigned to', '')).strip()
    person_inv = str(row.get('Person Involve', '')).strip()
    assigned = pic if pic else person_inv
    
    act_type = str(row.get('Activity Type', '')).strip()
    disc = str(row.get('Discipline', '')).strip()
    desc = str(row.get('Description of Survey Daily activities', '')).strip()
    
    remarks1 = str(row.get('Detail Data / Condition', '')).strip()
    remarks2 = str(row.get('Remarks', '')).strip()
    store_in = str(row.get('Store in', '')).strip()
    
    safe_scope = (desc[:95] + '...') if len(desc) > 95 else desc
    if not safe_scope: safe_scope = "Historical_Task"
    
    full_remarks = []
    if desc and len(desc) > 95: full_remarks.append(f"Full Description: {desc}")
    if remarks1: full_remarks.append(f"Details: {remarks1}")
    if remarks2: full_remarks.append(f"Remarks: {remarks2}")
    if store_in: full_remarks.append(f"Legacy Path: {store_in}")
    combined_remarks = " | ".join(full_remarks)

    year_month = start_date.strftime('%Y_%m') if pd.notnull(start_date) else 'Unknown_Date'

    output_data.append({
        'start_time': start_date.strftime('%Y-%m-%d') if pd.notnull(start_date) else '',
        'end_time': start_date.strftime('%Y-%m-%d') if pd.notnull(start_date) else '',
        'status': 'Closed',
        'requestor': req[:100],
        'assigned_to': assigned[:100],
        'task_category': act_type[:100],
        'action_required': disc[:100],
        'instrument': 'Legacy_Data',
        'area': '900_Legacy_Data',
        'location': 'DPR_Import',
        'sub_location': year_month,
        'work_scope': safe_scope,
        'remarks': combined_remarks,
        'surveyor_name': 'Legacy_Import'
    })

# Export to CSV
out_df = pd.DataFrame(output_data)
out_df.to_csv(output_csv, index=False)
print(f"Success! {len(out_df)} rows mapped and saved to {output_csv}. You can now open it in Excel to review!")