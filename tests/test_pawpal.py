"""
Pytest test suite for PawPal+ (Phase 2 + Phase 5).

Test plan
---------
Happy paths
  - Task completion flips the completed flag
  - Priority scores are ordered HIGH > MEDIUM > LOW
  - Adding a task to a pet stamps pet_name and increments task count
  - Owner.all_tasks() flattens tasks across multiple pets
  - Scheduler detects overlapping fixed-time tasks
  - Scheduler correctly passes non-overlapping tasks through with no conflict

Edge cases
  - Pet with no tasks returns empty list from filter / sort
  - Scheduler with no tasks builds an empty schedule
  - Recurring task renewal produces a fresh copy and keeps the original marked done
  - Completing a non-recurring task does NOT add a renewal
  - sort_by_time puts fixed-time tasks before flexible ones, in chronological order
  - filter_tasks(completed=False) excludes completed tasks
  - filter_tasks(pet_name=...) returns only that pet's tasks
  - conflict_warnings returns human-readable strings (not raw tuples)
  - Tasks at identical start times are flagged as conflicts
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
    is_recurring: bool = False,
) -> Task:
    """Convenience factory for creating Task instances in tests."""
    return Task(
        title=title,
        task_type=task_type,
        duration_minutes=duration_minutes,
        priority=priority,
        scheduled_time=scheduled_time,
        is_recurring=is_recurring,
    )


def make_scheduler_with_tasks(*tasks, owner_name="Test Owner", pet_name="Pet") -> tuple:
    """Return (scheduler, pet) pre-loaded with the given tasks."""
    owner = Owner(name=owner_name)
    pet = Pet(name=pet_name, species="dog")
    for t in tasks:
        pet.add_task(t)
    owner.add_pet(pet)
    return Scheduler(owner), pet


# ---------------------------------------------------------------------------
# Task — happy paths
# ---------------------------------------------------------------------------

def test_mark_complete():
    """mark_complete() should set completed to True."""
    task = make_task()
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_priority_score_ordering():
    """HIGH score > MEDIUM score > LOW score."""
    assert make_task(priority=Priority.HIGH).priority_score() > \
           make_task(priority=Priority.MEDIUM).priority_score()
    assert make_task(priority=Priority.MEDIUM).priority_score() > \
           make_task(priority=Priority.LOW).priority_score()


def test_is_fixed_time_true():
    """is_fixed_time() returns True when scheduled_time is set."""
    assert make_task(scheduled_time=time(8, 0)).is_fixed_time() is True


def test_is_fixed_time_false():
    """is_fixed_time() returns False when scheduled_time is None."""
    assert make_task().is_fixed_time() is False


def test_summary_contains_title_and_priority():
    """summary() should include the task title and priority label."""
    task = make_task(title="Morning walk", priority=Priority.HIGH)
    s = task.summary()
    assert "Morning walk" in s
    assert "HIGH" in s


# ---------------------------------------------------------------------------
# Task — renew (recurring logic)
# ---------------------------------------------------------------------------

def test_renew_returns_uncompleted_copy():
    """renew() should produce a new Task with completed=False."""
    task = make_task(title="Daily walk", is_recurring=True)
    task.mark_complete()
    renewed = task.renew()
    assert renewed.completed is False
    assert renewed.title == task.title


def test_renew_does_not_mutate_original():
    """renew() must not change the original task's completed state."""
    task = make_task(is_recurring=True)
    task.mark_complete()
    task.renew()
    assert task.completed is True


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

def test_add_task_increases_count():
    """Adding a task to a pet should increase its task count by one."""
    pet = Pet(name="Buddy", species="dog")
    assert len(pet.tasks) == 0
    pet.add_task(make_task(title="Walk"))
    assert len(pet.tasks) == 1


def test_add_task_stamps_pet_name():
    """add_task() should set task.pet_name to the pet's name."""
    pet = Pet(name="Mochi", species="dog")
    task = make_task()
    pet.add_task(task)
    assert task.pet_name == "Mochi"


def test_pet_no_tasks_sorted_is_empty():
    """get_tasks_by_priority() on a pet with no tasks returns an empty list."""
    pet = Pet(name="Empty", species="cat")
    assert pet.get_tasks_by_priority() == []


def test_get_tasks_by_priority_order():
    """get_tasks_by_priority() should return tasks highest-priority first."""
    pet = Pet(name="Rex", species="dog")
    pet.add_task(make_task(title="Low",  priority=Priority.LOW))
    pet.add_task(make_task(title="High", priority=Priority.HIGH))
    pet.add_task(make_task(title="Med",  priority=Priority.MEDIUM))
    sorted_tasks = pet.get_tasks_by_priority()
    assert sorted_tasks[0].title == "High"
    assert sorted_tasks[-1].title == "Low"


def test_remove_task_returns_true_when_found():
    """remove_task() should return True and shrink the list."""
    pet = Pet(name="Rex", species="dog")
    pet.add_task(make_task(title="Walk"))
    assert pet.remove_task("Walk") is True
    assert len(pet.tasks) == 0


def test_remove_task_returns_false_when_not_found():
    """remove_task() should return False if title doesn't match."""
    pet = Pet(name="Rex", species="dog")
    assert pet.remove_task("Nonexistent") is False


# ---------------------------------------------------------------------------
# Owner
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
    titles = {t.title for t in owner.all_tasks()}
    assert titles == {"Walk Rex", "Feed Whiskers"}


def test_owner_get_pet_returns_none_for_unknown():
    """get_pet() should return None when the name is not found."""
    owner = Owner(name="Jordan")
    assert owner.get_pet("Ghost") is None


def test_owner_remove_pet():
    """remove_pet() should shrink the pets list and return True."""
    owner = Owner(name="Sam")
    owner.add_pet(Pet(name="Dot", species="cat"))
    assert owner.remove_pet("Dot") is True
    assert owner.get_pet("Dot") is None


# ---------------------------------------------------------------------------
# Scheduler — happy paths
# ---------------------------------------------------------------------------

def test_detect_conflicts():
    """Two tasks with overlapping windows should be reported as a conflict."""
    # 07:00–07:30 overlaps with 07:15–07:45
    task_a = make_task(title="Task A", duration_minutes=30, scheduled_time=time(7, 0))
    task_b = make_task(title="Task B", duration_minutes=30, scheduled_time=time(7, 15))
    owner = Owner(name="Test Owner")
    scheduler = Scheduler(owner)
    conflicts = scheduler.detect_conflicts([task_a, task_b])
    assert len(conflicts) == 1
    assert {conflicts[0][0].title, conflicts[0][1].title} == {"Task A", "Task B"}


def test_detect_no_conflicts_for_non_overlapping():
    """Tasks that do not overlap should produce no conflicts."""
    # 07:00–07:30 and 08:00–08:30 are clearly separate
    task_a = make_task(title="Task A", duration_minutes=30, scheduled_time=time(7, 0))
    task_b = make_task(title="Task B", duration_minutes=30, scheduled_time=time(8, 0))
    owner = Owner(name="Test Owner")
    scheduler = Scheduler(owner)
    assert scheduler.detect_conflicts([task_a, task_b]) == []


def test_detect_conflict_same_start_time():
    """Two tasks starting at the exact same time must conflict."""
    task_a = make_task(title="Feed",  duration_minutes=10, scheduled_time=time(9, 0))
    task_b = make_task(title="Bathe", duration_minutes=20, scheduled_time=time(9, 0))
    owner = Owner(name="Owner")
    conflicts = Scheduler(owner).detect_conflicts([task_a, task_b])
    assert len(conflicts) == 1


def test_build_schedule_empty_owner():
    """Scheduler with no pets / no tasks should build an empty schedule."""
    scheduler = Scheduler(Owner(name="Nobody"))
    schedule = scheduler.build_schedule()
    assert schedule == []


def test_build_schedule_excludes_completed_tasks():
    """Completed tasks should not appear in the built schedule."""
    task = make_task(title="Done task")
    task.mark_complete()
    scheduler, _ = make_scheduler_with_tasks(task)
    schedule = scheduler.build_schedule()
    assert all(not t.completed for t in schedule)


# ---------------------------------------------------------------------------
# Scheduler — sort_by_time
# ---------------------------------------------------------------------------

def test_sort_by_time_fixed_before_flexible():
    """Fixed-time tasks must appear before flexible tasks."""
    flexible = make_task(title="Flexible")
    fixed    = make_task(title="Fixed", scheduled_time=time(9, 0))
    scheduler, _ = make_scheduler_with_tasks(flexible, fixed)
    sorted_tasks = scheduler.sort_by_time()
    assert sorted_tasks[0].title == "Fixed"
    assert sorted_tasks[-1].title == "Flexible"


def test_sort_by_time_chronological_order():
    """Fixed-time tasks should appear in ascending time order."""
    t1 = make_task(title="Evening",   scheduled_time=time(18, 0))
    t2 = make_task(title="Morning",   scheduled_time=time(7, 0))
    t3 = make_task(title="Afternoon", scheduled_time=time(13, 0))
    scheduler, _ = make_scheduler_with_tasks(t1, t2, t3)
    sorted_tasks = scheduler.sort_by_time()
    times = [t.scheduled_time for t in sorted_tasks if t.scheduled_time]
    assert times == sorted(times)


def test_sort_by_time_no_tasks_returns_empty():
    """sort_by_time() on an owner with no tasks returns an empty list."""
    scheduler = Scheduler(Owner(name="Empty"))
    assert scheduler.sort_by_time() == []


# ---------------------------------------------------------------------------
# Scheduler — filter_tasks
# ---------------------------------------------------------------------------

def test_filter_tasks_by_pet_name():
    """filter_tasks(pet_name=...) should return only that pet's tasks."""
    owner = Owner(name="Jordan")
    pet_a = Pet(name="Alpha", species="dog")
    pet_b = Pet(name="Beta",  species="cat")
    pet_a.add_task(make_task(title="Alpha task"))
    pet_b.add_task(make_task(title="Beta task"))
    owner.add_pet(pet_a)
    owner.add_pet(pet_b)
    scheduler = Scheduler(owner)
    result = scheduler.filter_tasks(pet_name="Alpha")
    assert all(t.pet_name == "Alpha" for t in result)
    assert len(result) == 1


def test_filter_tasks_completed_false():
    """filter_tasks(completed=False) should exclude completed tasks."""
    done    = make_task(title="Done")
    pending = make_task(title="Pending")
    done.mark_complete()
    scheduler, _ = make_scheduler_with_tasks(done, pending)
    result = scheduler.filter_tasks(completed=False)
    assert all(not t.completed for t in result)
    assert any(t.title == "Pending" for t in result)


def test_filter_tasks_completed_true():
    """filter_tasks(completed=True) should return only completed tasks."""
    done    = make_task(title="Done")
    pending = make_task(title="Pending")
    done.mark_complete()
    scheduler, _ = make_scheduler_with_tasks(done, pending)
    result = scheduler.filter_tasks(completed=True)
    assert all(t.completed for t in result)


# ---------------------------------------------------------------------------
# Scheduler — complete_task / recurring renewal
# ---------------------------------------------------------------------------

def test_complete_task_recurring_adds_renewal():
    """Completing a recurring task should add a fresh copy to the pet."""
    task = make_task(title="Daily walk", is_recurring=True)
    scheduler, pet = make_scheduler_with_tasks(task)
    initial_count = len(pet.tasks)
    scheduler.complete_task(task)
    assert len(pet.tasks) == initial_count + 1


def test_complete_task_recurring_original_stays_complete():
    """After complete_task, the original task must remain completed."""
    task = make_task(title="Daily walk", is_recurring=True)
    scheduler, _ = make_scheduler_with_tasks(task)
    scheduler.complete_task(task)
    assert task.completed is True


def test_complete_task_non_recurring_no_renewal():
    """Completing a non-recurring task must NOT add a new task."""
    task = make_task(title="One-off task", is_recurring=False)
    scheduler, pet = make_scheduler_with_tasks(task)
    initial_count = len(pet.tasks)
    result = scheduler.complete_task(task)
    assert result is None
    assert len(pet.tasks) == initial_count


def test_complete_task_renewal_not_in_schedule():
    """After renewal, the completed original should not appear in the schedule."""
    task = make_task(title="Daily walk", is_recurring=True)
    scheduler, _ = make_scheduler_with_tasks(task)
    scheduler.complete_task(task)
    assert all(not t.completed for t in scheduler._schedule)


# ---------------------------------------------------------------------------
# Scheduler — conflict_warnings
# ---------------------------------------------------------------------------

def test_conflict_warnings_returns_strings():
    """conflict_warnings() should return a list of strings, not tuples."""
    task_a = make_task(title="A", duration_minutes=30, scheduled_time=time(7, 0))
    task_b = make_task(title="B", duration_minutes=30, scheduled_time=time(7, 10))
    scheduler, _ = make_scheduler_with_tasks(task_a, task_b)
    warnings = scheduler.conflict_warnings()
    assert len(warnings) > 0
    assert all(isinstance(w, str) for w in warnings)


def test_conflict_warnings_empty_when_no_conflicts():
    """conflict_warnings() should return [] when no tasks overlap."""
    task_a = make_task(title="A", duration_minutes=30, scheduled_time=time(7, 0))
    task_b = make_task(title="B", duration_minutes=30, scheduled_time=time(9, 0))
    scheduler, _ = make_scheduler_with_tasks(task_a, task_b)
    assert scheduler.conflict_warnings() == []
