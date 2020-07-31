from typing import Dict, List, Optional

from rotkehlchen.fval import FVal


def assert_serialized_lists_equal(
        a: List,
        b: List,
        max_length_to_check: Optional[int] = None,
        ignore_keys: Optional[List] = None,
        length_list_keymap: Optional[Dict] = None,
        max_diff: str = "1e-6",
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
            max_diff=max_diff,
        )


def assert_serialized_dicts_equal(
        a: Dict,
        b: Dict,
        ignore_keys: Optional[List] = None,
        length_list_keymap: Optional[Dict] = None,
        max_diff: str = "1e-6",
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
                raise AssertionError(f'Could not turn {a_key} amount {b[a_key]} into an FVal')
            msg = f"{a_key} amount doesn't match. {compare_val} != {a_val}"
            assert compare_val.is_close(a_val, max_diff=max_diff), msg
        elif isinstance(b[a_key], FVal):
            try:
                compare_val = FVal(a_val)
            except ValueError:
                raise AssertionError(f'Could not turn {a_key} value {a[a_key]} into an FVal')
            msg = f"{a_key} doesn't match. {compare_val} != {b[a_key]}"
            assert compare_val.is_close(b[a_key], max_diff=max_diff), msg
        elif isinstance(a_val, str) and isinstance(b[a_key], str):
            if a_val == b[a_key]:
                continue

            # if strings are not equal, try to turn them to Fvals
            try:
                afval = FVal(a_val)
            except ValueError:
                raise AssertionError(
                    f'After string comparison failure could not turn {a_val} to a number',
                )

            try:
                bfval = FVal(b[a_key])
            except ValueError:
                raise AssertionError(
                    f'After string comparison failure could not turn {b[a_key]} to a number',
                )
            msg = f"{a_key} doesn't match. {afval} != {bfval}"
            assert afval.is_close(bfval, max_diff=max_diff), msg

        elif isinstance(a_val, dict) and 'amount' in a_val and 'usd_value' in a_val:
            assert 'amount' in b[a_key]
            assert 'usd_value' in b[a_key]

            try:
                compare_val = FVal(b[a_key]['amount'])
            except ValueError:
                raise AssertionError(f'Could not turn {a_key} amount {b[a_key]} into an FVal')
            msg = f"{a_key} amount doesn't match. {compare_val} != {a_val['amount']}"
            assert compare_val.is_close(a_val['amount'], max_diff=max_diff), msg

            try:
                compare_val = FVal(b[a_key]['usd_value'])
            except ValueError:
                raise AssertionError(f'Could not turn {a_key} usd_value {b[a_key]} into an FVal')
            msg = f"{a_key} usd_value doesn't match. {compare_val} != {a_val['usd_value']}"
            assert compare_val.is_close(a_val['usd_value'], max_diff=max_diff), msg
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
