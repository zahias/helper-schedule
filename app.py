from datetime import date, timedelta
import streamlit as st

st.set_page_config(page_title="Weekly Schedule (Helen)", page_icon="✅", layout="centered")

APP_TITLE = "Weekly Schedule (Helen) — Tick when done"

# -----------------------------
# Task lists (exact text you provided)
# -----------------------------
DAILY_TASKS = [
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

EVERY2_TASKS = [
    "Mop all floors — separate mop (litter room vs house)",
    "Wipe lower window panes & sills throughout the house",
]
EVERY2_DAYS = ["Wednesday", "Friday", "Sunday"]  # shows only on these days

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
    """Stable widget key per day+task."""
    base = f"{day}::{task}"
    # Streamlit keys must be reasonably short & ascii-ish; simple filter:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in base)[:200]

def tasks_for_day(day: str):
    """Return (section_title, list_of_tasks) groups for the selected day."""
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

# Default day = today's name if in Wed–Sun, else Wednesday
today_name = date.today().strftime("%A")
default_idx = DAYS.index(today_name) if today_name in DAYS else 0
day = st.radio("Choose the day", DAYS, horizontal=True, index=default_idx)

groups = tasks_for_day(day)

# Small progress helper
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
st.markdown(f"**Progress for {day}: {done} / {total}**")

# Reset button for today only
if st.button("Reset today"):
    for _, items in groups:
        for t in items:
            st.session_state[slug(day, t)] = False
    st.experimental_rerun()

st.divider()

# Render simple checklists
for section, items in groups:
    st.subheader(section)
    for t in items:
        st.checkbox(t, key=slug(day, t))

# Footer tip
st.caption("Tip: Pick the day above. Tick tasks as you finish them. Use ‘Reset today’ if you want to start over.")
