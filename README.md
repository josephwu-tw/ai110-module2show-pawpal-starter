# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Smarter Scheduling

PawPal+ includes four algorithmic features beyond basic task storage:

| Feature | Method | What it does |
|---|---|---|
| **Time-based sorting** | `Scheduler.sort_by_time()` | Orders all pending tasks chronologically — fixed-time tasks first (ascending by start time), then flexible tasks by priority score descending. Uses Python's `sorted()` with a `lambda` key on `time` objects. |
| **Flexible filtering** | `Scheduler.filter_tasks(pet_name, completed)` | Filters the owner's task pool by pet name and/or completion status. Accepts `None` for either argument to skip that filter, making it composable. |
| **Recurring task renewal** | `Scheduler.complete_task(task)` | Marks a task done and, if `is_recurring=True`, calls `Task.renew()` to produce a fresh uncompleted copy and re-registers it on the pet. The schedule is rebuilt automatically so the renewed task appears immediately. |
| **Conflict detection** | `Scheduler.conflict_warnings()` | Compares time windows (start + duration in minutes) for all fixed-time pending tasks and returns human-readable warning strings for every overlap. Returns an empty list when no conflicts exist — never crashes. |

## Testing PawPal+

Run the full test suite with:

```bash
python -m pytest
```

The suite lives in `tests/test_pawpal.py` and covers **33 tests** across all four classes:

| Area | What's tested |
|---|---|
| `Task` | Completion flag, priority score ordering, `is_fixed_time`, `summary` output, `renew` immutability |
| `Pet` | Task stamping, count changes, priority sort order, `remove_task` happy/not-found paths, empty-pet edge case |
| `Owner` | Task flattening across pets, `get_pet` miss, `remove_pet` |
| `Scheduler` | Conflict detection (overlap, same-time, no-overlap), empty schedule, completed-task exclusion, `sort_by_time` ordering, `filter_tasks` by pet/status, recurring renewal, `conflict_warnings` format |

**Confidence level: ★★★★☆**
All happy paths and the main edge cases (no tasks, identical start times, non-recurring tasks, renewal immutability) are covered. Areas not yet tested: owner preferences affecting schedule order, multi-day recurrence windows, and UI-layer state management.

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
