"""
PawPal+ — backend logic layer.

Classes
-------
Task      : a single care action for a pet (feeding, walk, medication, appointment)
Pet       : a pet with its profile and associated tasks
Owner     : an owner who manages one or more pets
Scheduler : builds and explains a daily care plan for an owner's pets
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskType(str, Enum):
    FEEDING = "feeding"
    WALK = "walk"
    MEDICATION = "medication"
    APPOINTMENT = "appointment"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """Represents a single pet-care action.

    Attributes
    ----------
    title            : human-readable name, e.g. "Morning walk"
    task_type        : category drawn from TaskType
    duration_minutes : how long the task takes
    priority         : LOW / MEDIUM / HIGH
    scheduled_time   : wall-clock time the task should start (None = flexible)
    pet_name         : name of the pet this task belongs to (set by Pet)
    is_recurring     : True if the task repeats every day
    notes            : any extra context (medication dosage, vet address, …)
    completed        : True if the task has been marked done
    """

    title: str
    task_type: TaskType
    duration_minutes: int
    priority: Priority = Priority.MEDIUM
    scheduled_time: Optional[time] = None
    pet_name: str = ""
    is_recurring: bool = False
    notes: str = ""
    completed: bool = False

    # ------------------------------------------------------------------
    # Derived / helper methods
    # ------------------------------------------------------------------

    def priority_score(self) -> int:
        """Return a numeric score so tasks can be sorted (higher = sooner)."""
        scores = {Priority.HIGH: 3, Priority.MEDIUM: 2, Priority.LOW: 1}
        return scores[self.priority]

    def is_fixed_time(self) -> bool:
        """Return True when the task has a hard scheduled start time."""
        return self.scheduled_time is not None

    def summary(self) -> str:
        """Return a one-line human-readable description of this task."""
        priority_label = f"[{self.priority.value.upper()}]"
        type_label = f"({self.task_type.value})"
        duration_label = f"— {self.duration_minutes} min"
        if self.scheduled_time is not None:
            time_label = f"@ {self.scheduled_time.strftime('%H:%M')}"
        else:
            time_label = "[flexible]"
        pet_label = f"[{self.pet_name}]" if self.pet_name else ""
        parts = [priority_label, self.title, type_label, duration_label, time_label]
        if pet_label:
            parts.append(pet_label)
        return " ".join(parts)

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    """Represents a pet and its care needs.

    Attributes
    ----------
    name    : pet's name
    species : e.g. "dog", "cat", "rabbit"
    breed   : optional breed string
    age     : age in years (float allows e.g. 0.5 for a six-month-old)
    tasks   : list of Task objects assigned to this pet
    """

    name: str
    species: str
    breed: str = ""
    age: float = 0.0
    tasks: list[Task] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Task management
    # ------------------------------------------------------------------

    def add_task(self, task: Task) -> None:
        """Attach a Task to this pet, stamping its pet_name."""
        task.pet_name = self.name
        self.tasks.append(task)

    def remove_task(self, title: str) -> bool:
        """Remove a task by title. Return True if found and removed."""
        for task in self.tasks:
            if task.title == title:
                self.tasks.remove(task)
                return True
        return False

    def get_tasks_by_priority(self) -> list[Task]:
        """Return tasks sorted highest-priority first."""
        return sorted(self.tasks, key=lambda t: t.priority_score(), reverse=True)

    def get_tasks_by_type(self, task_type: TaskType) -> list[Task]:
        """Return all tasks matching the given TaskType."""
        return [t for t in self.tasks if t.task_type == task_type]


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    """Represents the pet owner who manages one or more pets.

    Attributes
    ----------
    name        : owner's display name
    email       : contact e-mail (optional)
    pets        : list of Pet objects this owner manages
    preferences : free-form dict for owner settings
                  (e.g. {"preferred_walk_time": "07:00", "max_daily_hours": 3})
    """

    name: str
    email: str = ""
    pets: list[Pet] = field(default_factory=list)
    preferences: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Pet management
    # ------------------------------------------------------------------

    def add_pet(self, pet: Pet) -> None:
        """Add a Pet to this owner's roster."""
        self.pets.append(pet)

    def remove_pet(self, pet_name: str) -> bool:
        """Remove a pet by name. Return True if found and removed."""
        for pet in self.pets:
            if pet.name == pet_name:
                self.pets.remove(pet)
                return True
        return False

    def get_pet(self, pet_name: str) -> Optional[Pet]:
        """Look up a pet by name; return None if not found."""
        for pet in self.pets:
            if pet.name == pet_name:
                return pet
        return None

    def all_tasks(self) -> list[Task]:
        """Return every task across all of this owner's pets."""
        result = []
        for pet in self.pets:
            result.extend(pet.tasks)
        return result


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """Builds and explains a daily care plan for an owner's pets.

    The scheduler:
    - collects all tasks from the owner's pets
    - sorts them by priority and fixed start-times
    - detects time conflicts between tasks
    - produces an ordered, annotated daily schedule
    """

    def __init__(self, owner: Owner) -> None:
        """Initialise the scheduler with an Owner and an empty schedule."""
        self.owner = owner
        self._schedule: list[Task] = []   # ordered list produced by build_schedule

    # ------------------------------------------------------------------
    # Core scheduling methods
    # ------------------------------------------------------------------

    def build_schedule(self) -> list[Task]:
        """Sort and arrange all tasks into a conflict-free daily plan.

        Returns the ordered list of scheduled tasks.
        """
        self._schedule = self.get_sorted_tasks()
        return self._schedule

    def detect_conflicts(self, tasks: list[Task]) -> list[tuple[Task, Task]]:
        """Return pairs of tasks whose time windows overlap."""
        fixed = [t for t in tasks if t.is_fixed_time()]
        conflicts = []
        for i in range(len(fixed)):
            for j in range(i + 1, len(fixed)):
                a, b = fixed[i], fixed[j]
                # Convert scheduled_time to minutes-since-midnight for comparison
                a_start = a.scheduled_time.hour * 60 + a.scheduled_time.minute
                a_end = a_start + a.duration_minutes
                b_start = b.scheduled_time.hour * 60 + b.scheduled_time.minute
                b_end = b_start + b.duration_minutes
                # Overlap when one starts before the other ends
                if a_start < b_end and b_start < a_end:
                    conflicts.append((a, b))
        return conflicts

    def get_sorted_tasks(self) -> list[Task]:
        """Return all owner tasks sorted: fixed-time first, then by priority score."""
        all_tasks = self.owner.all_tasks()
        fixed = sorted(
            [t for t in all_tasks if t.is_fixed_time()],
            key=lambda t: t.scheduled_time,
        )
        flexible = sorted(
            [t for t in all_tasks if not t.is_fixed_time()],
            key=lambda t: t.priority_score(),
            reverse=True,
        )
        return fixed + flexible

    # ------------------------------------------------------------------
    # Explanation / display
    # ------------------------------------------------------------------

    def explain_plan(self) -> str:
        """Return a human-readable explanation of the current schedule."""
        if not self._schedule:
            self.build_schedule()
        lines = [f"=== Today's Schedule for {self.owner.name} ==="]
        for i, task in enumerate(self._schedule, start=1):
            lines.append(f"{i}. {task.summary()}")
        return "\n".join(lines)

    def daily_summary(self) -> dict:
        """Return a summary dict: total tasks, total minutes, tasks by priority."""
        if not self._schedule:
            self.build_schedule()
        tasks = self._schedule
        total_tasks = len(tasks)
        total_minutes = sum(t.duration_minutes for t in tasks)
        by_priority: dict[str, int] = {}
        for t in tasks:
            key = t.priority.value
            by_priority[key] = by_priority.get(key, 0) + 1
        conflict_pairs = self.detect_conflicts(tasks)
        conflicts = [(a.title, b.title) for a, b in conflict_pairs]
        return {
            "total_tasks": total_tasks,
            "total_minutes": total_minutes,
            "by_priority": by_priority,
            "conflicts": conflicts,
        }
