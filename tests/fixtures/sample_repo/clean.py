"""Clean fixture module containing safe code with proper guards."""

import subprocess


def calculate_average_safe(numbers: list[float]) -> float:
    """Safely calculate average with non-empty check."""
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)


def append_to_list_safe(val: int, items: list[int] | None = None) -> list[int]:
    """Safely append to list using None default."""
    if items is None:
        items = []
    items.append(val)
    return items


def run_user_script_safe(cmd: str) -> None:
    """Execute command safely without shell evaluation."""
    subprocess.run(["echo", cmd], shell=False, check=False)

