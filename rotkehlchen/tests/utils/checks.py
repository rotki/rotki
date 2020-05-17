from typing import Dict

from rotkehlchen.fval import FVal


def assert_serialized_dicts_equal(a: Dict, b: Dict) -> None:
    """Compares serialized dicts so that serialized numbers can be compared for equality"""
    assert len(a) == len(b), f"Dicts don't have the same key length {len(a)} != {len(b)}"
    for a_key, a_val in a.items():
        if isinstance(a_val, FVal):
            try:
                compare_val = FVal(b[a_key])
            except ValueError:
                raise AssertionError(f'Could not turn {a_key} value {b[a_key]} into an FVal')
            assert compare_val == a_val, f"{a_key} doesn't match. {compare_val} != {a_val}"
        elif isinstance(b[a_key], FVal):
            try:
                compare_val = FVal(a_val)
            except ValueError:
                raise AssertionError(f'Could not turn {a_key} value {a[a_key]} into an FVal')
            assert compare_val == b[a_key], f"{a_key} doesn't match. {compare_val} != {b[a_key]}"
        else:
            assert a_val == b[a_key], f"{a_key} doesn't match. {a_val} != {b[a_key]}"
