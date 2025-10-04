import io
from datetime import datetime, date
from typing import Dict, List

import pandas as pd
import streamlit as st

# === Google Drive imports ===
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from googleapiclient.errors import HttpError

# =============================
# CONFIG — SCHEDULE DEFINITIONS
# =============================

DAYS = ["Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

DAILY_TASKS = [
    "Open windows 10–15 min; Wipe surfaces/Remove dust/tidy up/Remove fur with glove on sofas, chairs, curtain bottoms silently",
    "Rinse/wash dishes after meals; dry and clean sink before bedtime",
    "Wipe dining table & kitchen counters after each meal",
    "Sweep or spot-vacuum crumbs in living room/kitchen",
    "Hoover or run robot (avoid baby nap); quick fur spots",
    "Clean toilets (seat, bowl, rim) + sink; quick shower rinse",
    "Litter room: check 2–3×; sweep spills; wipe majla if dirty (use gloves and wash hands always afterwards)",
    "Wipe stovetop after use; degrease backsplash if splashed",
    "Take out kitchen & litter trash (wash hands afterwards); replace bags",
    "Laundry – sort colors & load machine in the morning",
    "Laundry – fold same day and put away neatly",
    "Wash water pet bowl; refresh water AM/PM",
    "Laundry – iron shirts/pants as needed",
]

# every-2-days on Wed, Fri, Sun
EVERY2_TASKS = [
    "Mop all floors — separate mop (litter room vs house)",
    "Wipe lower window panes & sills throughout the house",
]
EVERY2_DAYS = {"Wednesday", "Friday", "Sunday"}

# weekly tasks assigned to a specific weekday
WEEKLY_TASKS_THU = [
    "Litter tray: empty, wash, refill; scrub surrounding floor",
    "Pantry quick tidy + expiry scan",
    "Squeegee shower tiles after last shower",
    "Mirrors & glass doors",
    "Clean house entry area",
    "Refill Soap",
]
WEEKLY_TASKS_SAT = [
    "Oven: remove trays; clean inside, door glass, upper parts",
    "Microwave: clean inside; wipe handle/exterior",
    "Fridge: wipe exterior & handles; spot-clean shelves (spills)",
    "Terrace clean: clean furniture; wash floor; wipe railing",
    "Disinfect doors, handles, and light switches",
]

# =========================
# CONFIG — DRIVE + FILE I/O
# =========================
DEFAULT_EXCEL_NAME = "Helen_Weekly_Schedule_Log.xlsx"

def _init_drive():
    """Initialize Google Drive service from st.secrets; return service or None on failure."""
    try:
        creds_dict = st.secrets.get("gdrive")
        if not creds_dict:
            return None
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        service = build("drive", "v3", credentials=creds)
        return service
    except Exception as e:
        st.warning(f"Google Drive not configured (using local fallback). Details: {e}")
        return None


def _find_file(service, name: str) -> str:
    """Return file ID if a Drive file with this name exists (and not trashed), else ''."""
    try:
        q = f"name = '{name}' and mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' and trashed = false"
        resp = service.files().list(q=q, spaces="drive", fields="files(id, name)").execute()
        files = resp.get("files", [])
        return files[0]["id"] if files else ""
    except HttpError as e:
        st.error(f"Drive search error: {e}")
        return ""


def _empty_log_excel_bytes() -> bytes:
    """Create a minimal Excel workbook (in-memory) with a 'log' sheet and no rows."""
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df = pd.DataFrame(columns=["timestamp", "date", "day", "task", "completed", "note"])
        df.to_excel(writer, sheet_name="log", index=False)
    return out.getvalue()


def _create_drive_file(service, name: str, parent_folder_id: str = "") -> str:
    """Create a new Excel file on Drive and return its file ID."""
    file_metadata = {"name": name, "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
    if parent_folder_id:
        file_metadata["parents"] = [parent_folder_id]
    media = MediaIoBaseUpload(io.BytesIO(_empty_log_excel_bytes()),
                              mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                              resumable=False)
    created = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return created["id"]


def _download_excel(service, file_id: str) -> bytes:
    """Download the Excel file bytes from Drive."""
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue()


def _upload_excel(service, file_id: str, data: bytes):
    """Upload (update) the Excel file on Drive."""
    media = MediaIoBaseUpload(io.BytesIO(data),
                              mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                              resumable=False)
    service.files().update(fileId=file_id, media_body=media).execute()


def _load_log_df_from_bytes(xls_bytes: bytes) -> pd.DataFrame:
    try:
        with pd.ExcelFile(io.BytesIO(xls_bytes)) as xls:
            if "log" in xls.sheet_names:
                return pd.read_excel(xls, sheet_name="log")
            else:
                return pd.DataFrame(columns=["timestamp", "date", "day", "task", "completed", "note"])
    except Exception:
        return pd.DataFrame(columns=["timestamp", "date", "day", "task", "completed", "note"])


def _save_log_df_to_bytes(df: pd.DataFrame) -> bytes:
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="log", index=False)
    return out.getvalue()


# ==================
# APP HELPER LOGIC
# ==================

def weekday_name(d: date) -> str:
    return d.strftime("%A")


def tasks_for_day(day_name: str) -> List[str]:
    """Return the list of tasks scheduled for the provided day name."""
    tasks = list(DAILY_TASKS)

    if day_name in EVERY2_DAYS:
        tasks.extend(EVERY2_TASKS)

    if day_name == "Thursday":
        tasks.extend(WEEKLY_TASKS_THU)
    if day_name == "Saturday":
        tasks.extend(WEEKLY_TASKS_SAT)

    return tasks


def latest_status_map(log_df: pd.DataFrame, target_date: date) -> Dict[str, bool]:
    """For a given date, return the latest completion status per task (True/False)."""
    if log_df.empty:
        return {}
    dstr = target_date.isoformat()
    sub = log_df[log_df["date"] == dstr]
    if sub.empty:
        return {}
    sub = sub.sort_values("timestamp")
    latest = sub.groupby("task").tail(1)
    return {row["task"]: bool(row["completed"]) for _, row in latest.iterrows()}


def upsert_log(log_df: pd.DataFrame, target_date: date, day_name: str,
               task_status: Dict[str, bool], note: str) -> pd.DataFrame:
    """Append new rows for today's status (append-only log)."""
    now = datetime.utcnow().isoformat()
    rows = []
    for task, done in task_status.items():
        rows.append({
            "timestamp": now,
            "date": target_date.isoformat(),
            "day": day_name,
            "task": task,
            "completed": 1 if done else 0,
            "note": note if note else "",
        })
    to_add = pd.DataFrame(rows)
    if log_df.empty:
        return to_add
    return pd.concat([log_df, to_add], ignore_index=True)


# =========
#   UI
# =========

st.set_page_config(page_title="Weekly Schedule (Helen)", page_icon="✅", layout="centered")

st.title("Weekly Schedule (Helen) — Tick ☑ when done")

with st.sidebar:
    st.markdown("### How it works")
    st.write(
        "- Choose the date. The app loads only tasks **scheduled** for that weekday (Wed–Sun).\n"
        "- Tick tasks as you complete them. Add a short note if needed.\n"
        "- Click **Save** to record to an Excel file on Google Drive.\n"
        "- Next time you open the same date, the last saved ticks will prefill."
    )
    st.markdown("---")
    st.markdown("### Drive setup")
    st.write(
        "Add your service account JSON to `st.secrets['gdrive']` and (optionally):\n"
        "- `st.secrets['app']['drive_file_name']` (default: Helen_Weekly_Schedule_Log.xlsx)\n"
        "- `st.secrets['app']['parent_folder_id']` (optional Drive folder ID)\n"
        "Share the folder with the service account email."
    )

today = date.today()
sel_date = st.date_input("Select date", value=today, format="YYYY-MM-DD")
sel_day = weekday_name(sel_date)

if sel_day not in DAYS:
    st.info(
        f"Selected day is **{sel_day}**. Helen typically works **Wednesday–Sunday**. "
        "You can still save progress for this date."
    )

# Load log (Drive or local)
service = _init_drive()
fname = st.secrets.get("app", {}).get("drive_file_name", DEFAULT_EXCEL_NAME)
parent_folder_id = st.secrets.get("app", {}).get("parent_folder_id", "")

log_df = pd.DataFrame(columns=["timestamp", "date", "day", "task", "completed", "note"])
file_id = ""
loaded_from_drive = False

if service is not None:
    file_id = _find_file(service, fname)
    try:
        if not file_id:
            file_id = _create_drive_file(service, fname, parent_folder_id)
        xls_bytes = _download_excel(service, file_id)
        log_df = _load_log_df_from_bytes(xls_bytes)
        loaded_from_drive = True
    except Exception as e:
        st.warning(f"Drive access fallback to local (temp). Reason: {e}")

# Prefill state from log
prefill = latest_status_map(log_df, sel_date)

st.subheader(f"Tasks for {sel_day}")
st.caption("Tip: start with quiet tasks (opening windows, tidying) before any noisy tasks like hoovering.")

def render_section(title: str, task_list: List[str]) -> Dict[str, bool]:
    st.markdown(f"#### {title}")
    check_all = st.checkbox(f"Check all in {title}", key=f"all_{title}_{sel_date.isoformat()}")
    states = {}
    for task in task_list:
        default_val = prefill.get(task, False)
        val = check_all or st.checkbox(task, value=default_val, key=f"{sel_date.isoformat()}::{task}")
        states[task] = bool(val)
    st.divider()
    return states

# Build visible sections based on selected day
daily_states = render_section("DAILY TASKS", DAILY_TASKS)

every2_states = {}
if sel_day in {"Wednesday", "Friday", "Sunday"}:
    every2_states = render_section("EVERY 2 DAYS", EVERY2_TASKS)

weekly_states = {}
if sel_day == "Thursday":
    weekly_states = render_section("WEEKLY TASKS (Thursday)", WEEKLY_TASKS_THU)
elif sel_day == "Saturday":
    weekly_states = render_section("WEEKLY TASKS (Saturday)", WEEKLY_TASKS_SAT)

# Notes
note = st.text_area("Notes for today (optional)", placeholder="e.g., Ran out of trash bags, microwave very dirty today, etc.")

# Merge all visible tasks for saving
all_states = {**daily_states, **every2_states, **weekly_states}

# Save button
save = st.button("💾 Save to Google Drive", type="primary")

if save:
    if not all_states:
        st.warning("No tasks visible to save for this day.")
    else:
        new_log = upsert_log(log_df, sel_date, sel_day, all_states, note)

        if loaded_from_drive and service is not None and file_id:
            try:
                data_bytes = _save_log_df_to_bytes(new_log)
                _upload_excel(service, file_id, data_bytes)
                st.success(f"Saved to Google Drive file: {fname}")
            except Exception as e:
                st.error(f"Failed to save to Drive ({e}). Attempting local save...")
                data_bytes = _save_log_df_to_bytes(new_log)
                with open("local_log.xlsx", "wb") as f:
                    f.write(data_bytes)
                st.info("Saved to local file 'local_log.xlsx' (temporary).")
        else:
            data_bytes = _save_log_df_to_bytes(new_log)
            with open("local_log.xlsx", "wb") as f:
                f.write(data_bytes)
            st.success("Saved locally to 'local_log.xlsx' (temporary). Configure Drive to persist.")
        st.balloons()

# History / Summary for the selected date
st.markdown("### Today’s Summary")
done_count = sum(1 for v in all_states.values() if v)
st.write(f"Completed **{done_count}** of **{len(all_states)}** visible tasks.")
if done_count and len(all_states):
    done_list = [t for t, v in all_states.items() if v]
    st.write("✅ Done:")
    st.write("\\n".join(f"- {t}" for t in done_list))
else:
    st.caption("No tasks ticked yet.")

st.markdown("---")
st.caption("If the helper only uses a phone, enable wide mode from the ☰ menu for larger checkboxes.")
