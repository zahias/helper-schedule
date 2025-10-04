from datetime import date
import streamlit as st

# Mobile-first page config
st.set_page_config(page_title="Weekly Schedule (Helen)", page_icon="✅", layout="wide")

APP_TITLE = "Weekly Schedule (Helen) — Tick when done"

# -----------------------------
# Task lists (your exact list, with 'surfaces' typo fixed)
# -----------------------------
DAILY_TASKS = [
    "Open windows 10–15 min; Wipe surfaces/Remove dust/tidy up/Remove fur with glove on sofas, chairs, curtain bottoms silently",
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

EVERY2_TASKS = [
    "Mop all floors — separate mop (litter room vs house)",
    "Wipe lower window panes & sills throughout the house",
]
EVERY2_DAYS = ["Wednesday", "Friday", "Sunday"]

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

DAYS = ["Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def slug(day: str, task: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in f"{day}::{task}")[:200]

def tasks_for_day(day: str):
    groups = [("DAILY TASKS", DAILY_TASKS)]
    if day in EVERY2_DAYS:
        groups.append(("EVERY 2 DAYS", EVERY2_TASKS))
    if day == "Thursday":
        groups.append(("WEEKLY TASKS", WEEKLY_TASKS_THU))
    if day == "Saturday":
        groups.append(("WEEKLY TASKS", WEEKLY_TASKS_SAT))
    return groups

# -----------------------------
# UI
# -----------------------------
st.title(APP_TITLE)

# Simple text-size control (big, bigger, biggest)
size_choice = st.radio(
    "Text size",
    ["Normal", "Large", "Extra Large"],
    horizontal=True,
    index=1,  # default to Large
)

# Map sizes to CSS vars
size_map = {
    "Normal": {"base": 17, "check": 18, "radio": 16, "scale": 1.00},
    "Large": {"base": 19, "check": 20, "radio": 18, "scale": 1.12},
    "Extra Large": {"base": 21, "check": 22, "radio": 20, "scale": 1.25},
}
S = size_map[size_choice]

# Mobile-friendly CSS for readability
st.markdown(
    f"""
    <style>
    html, body, .block-container {{ font-size: {S['base']}px; }}
    .block-container {{ padding-top: 0.5rem; padding-bottom: 2rem; }}

    /* Day picker: horizontal pills + larger text */
    div[role="radiogroup"] {{
      display: flex !important;
      gap: 8px;
      overflow-x: auto;
      white-space: nowrap;
      padding: 0.25rem 0 0.5rem 0;
    }}
    div[role="radiogroup"] > label {{
      border: 1px solid #e6e6e6 !important;
      border-radius: 999px !important;
      padding: 0.45rem 0.9rem !important;
      margin: 0 !important;
      background: #fafafa;
      font-size: {S['radio']}px !important;
    }}

    /* Bigger checkbox labels + comfy line height */
    div[data-testid="stCheckbox"] label {{
      font-size: {S['check']}px !important;
      line-height: 1.5 !important;
    }}
    /* Slightly enlarge the checkbox hit area */
    div[data-testid="stCheckbox"] input {{
      transform: scale({S['scale']});
      margin-right: 6px;
    }}

    /* Make section headers stand out a bit more on mobile */
    h3, h2 {{ margin-top: 0.8rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Day picker (mobile-friendly horizontal radio)
today_name = date.today().strftime("%A")
default_idx = DAYS.index(today_name) if today_name in DAYS else 0
day = st.radio("Choose the day", DAYS, horizontal=True, index=default_idx, label_visibility="collapsed")

groups = tasks_for_day(day)

# Progress
def progress_counts(day_name: str):
    total = 0
    done = 0
    for _, items in groups:
        for t in items:
            total += 1
            if st.session_state.get(slug(day_name, t), False):
                done += 1
    return done, total

done, total = progress_counts(day)
pct = int(100 * done / total) if total else 0
st.write(f"**Progress for {day}: {done} / {total} ({pct}%)**")
st.progress(pct)

left, right = st.columns(2)
if left.button("Mark all done ✅"):
    for _, items in groups:
        for t in items:
            st.session_state[slug(day, t)] = True
    st.rerun()
if right.button("Reset today ⭕"):
    for _, items in groups:
        for t in items:
            st.session_state[slug(day, t)] = False
    st.rerun()

st.divider()

# Checklist (simple)
for section, items in groups:
    st.subheader(section)
    for t in items:
        st.checkbox(t, key=slug(day, t))

st.caption("Tip: Swipe the day selector if it overflows. Increase text size above if needed.")
