import json
import io
import csv
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple

import streamlit as st

APP_TITLE = "Weekly Schedule (Helen) — Tick when done"

# -----------------------------
# Task Definitions (Exact text)
# -----------------------------
DAILY_TASKS: List[str] = [
    "Open windows 10–15 min; Wipe sufarces/Remove dust/tidy up/Remove fur with glove on sofas, chairs, curtain bottoms silently",
    "Rinse/wash dishes after meals; dry and clean sink before bedtime",
    "Wipe dining table & kitchen counters after each meal",
    "Sweep or spot-vacuum crumbs in living room/kitchen",
    "Hoover or run robot (avoid baby nap); quick fur spots",
    "Clean toilets (seat, bowl, rim) + sink; quick shower rinse",
    "Litter room: check 2–3×; sweep spills; wipe majla if dirty (use gloves and wash hands always afterwards)",
    "Wipe stovetop after use; degrease backsplash if splashed",
    "Take out kitchen & litter trash ( wash hands afterwards); replace bags",
    "Laundry – sort colors & load machine in the morning",
    "Laundry – fold same day and put away neatly",
    "Wash water pet bowl; refresh water AM/PM",
    "Laundry – iron shirts/pants as needed",
]

# Every 2 days appear on Wed, Fri, Sun (to match your table pattern)
EVERY2_TASKS: List[str] = [
    "Mop all floors — separate mop (litter room vs house)",
    "Wipe lower window panes & sills throughout the house",
]
EVERY2_SCHEDULE_DAYS = ["Wednesday", "Friday", "Sunday"]

# Weekly: first group on Saturday; second group on Thursday (per your table)
WEEKLY_TASKS_SATURDAY: List[str] = [
    "Oven: remove trays; clean inside, door glass, upper parts",
    "Microwave: clean inside; wipe handle/exterior",
    "Fridge: wipe exterior & handles; spot-clean shelves (spills)",
    "Terrace clean: clean furniture; wash floor; wipe railing",
    "Disinfect doors, handles, and light switches",
]
WEEKLY_TASKS_THURSDAY: List[str] = [
    "Litter tray: empty, wash, refill; scrub surrounding floor",
    "Pantry quick tidy + expiry scan",
    "Squeegee shower tiles after last shower",
    "Mirrors & glass doors",
    "Clean house entry area",
    "Refill Soap",
]

# -----------------------------
# Helpers
# -----------------------------
def slugify(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in text).strip("-")

def get_week_start_wed(d: date) -> date:
    """Return the Wednesday of the week containing date d."""
    # Python weekday(): Monday=0 ... Sunday=6. Wednesday=2
    offset = (d.weekday() - 2) % 7
    return d - timedelta(days=offset)

def week_days_wed_to_sun(week_start_wed: date) -> List[date]:
    return [week_start_wed + timedelta(days=i) for i in range(5)]  # Wed..Sun

def fmt_date(d: date) -> str:
    return d.strftime("%a %d %b %Y")

def today_local() -> date:
    # Streamlit Cloud uses server time; this is fine for daily ticking.
    # If you need strict timezone, consider pytz/zoneinfo.
    return date.today()

# -----------------------------
# Storage (simple JSON on disk)
# -----------------------------
def load_store() -> Dict:
    try:
        with open("progress.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_store(store: Dict):
    with open("progress.json", "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)

def get_week_key(week_start_wed: date) -> str:
    return week_start_wed.isoformat()

def default_week_state() -> Dict[str, Dict[str, bool]]:
    return {}  # day -> task_slug -> bool

def ensure_week_initialized(store: Dict, week_key: str):
    if "weeks" not in store:
        store["weeks"] = {}
    if week_key not in store["weeks"]:
        store["weeks"][week_key] = default_week_state()

# -----------------------------
# Task schedule logic
# -----------------------------
ALL_DAYS = ["Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def tasks_due_on(day_name: str) -> List[Tuple[str, str]]:
    """Return list of (section, task_text) for tasks due on the given day."""
    due = []
    # Daily
    for t in DAILY_TASKS:
        due.append(("DAILY", t))

    # Every 2 days
    if day_name in EVERY2_SCHEDULE_DAYS:
        for t in EVERY2_TASKS:
            due.append(("EVERY 2 DAYS", t))

    # Weekly (Thu group / Sat group)
    if day_name == "Thursday":
        for t in WEEKLY_TASKS_THURSDAY:
            due.append(("WEEKLY", t))
    if day_name == "Saturday":
        for t in WEEKLY_TASKS_SATURDAY:
            due.append(("WEEKLY", t))

    return due

def all_tasks_for_week() -> List[Tuple[str, str, List[str]]]:
    """
    For exporting CSV: return tuples of (section, task_text, days_scheduled)
    """
    rows = []
    for t in DAILY_TASKS:
        rows.append(("DAILY", t, ALL_DAYS))
    for t in EVERY2_TASKS:
        rows.append(("EVERY 2 DAYS", t, EVERY2_SCHEDULE_DAYS))
    rows.extend([("WEEKLY", t, ["Saturday"]) for t in WEEKLY_TASKS_SATURDAY])
    rows.extend([("WEEKLY", t, ["Thursday"]) for t in WEEKLY_TASKS_THURSDAY])
    return rows

# -----------------------------
# UI
# -----------------------------
st.set_page_config(page_title=APP_TITLE, page_icon="✅", layout="centered")
st.title(APP_TITLE)

# Sidebar controls
with st.sidebar:
    st.header("Controls")
    chosen_date = st.date_input("Select a date", value=today_local())
    week_start = get_week_start_wed(chosen_date)
    week_label = f"Week: {fmt_date(week_start)} → {fmt_date(week_start + timedelta(days=4))} (Wed→Sun)"
    st.markdown(f"**{week_label}**")

    # Determine day index and name within Wed→Sun
    days = week_days_wed_to_sun(week_start)
    day_options = {d.strftime("%A"): d for d in days}  # "Wednesday": date
    # Pick the day matching chosen_date if within Wed-Sun, otherwise default to Wednesday
    if chosen_date in days:
        default_day_name = chosen_date.strftime("%A")
    else:
        default_day_name = "Wednesday"

    day_name = st.selectbox("Day to tick", options=list(day_options.keys()), index=list(day_options.keys()).index(default_day_name))

    st.markdown("---")
    st.caption("💾 Save / Restore")
    uploaded = st.file_uploader("Restore progress (.json)", type=["json"], help="Upload a previously downloaded progress.json")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        download_json_btn = st.button("⬇️ Download progress JSON")
    with col_d2:
        download_csv_btn = st.button("⬇️ Download this week as CSV")

    st.markdown("---")
    st.caption("⚠️ Reset")
    reset_day = st.button("Reset selected day")
    reset_week = st.button("Reset entire week")

# Load/restore progress store
store = load_store()

# Handle uploaded progress
if uploaded is not None:
    try:
        uploaded_store = json.load(uploaded)
        # Simple replace strategy; you could also merge
        store = uploaded_store
        save_store(store)
        st.success("Progress restored from uploaded file.")
    except Exception as e:
        st.error(f"Could not read uploaded JSON: {e}")

# Ensure current week initialized
week_key = get_week_key(week_start)
ensure_week_initialized(store, week_key)

# Initialize day state map
if day_name not in store["weeks"][week_key]:
    store["weeks"][week_key][day_name] = {}

# Reset actions
if reset_day:
    store["weeks"][week_key][day_name] = {}
    save_store(store)
    st.warning(f"All ticks cleared for **{day_name}**.", icon="⚠️")

if reset_week:
    store["weeks"][week_key] = {}
    save_store(store)
    st.warning("All ticks cleared for the **entire week**.", icon="⚠️")

# Due tasks for selected day
due = tasks_due_on(day_name)

# Sectioned layout
st.subheader(f"Tasks due on **{day_name}**")
st.caption("Tick tasks as you complete them. Daily tasks always appear. ‘Every 2 Days’ and ‘Weekly’ show only on their scheduled days.")

# Quick actions
qc1, qc2 = st.columns(2)
with qc1:
    mark_all = st.button("Mark all done ✅")
with qc2:
    clear_all = st.button("Clear all ⭕")

day_state: Dict[str, bool] = store["weeks"][week_key].get(day_name, {})

# Apply quick actions (in-memory first)
if mark_all:
    for _, task in due:
        day_state[slugify(task)] = True
if clear_all:
    for _, task in due:
        day_state[slugify(task)] = False

# Render tasks grouped by section
section_order = ["DAILY", "EVERY 2 DAYS", "WEEKLY"]
for section in section_order:
    section_tasks = [t for sec, t in due if sec == section]
    if not section_tasks:
        continue
    st.markdown(f"### {section}")
    for task in section_tasks:
        key = slugify(task)
        current_val = day_state.get(key, False)
        new_val = st.checkbox(task, value=current_val, key=f"{day_name}-{key}")
        day_state[key] = new_val

# Save button
if st.button("Save progress 💾"):
    # Persist updated day_state
    store["weeks"][week_key][day_name] = day_state
    save_store(store)
    st.success("Progress saved.", icon="✅")

# Download buttons (generate files when clicked)
if download_json_btn:
    # Ensure latest UI state is saved before export
    store["weeks"][week_key][day_name] = day_state
    json_bytes = json.dumps(store, ensure_ascii=False, indent=2).encode("utf-8")
    st.download_button(
        label="Download progress.json",
        data=json_bytes,
        file_name="progress.json",
        mime="application/json",
    )

if download_csv_btn:
    # Build a CSV showing full week plan + current ticks
    rows = []
    tasks_plan = all_tasks_for_week()
    for section, task, scheduled_days in tasks_plan:
        for dname in ALL_DAYS:
            is_scheduled = dname in scheduled_days
            val = ""
            if is_scheduled:
                # lookup saved state if exists
                week_map = store["weeks"].get(week_key, {})
                day_map = week_map.get(dname, {})
                val = "✅" if day_map.get(slugify(task), False) else "☐"
            rows.append([section, task, dname, "Yes" if is_scheduled else "No", val])

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Section", "Task", "Day", "Scheduled", "Done"])
    writer.writerows(rows)
    st.download_button(
        label="Download week.csv",
        data=out.getvalue().encode("utf-8-sig"),
        file_name="week.csv",
        mime="text/csv",
    )

# Footer tip
st.markdown("---")
st.caption(
    "Tip: Use the **sidebar date** to jump to any day (Wed→Sun). "
    "Click **Save progress** or download **progress.json** to keep a copy. "
    "You can restore it later from the sidebar."
)
