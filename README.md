# Helen Weekly Schedule — Streamlit App

A simple Streamlit app for your helper to tick daily/weekly chores and save progress to an Excel file on Google Drive.

## Files
- `app.py` — the Streamlit app
- `requirements.txt` — dependencies for Streamlit Cloud

## Deploy on Streamlit Cloud
1. Create a new app from your GitHub repo containing these files.
2. In Streamlit Cloud, open **Settings → Secrets** and paste your Google service account JSON + optional app config:

```toml
[gdrive]
type = "service_account"
project_id = "YOUR_PROJECT_ID"
private_key_id = "YOUR_KEY_ID"
private_key = "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----\n"
client_email = "svc-account@YOUR_PROJECT.iam.gserviceaccount.com"
client_id = "YOUR_CLIENT_ID"
token_uri = "https://oauth2.googleapis.com/token"

[app]
drive_file_name = "Helen_Weekly_Schedule_Log.xlsx"
# parent_folder_id = "YOUR_GOOGLE_DRIVE_FOLDER_ID"  # optional
```

3. In Google Drive, share the target folder (or your My Drive) with the **service account email**.
4. Deploy. The app creates (or finds) `Helen_Weekly_Schedule_Log.xlsx` with a `log` sheet.

## How it works
- Select a date. The app shows tasks scheduled for that weekday (Wed–Sun).
- Tick tasks and add a note if needed.
- Click **Save** to append to the Excel log on Drive.
- When you open the same date again, your last saved ticks will prefill automatically.

## Notes
- If Drive isn’t configured, the app saves to a temporary local `local_log.xlsx` (useful for testing).
- You can adjust the task lists in `app.py`.
