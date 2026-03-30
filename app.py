import streamlit as st
from datetime import time

from pawpal_system import Owner, Pet, Task, Scheduler, Priority, TaskType

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# ---------------------------------------------------------------------------
# Session-state bootstrap — runs once per browser session
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = None   # set when owner form is submitted

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🐾 PawPal+")
st.caption("Smart pet care management — powered by your Python backend.")
st.divider()

# ---------------------------------------------------------------------------
# Section 1 — Owner setup
# ---------------------------------------------------------------------------
st.subheader("1. Owner Profile")

if st.session_state.owner is None:
    with st.form("owner_form"):
        owner_name = st.text_input("Your name", value="Jordan")
        owner_email = st.text_input("Email (optional)")
        pref_walk = st.text_input("Preferred walk time (HH:MM)", value="07:00")
        max_hours = st.number_input("Max daily care hours", min_value=1, max_value=12, value=3)
        submitted = st.form_submit_button("Save owner")

    if submitted:
        st.session_state.owner = Owner(
            name=owner_name,
            email=owner_email,
            preferences={"preferred_walk_time": pref_walk, "max_daily_hours": max_hours},
        )
        st.rerun()
else:
    owner: Owner = st.session_state.owner
    st.success(f"Owner: **{owner.name}**  |  {owner.email or '—'}  |  "
               f"Walk pref: {owner.preferences.get('preferred_walk_time', '—')}  |  "
               f"Max hours: {owner.preferences.get('max_daily_hours', '—')}")
    if st.button("Reset owner (clears all data)"):
        st.session_state.owner = None
        st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# Sections 2 & 3 — only show if owner exists
# ---------------------------------------------------------------------------
if st.session_state.owner is None:
    st.info("Fill in the owner profile above to continue.")
    st.stop()

owner: Owner = st.session_state.owner

# ---------------------------------------------------------------------------
# Section 2 — Add a pet
# ---------------------------------------------------------------------------
st.subheader("2. Add a Pet")

with st.form("pet_form"):
    col1, col2 = st.columns(2)
    with col1:
        pet_name = st.text_input("Pet name", value="Mochi")
        species = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
    with col2:
        breed = st.text_input("Breed (optional)")
        age = st.number_input("Age (years)", min_value=0.0, max_value=30.0, value=2.0, step=0.5)
    add_pet_btn = st.form_submit_button("Add pet")

if add_pet_btn:
    if owner.get_pet(pet_name):
        st.warning(f"A pet named '{pet_name}' already exists.")
    elif not pet_name.strip():
        st.warning("Pet name cannot be empty.")
    else:
        owner.add_pet(Pet(name=pet_name, species=species, breed=breed, age=age))
        st.success(f"Added **{pet_name}** the {species}!")
        st.rerun()

if owner.pets:
    st.markdown("**Your pets:**")
    for pet in owner.pets:
        label = f"**{pet.name}** — {pet.species}"
        if pet.breed:
            label += f" ({pet.breed})"
        label += f", {pet.age:.1f} yrs  |  {len(pet.tasks)} task(s)"
        st.markdown(f"- {label}")
else:
    st.caption("No pets yet.")

st.divider()

# ---------------------------------------------------------------------------
# Section 3 — Add a task to a pet
# ---------------------------------------------------------------------------
st.subheader("3. Add a Task")

if not owner.pets:
    st.info("Add at least one pet before adding tasks.")
else:
    with st.form("task_form"):
        pet_options = [p.name for p in owner.pets]
        target_pet = st.selectbox("Assign to pet", pet_options)

        col1, col2 = st.columns(2)
        with col1:
            task_title = st.text_input("Task title", value="Morning walk")
            task_type = st.selectbox("Task type", [t.value for t in TaskType])
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=480, value=30)
        with col2:
            priority = st.selectbox("Priority", [p.value for p in Priority], index=1)
            use_fixed_time = st.checkbox("Set a start time?")
            hour = st.number_input("Hour (0–23)", min_value=0, max_value=23, value=7,
                                   disabled=not use_fixed_time)
            minute = st.number_input("Minute (0–59)", min_value=0, max_value=59, value=0,
                                     disabled=not use_fixed_time)

        is_recurring = st.checkbox("Recurring daily task?")
        notes = st.text_input("Notes (optional)")
        add_task_btn = st.form_submit_button("Add task")

    if add_task_btn:
        scheduled_time = time(int(hour), int(minute)) if use_fixed_time else None
        new_task = Task(
            title=task_title,
            task_type=TaskType(task_type),
            duration_minutes=int(duration),
            priority=Priority(priority),
            scheduled_time=scheduled_time,
            is_recurring=is_recurring,
            notes=notes,
        )
        pet = owner.get_pet(target_pet)
        pet.add_task(new_task)
        st.success(f"Added task **{task_title}** to {target_pet}.")
        st.rerun()

    # Show all current tasks
    all_tasks = owner.all_tasks()
    if all_tasks:
        st.markdown("**All current tasks:**")
        rows = [
            {
                "Pet": t.pet_name,
                "Task": t.title,
                "Type": t.task_type.value,
                "Priority": t.priority.value,
                "Duration (min)": t.duration_minutes,
                "Start time": t.scheduled_time.strftime("%H:%M") if t.scheduled_time else "flexible",
                "Recurring": "Yes" if t.is_recurring else "No",
            }
            for t in all_tasks
        ]
        st.table(rows)
    else:
        st.caption("No tasks yet.")

st.divider()

# ---------------------------------------------------------------------------
# Section 4 — Generate schedule
# ---------------------------------------------------------------------------
st.subheader("4. Generate Schedule")

if st.button("Build today's schedule"):
    if not owner.all_tasks():
        st.warning("Add at least one task before building a schedule.")
    else:
        scheduler = Scheduler(owner)
        schedule = scheduler.build_schedule()
        summary = scheduler.daily_summary()

        st.markdown("### Today's Plan")
        for i, task in enumerate(schedule, start=1):
            done_icon = "✅" if task.completed else "🔲"
            time_str = task.scheduled_time.strftime("%H:%M") if task.scheduled_time else "flexible"
            st.markdown(
                f"{done_icon} **{i}. {task.title}** `[{task.priority.value.upper()}]`  "
                f"— {task.duration_minutes} min @ {time_str}  _{task.pet_name}_"
            )

        st.markdown("### Daily Summary")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total tasks", summary["total_tasks"])
        with col2:
            st.metric("Total minutes", summary["total_minutes"])

        st.markdown("**By priority:** " + "  |  ".join(
            f"{k.upper()}: {v}" for k, v in summary["by_priority"].items()
        ))

        if summary["conflicts"]:
            st.error("⚠️ Schedule conflicts detected:")
            for a_title, b_title in summary["conflicts"]:
                st.markdown(f"- **{a_title}** overlaps with **{b_title}**")
        else:
            st.success("No schedule conflicts.")
