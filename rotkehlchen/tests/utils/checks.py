from typing import Dict, List, Optional

from rotkehlchen.fval import FVal


def assert_serialized_lists_equal(
        a: List,
        b: List,
        max_length_to_check: Optional[int] = None,
        ignore_keys: Optional[List] = None,
        length_list_keymap: Optional[Dict] = None,
) -> None:
    """Compares lists of serialized dicts"""
    assert isinstance(a, list), "Expected 2 lists. Comparing {type(a)} to {type(b)}"
    assert isinstance(b, list), "Expected 2 lists. Comparing {type(a)} to {type(b)}"
    if not max_length_to_check:
        assert len(a) == len(b), f"Lists don't have the same key length {len(a)} != {len(b)}"
    for idx, a_entry in enumerate(a):
        if max_length_to_check and idx + 1 > max_length_to_check:
            break
        assert_serialized_dicts_equal(
            a=a_entry,
            b=b[idx],
            ignore_keys=ignore_keys,
            length_list_keymap=length_list_keymap,
        )


def assert_serialized_dicts_equal(
        a: Dict,
        b: Dict,
        ignore_keys: Optional[List] = None,
        length_list_keymap: Optional[Dict] = None,
) -> None:
    """Compares serialized dicts so that serialized numbers can be compared for equality"""
    assert len(a) == len(b), f"Dicts don't have the same key length {len(a)} != {len(b)}"
    for a_key, a_val in a.items():

        if ignore_keys and a_key in ignore_keys:
            continue

        if isinstance(a_val, FVal):
            try:
                compare_val = FVal(b[a_key])
            except ValueError:
                raise AssertionError(f'Could not turn {a_key} value {b[a_key]} into an FVal')
            assert compare_val.is_close(a_val), f"{a_key} doesn't match. {compare_val} != {a_val}"
        elif isinstance(b[a_key], FVal):
            try:
                compare_val = FVal(a_val)
            except ValueError:
                raise AssertionError(f'Could not turn {a_key} value {a[a_key]} into an FVal')
            msg = f"{a_key} doesn't match. {compare_val} != {b[a_key]}"
            assert compare_val.is_close(b[a_key]), msg
        elif isinstance(a_val, list):
            max_length_to_check = None
            if length_list_keymap and a_key in length_list_keymap:
                max_length_to_check = length_list_keymap[a_key]
            assert_serialized_lists_equal(
                a=a_val,
                b=b[a_key],
                max_length_to_check=max_length_to_check,
                ignore_keys=ignore_keys,
                length_list_keymap=length_list_keymap,
            )
        else:
            assert a_val == b[a_key], f"{a_key} doesn't match. {a_val} != {b[a_key]}"
