"""Buggy fixture module containing seeded defects."""

import os


def calculate_average(numbers: list[float]) -> float:
    """Calculate mean of numbers, buggy when numbers is empty."""
    return sum(numbers) / len(numbers)


def append_to_list(val: int, items: list[int] = []) -> list[int]:
    """Append to list with mutable default argument."""
    items.append(val)
    return items


def run_user_script(cmd: str) -> None:
    """Execute command unsafely using os.system."""
    os.system(cmd)


def silent_operation(val: int) -> int:
    """Perform operation with swallowed exception."""
    try:
        return 100 // val
    except Exception:
        pass
    return 0
