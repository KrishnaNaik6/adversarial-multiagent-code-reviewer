"""Standalone test runner harness executed inside the isolated sandbox."""

import importlib.util
import inspect
import sys
import traceback


def main() -> None:
    """Run tests in specified file via pytest or direct inspection."""
    if len(sys.argv) < 2:
        print("Usage: python harness.py <test_file>", file=sys.stderr)
        sys.exit(2)

    test_file = sys.argv[1]

    # Try executing via pytest if installed
    try:
        import pytest

        sys.exit(pytest.main([test_file, "-q", "--no-header"]))
    except ImportError:
        pass

    # Fallback to direct Python test execution
    try:
        spec = importlib.util.spec_from_file_location("test_module", test_file)
        if spec is None or spec.loader is None:
            print(f"Could not load test file: {test_file}", file=sys.stderr)
            sys.exit(2)

        module = importlib.util.module_from_spec(spec)
        sys.modules["test_module"] = module
        spec.loader.exec_module(module)
    except Exception:
        traceback.print_exc()
        sys.exit(1)

    test_functions = [
        obj
        for name, obj in inspect.getmembers(module)
        if inspect.isfunction(obj) and name.startswith("test_")
    ]

    if not test_functions:
        print("No test functions found in test file.", file=sys.stderr)
        sys.exit(2)

    passed = 0
    for func in test_functions:
        try:
            func()
            passed += 1
        except Exception:
            print("=================================== FAILURES ===================================")
            print(f"_________________________ {func.__name__} _________________________")
            traceback.print_exc()
            sys.exit(1)

    print(f"{passed} passed in 0.01s")
    sys.exit(0)


if __name__ == "__main__":
    main()

