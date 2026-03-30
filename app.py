import streamlit as st
from datetime import time

from pawpal_system import Owner, Pet, Task, Scheduler, Priority, TaskType

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# ---------------------------------------------------------------------------
# Session-state bootstrap — runs once per browser session
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = None

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
    st.success(
        f"**{owner.name}**  |  {owner.email or '—'}  |  "
        f"Walk pref: {owner.preferences.get('preferred_walk_time', '—')}  |  "
        f"Max hours/day: {owner.preferences.get('max_daily_hours', '—')}"
    )
    if st.button("Reset owner (clears all data)"):
        st.session_state.owner = None
        st.rerun()

st.divider()

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
    cols = st.columns(len(owner.pets))
    for col, pet in zip(cols, owner.pets):
        pending = sum(1 for t in pet.tasks if not t.completed)
        done    = sum(1 for t in pet.tasks if t.completed)
        with col:
            st.metric(
                label=f"{pet.name} ({pet.species})",
                value=f"{pending} pending",
                delta=f"{done} done" if done else None,
                delta_color="off",
            )
            if pet.breed:
                st.caption(f"{pet.breed}, {pet.age:.1f} yrs")
else:
    st.caption("No pets yet.")

st.divider()

# ---------------------------------------------------------------------------
# Section 3 — Add a task
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
        owner.get_pet(target_pet).add_task(new_task)
        st.success(f"Added **{task_title}** to {target_pet}.")
        st.rerun()

    # Task table — sorted by time via Scheduler.sort_by_time()
    all_tasks = owner.all_tasks()
    if all_tasks:
        scheduler_preview = Scheduler(owner)
        sorted_tasks = scheduler_preview.sort_by_time()
        st.caption("Tasks shown in scheduled order (fixed-time first, then by priority).")
        rows = [
            {
                "Pet": t.pet_name,
                "Task": t.title,
                "Type": t.task_type.value,
                "Priority": t.priority.value.upper(),
                "Duration (min)": t.duration_minutes,
                "Start": t.scheduled_time.strftime("%H:%M") if t.scheduled_time else "flexible",
                "Recurring": "✓" if t.is_recurring else "",
                "Done": "✓" if t.completed else "",
            }
            for t in sorted_tasks
        ]
        st.table(rows)
    else:
        st.caption("No tasks yet.")

st.divider()

# ---------------------------------------------------------------------------
# Section 4 — Schedule (three tabs)
# ---------------------------------------------------------------------------
st.subheader("4. Schedule")

tab_plan, tab_filter, tab_conflicts = st.tabs(
    ["📋 Today's Plan", "🔍 Filter Tasks", "⚠️ Conflicts"]
)

# ---- Tab 1: Today's Plan ---------------------------------------------------
with tab_plan:
    if st.button("Build today's schedule", key="build_btn"):
        if not owner.all_tasks():
            st.warning("Add at least one task before building a schedule.")
        else:
            scheduler = Scheduler(owner)
            schedule  = scheduler.build_schedule()
            summary   = scheduler.daily_summary()

            # Conflict banner — shown at the top so it's impossible to miss
            warnings = scheduler.conflict_warnings()
            if warnings:
                st.error("**Schedule conflicts detected — review before your day starts:**")
                for w in warnings:
                    st.markdown(f"- {w}")
            else:
                st.success("No time conflicts — your schedule is clean.")

            st.markdown("---")

            # Schedule cards
            priority_colors = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            for i, task in enumerate(schedule, start=1):
                dot      = priority_colors.get(task.priority.value, "⚪")
                time_str = task.scheduled_time.strftime("%H:%M") if task.scheduled_time else "flexible"
                recur    = " 🔁" if task.is_recurring else ""
                note_str = f"  \n  _{task.notes}_" if task.notes else ""

                st.markdown(
                    f"{dot} **{i}. {task.title}**{recur}  \n"
                    f"  {task.task_type.value.capitalize()} · {task.duration_minutes} min · "
                    f"@ {time_str} · _{task.pet_name}_{note_str}"
                )

            st.divider()

            # Summary metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Total tasks",   summary["total_tasks"])
            col2.metric("Total minutes", summary["total_minutes"])
            col3.metric("Conflicts",     len(summary["conflicts"]),
                        delta="⚠ review" if summary["conflicts"] else "none",
                        delta_color="inverse")

            if summary["by_priority"]:
                st.markdown("**Priority breakdown:** " + "  ·  ".join(
                    f"{k.upper()} {v}" for k, v in summary["by_priority"].items()
                ))

# ---- Tab 2: Filter Tasks ---------------------------------------------------
with tab_filter:
    st.markdown("Filter your tasks by pet or completion status.")

    col1, col2 = st.columns(2)
    with col1:
        pet_filter_options = ["All pets"] + [p.name for p in owner.pets]
        pet_filter = st.selectbox("Pet", pet_filter_options, key="pet_filter")
    with col2:
        status_filter = st.selectbox(
            "Status", ["All", "Pending only", "Completed only"], key="status_filter"
        )

    if owner.all_tasks():
        scheduler_filter = Scheduler(owner)
        pet_arg      = None if pet_filter == "All pets" else pet_filter
        status_arg   = None
        if status_filter == "Pending only":
            status_arg = False
        elif status_filter == "Completed only":
            status_arg = True

        filtered = scheduler_filter.filter_tasks(pet_name=pet_arg, completed=status_arg)

        if filtered:
            st.caption(f"{len(filtered)} task(s) match your filter.")
            rows = [
                {
                    "Pet":          t.pet_name,
                    "Task":         t.title,
                    "Priority":     t.priority.value.upper(),
                    "Type":         t.task_type.value,
                    "Duration":     f"{t.duration_minutes} min",
                    "Start":        t.scheduled_time.strftime("%H:%M") if t.scheduled_time else "flexible",
                    "Done":         "✓" if t.completed else "—",
                }
                for t in filtered
            ]
            st.table(rows)
        else:
            st.info("No tasks match the selected filters.")
    else:
        st.info("No tasks added yet.")

# ---- Tab 3: Conflicts -------------------------------------------------------
with tab_conflicts:
    st.markdown(
        "Conflicts occur when two fixed-time tasks have overlapping windows "
        "(start time + duration). The scheduler warns you but never auto-moves tasks."
    )

    if owner.all_tasks():
        scheduler_conflict = Scheduler(owner)
        warnings = scheduler_conflict.conflict_warnings()

        if warnings:
            st.error(f"**{len(warnings)} conflict(s) found:**")
            for w in warnings:
                st.warning(w)
            st.markdown(
                "> **Tip:** edit one of the conflicting tasks to give it a different "
                "start time, or remove the fixed time to make it flexible."
            )
        else:
            st.success("No conflicts detected in your current task list.")
    else:
        st.info("No tasks added yet.")
