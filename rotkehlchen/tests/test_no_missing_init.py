import os
import warnings as test_warnings
from contextlib import suppress


def find_directories_with_missing_init(path: str) -> set[str]:
    package_dirs: set[str] = set()
    py_directories: set[str] = set()
    for root, dirs, files in os.walk(path):
        with suppress(ValueError):
            dirs.remove("__pycache__")

        for name in files:
            if name == "__init__.py":
                package_dirs.add(root)
            if name.endswith(".py"):
                py_directories.add(root)

    return py_directories - package_dirs


def test_no_missing_init():
    """Test that there is no directories missing an __init__.py file

    The reason for this is some linting tools like mypy and pylint don't check the
    directories that are missing the files.
    """

    rotki_path = os.path.abspath(os.path.join(os.path.abspath(__file__), "..", ".."))
    directories_with_missing_init = find_directories_with_missing_init(rotki_path)

    if directories_with_missing_init:
        for directory in directories_with_missing_init:
            test_warnings.warn(UserWarning(
                f'Found directory {directory} missing an init',
            ))

    assert not directories_with_missing_init, "some directories are missing __init__.py files"
