"""
Pytest test suite for PawPal+ Phase 2.
"""

from datetime import time

import pytest

from pawpal_system import (
    Owner,
    Pet,
    Priority,
    Scheduler,
    Task,
    TaskType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_task(
    title: str = "Test task",
    task_type: TaskType = TaskType.OTHER,
    duration_minutes: int = 30,
    priority: Priority = Priority.MEDIUM,
    scheduled_time=None,
) -> Task:
    """Convenience factory for creating Task instances in tests."""
    return Task(
        title=title,
        task_type=task_type,
        duration_minutes=duration_minutes,
        priority=priority,
        scheduled_time=scheduled_time,
    )


# ---------------------------------------------------------------------------
# Task tests
# ---------------------------------------------------------------------------

def test_mark_complete():
    """mark_complete() should set completed to True."""
    task = make_task()
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_priority_score_ordering():
    """HIGH score > MEDIUM score > LOW score."""
    high_task = make_task(priority=Priority.HIGH)
    med_task = make_task(priority=Priority.MEDIUM)
    low_task = make_task(priority=Priority.LOW)
    assert high_task.priority_score() > med_task.priority_score()
    assert med_task.priority_score() > low_task.priority_score()


# ---------------------------------------------------------------------------
# Pet tests
# ---------------------------------------------------------------------------

def test_add_task_increases_count():
    """Adding a task to a pet should increase its task count by one."""
    pet = Pet(name="Buddy", species="dog")
    assert len(pet.tasks) == 0
    pet.add_task(make_task(title="Walk"))
    assert len(pet.tasks) == 1


# ---------------------------------------------------------------------------
# Scheduler tests
# ---------------------------------------------------------------------------

def test_detect_conflicts():
    """Two tasks with overlapping time windows should be reported as a conflict."""
    # Task A: 07:00 for 30 min  -> 07:00–07:30
    # Task B: 07:15 for 30 min  -> 07:15–07:45  (overlaps A)
    task_a = make_task(title="Task A", duration_minutes=30, scheduled_time=time(7, 0))
    task_b = make_task(title="Task B", duration_minutes=30, scheduled_time=time(7, 15))

    owner = Owner(name="Test Owner")
    scheduler = Scheduler(owner)

    conflicts = scheduler.detect_conflicts([task_a, task_b])
    assert len(conflicts) == 1
    titles = {conflicts[0][0].title, conflicts[0][1].title}
    assert titles == {"Task A", "Task B"}


def test_detect_no_conflicts_for_non_overlapping():
    """Tasks that do not overlap should not produce conflicts."""
    # Task A: 07:00 for 30 min  -> 07:00–07:30
    # Task B: 08:00 for 30 min  -> 08:00–08:30  (no overlap)
    task_a = make_task(title="Task A", duration_minutes=30, scheduled_time=time(7, 0))
    task_b = make_task(title="Task B", duration_minutes=30, scheduled_time=time(8, 0))

    owner = Owner(name="Test Owner")
    scheduler = Scheduler(owner)

    conflicts = scheduler.detect_conflicts([task_a, task_b])
    assert conflicts == []


# ---------------------------------------------------------------------------
# Owner tests
# ---------------------------------------------------------------------------

def test_owner_all_tasks():
    """all_tasks() should return every task from every pet."""
    owner = Owner(name="Alex")

    pet1 = Pet(name="Rex", species="dog")
    pet1.add_task(make_task(title="Walk Rex"))

    pet2 = Pet(name="Whiskers", species="cat")
    pet2.add_task(make_task(title="Feed Whiskers"))

    owner.add_pet(pet1)
    owner.add_pet(pet2)

    all_tasks = owner.all_tasks()
    assert len(all_tasks) == 2
    titles = {t.title for t in all_tasks}
    assert titles == {"Walk Rex", "Feed Whiskers"}
