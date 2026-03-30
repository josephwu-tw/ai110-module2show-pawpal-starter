"""
PawPal+ — demo script (Phase 2 + Phase 4).

Demonstrates:
  1. Basic schedule output
  2. sort_by_time()  — tasks added out of order, then sorted
  3. filter_tasks()  — filter by pet and by completion status
  4. complete_task() — recurring task auto-renewal
  5. conflict_warnings() — two overlapping tasks trigger a warning

Run with:  python main.py
"""

from datetime import time

from pawpal_system import (
    Owner,
    Pet,
    Priority,
    Scheduler,
    Task,
    TaskType,
)

SEP = "-" * 50


def main() -> None:
    # ------------------------------------------------------------------
    # 1. Build owner and pets
    # ------------------------------------------------------------------
    jordan = Owner(
        name="Jordan",
        preferences={"preferred_walk_time": "07:00", "max_daily_hours": 3},
    )

    mochi = Pet(name="Mochi", species="dog", breed="Golden Retriever", age=2)
    noodle = Pet(name="Noodle", species="cat", breed="Tabby", age=4)

    # Tasks added deliberately OUT OF TIME ORDER to show sorting works
    mochi.add_task(Task("Evening feeding",  TaskType.FEEDING,     15, Priority.HIGH,   time(18, 0), is_recurring=True))
    mochi.add_task(Task("Flea medication",  TaskType.MEDICATION,   5, Priority.MEDIUM))          # flexible
    mochi.add_task(Task("Morning walk",     TaskType.WALK,         30, Priority.HIGH,   time(7, 0), is_recurring=True))

    noodle.add_task(Task("Playtime",        TaskType.OTHER,        20, Priority.LOW))             # flexible
    noodle.add_task(Task("Vet checkup",     TaskType.APPOINTMENT,  60, Priority.HIGH,   time(10, 0), notes="Annual wellness exam"))
    noodle.add_task(Task("Morning feeding", TaskType.FEEDING,      10, Priority.HIGH,   time(7, 30), is_recurring=True))

    jordan.add_pet(mochi)
    jordan.add_pet(noodle)

    scheduler = Scheduler(jordan)

    # ------------------------------------------------------------------
    # 2. sort_by_time — show tasks in chronological order
    # ------------------------------------------------------------------
    print(SEP)
    print("FEATURE 1 — sort_by_time() (tasks were added out of order)")
    print(SEP)
    for task in scheduler.sort_by_time():
        print(" ", task.summary())

    # ------------------------------------------------------------------
    # 3. filter_tasks — by pet name, then by completion status
    # ------------------------------------------------------------------
    print()
    print(SEP)
    print("FEATURE 2 — filter_tasks(pet_name='Mochi')")
    print(SEP)
    for task in scheduler.filter_tasks(pet_name="Mochi"):
        print(" ", task.summary())

    print()
    print(SEP)
    print("FEATURE 2 — filter_tasks(completed=False)  [all pending]")
    print(SEP)
    pending = scheduler.filter_tasks(completed=False)
    print(f"  {len(pending)} pending task(s) found")

    # ------------------------------------------------------------------
    # 4. complete_task — mark a recurring task done, auto-renew it
    # ------------------------------------------------------------------
    print()
    print(SEP)
    print("FEATURE 3 — complete_task() with recurring auto-renewal")
    print(SEP)
    morning_walk = mochi.get_tasks_by_type(TaskType.WALK)[0]
    print(f"  Completing: '{morning_walk.title}'  (recurring={morning_walk.is_recurring})")
    renewed = scheduler.complete_task(morning_walk)
    if renewed:
        print(f"  Auto-renewed: '{renewed.title}'  completed={renewed.completed}")

    # Confirm original is done and renewed copy is pending
    completed_tasks = scheduler.filter_tasks(completed=True)
    pending_tasks   = scheduler.filter_tasks(completed=False)
    print(f"  Completed tasks : {[t.title for t in completed_tasks]}")
    print(f"  Pending tasks   : {len(pending_tasks)} remaining")

    # ------------------------------------------------------------------
    # 5. conflict_warnings — add a task that overlaps morning walk
    # ------------------------------------------------------------------
    print()
    print(SEP)
    print("FEATURE 4 — conflict_warnings()  (intentional overlap at 07:00)")
    print(SEP)
    mochi.add_task(Task(
        title="Bath time",
        task_type=TaskType.OTHER,
        duration_minutes=20,
        priority=Priority.MEDIUM,
        scheduled_time=time(7, 10),   # starts while Morning walk is still running
    ))
    scheduler.build_schedule()
    warnings = scheduler.conflict_warnings()
    if warnings:
        for w in warnings:
            print(" ", w)
    else:
        print("  No conflicts detected.")

    # ------------------------------------------------------------------
    # 6. Full schedule + summary (from Phase 2)
    # ------------------------------------------------------------------
    print()
    print(SEP)
    print("FULL SCHEDULE")
    print(SEP)
    print(scheduler.explain_plan())
    print()
    summary = scheduler.daily_summary()
    print("=== Daily Summary ===")
    print(f"Total tasks   : {summary['total_tasks']}")
    print(f"Total minutes : {summary['total_minutes']}")
    print("By priority   :")
    for level, count in summary["by_priority"].items():
        print(f"  {level.upper():<8}: {count}")


if __name__ == "__main__":
    main()
