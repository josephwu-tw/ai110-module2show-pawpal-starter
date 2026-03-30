"""
PawPal+ — demo script for Phase 2.

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


def main() -> None:
    # ------------------------------------------------------------------
    # Build owner
    # ------------------------------------------------------------------
    jordan = Owner(
        name="Jordan",
        preferences={"preferred_walk_time": "07:00", "max_daily_hours": 3},
    )

    # ------------------------------------------------------------------
    # Build pets
    # ------------------------------------------------------------------
    mochi = Pet(name="Mochi", species="dog", breed="Golden Retriever", age=2)
    noodle = Pet(name="Noodle", species="cat", breed="Tabby", age=4)

    # ------------------------------------------------------------------
    # Add tasks for Mochi
    # ------------------------------------------------------------------
    mochi.add_task(Task(
        title="Morning walk",
        task_type=TaskType.WALK,
        duration_minutes=30,
        priority=Priority.HIGH,
        scheduled_time=time(7, 0),
        is_recurring=True,
    ))
    mochi.add_task(Task(
        title="Evening feeding",
        task_type=TaskType.FEEDING,
        duration_minutes=15,
        priority=Priority.HIGH,
        scheduled_time=time(18, 0),
        is_recurring=True,
    ))
    mochi.add_task(Task(
        title="Flea medication",
        task_type=TaskType.MEDICATION,
        duration_minutes=5,
        priority=Priority.MEDIUM,
        notes="Apply between shoulder blades",
    ))

    # ------------------------------------------------------------------
    # Add tasks for Noodle
    # ------------------------------------------------------------------
    noodle.add_task(Task(
        title="Morning feeding",
        task_type=TaskType.FEEDING,
        duration_minutes=10,
        priority=Priority.HIGH,
        scheduled_time=time(7, 30),
        is_recurring=True,
    ))
    noodle.add_task(Task(
        title="Vet checkup",
        task_type=TaskType.APPOINTMENT,
        duration_minutes=60,
        priority=Priority.HIGH,
        scheduled_time=time(10, 0),
        notes="Annual wellness exam",
    ))
    noodle.add_task(Task(
        title="Playtime",
        task_type=TaskType.OTHER,
        duration_minutes=20,
        priority=Priority.LOW,
    ))

    # ------------------------------------------------------------------
    # Register pets with owner
    # ------------------------------------------------------------------
    jordan.add_pet(mochi)
    jordan.add_pet(noodle)

    # ------------------------------------------------------------------
    # Build schedule and display results
    # ------------------------------------------------------------------
    scheduler = Scheduler(jordan)
    scheduler.build_schedule()

    print(scheduler.explain_plan())

    print()
    print("=== Daily Summary ===")
    summary = scheduler.daily_summary()
    print(f"Total tasks   : {summary['total_tasks']}")
    print(f"Total minutes : {summary['total_minutes']}")
    print("By priority   :")
    for priority_level, count in summary["by_priority"].items():
        print(f"  {priority_level.upper():<8}: {count}")

    print()
    conflicts = summary["conflicts"]
    if conflicts:
        print("=== Detected Conflicts ===")
        for pair in conflicts:
            print(f"  - '{pair[0]}' overlaps with '{pair[1]}'")
    else:
        print("=== No Schedule Conflicts Detected ===")


if __name__ == "__main__":
    main()
