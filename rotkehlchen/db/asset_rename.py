from sqlite3 import Cursor
from typing import List, Tuple

from rotkehlchen.db.utils import SingleAssetBalance
from rotkehlchen.fval import FVal


def rename_asset_in_timed_balances(
        cursor: Cursor,
        from_name: str,
        to_name: str,
) -> None:

    query = cursor.execute(
        f'SELECT COUNT(*) FROM timed_balances WHERE currency="{to_name}"',
    )
    if query.fetchone()[0] == 0:
        # We are in luck, this means no possibility of merging so executemany
        # should work without any problems
        cursor.execute(
            'UPDATE timed_balances SET currency=? WHERE currency=?',
            (to_name, from_name),
        )
        # go to the next rename pair
        return

    # from here and on treat merging of old and new named balances
    to_balances = []
    query = cursor.execute(
        f'SELECT time, amount, usd_value FROM timed_balances WHERE currency="{to_name}"',
    )
    for entry in query:
        to_balances.append(
            SingleAssetBalance(
                time=entry[0],
                amount=entry[1],
                usd_value=entry[2],
            ),
        )

    from_balances = []
    query = cursor.execute(
        f'SELECT time, amount, usd_value FROM timed_balances WHERE currency="{from_name}"',
    )
    for entry in query:
        from_balances.append(
            SingleAssetBalance(
                time=entry[0],
                amount=entry[1],
                usd_value=entry[2],
            ),
        )

    final_balances = []
    for from_balance in from_balances:
        match_idx = None

        for idx, to_balance in enumerate(to_balances):
            if to_balance.time == from_balance.time:
                match_idx = idx
                break

        if match_idx is not None:
            to_merge_balance = to_balances.pop(match_idx)
            amount = str(
                FVal(to_merge_balance.amount) + FVal(from_balance.amount),
            )
            usd_value = str(
                FVal(to_merge_balance.usd_value) + FVal(from_balance.usd_value),
            )
            from_balance = SingleAssetBalance(
                time=from_balance.time,
                amount=amount,
                usd_value=usd_value,
            )

        final_balances.append(
            (from_balance.time, to_name, from_balance.amount, from_balance.usd_value),
        )

    # If any to_balances remain unmerged, also add them to the final balances
    for to_balance in to_balances:
        final_balances.append(
            (to_balance.time, to_name, to_balance.amount, to_balance.usd_value),
        )

    # now delete all the current DB entries
    cursor.execute(f'DELETE FROM timed_balances WHERE currency="{from_name}"')
    cursor.execute(f'DELETE FROM timed_balances WHERE currency="{to_name}"')
    # and replace with the final merged balances
    cursor.executemany(
        'INSERT INTO timed_balances(time, currency, amount, usd_value) VALUES (?, ?, ?, ?)',
        final_balances,
    )


def rename_assets_in_timed_balances(
        cursor: Cursor,
        rename_pairs: List[Tuple[str, str]],
) -> None:
    """
    This was the easy way. Unfortunately it will throw an integrity error
    if there is a merge of assets. So if there is a `to_name` entry for a
    timestamp for which we also got a `for_name` entry.
    cursor.executemany(
        'UPDATE timed_balances SET currency=? WHERE currency=?',
        changed_symbols,
    )
    """
    for rename_pair in rename_pairs:
        rename_asset_in_timed_balances(
            cursor=cursor,
            from_name=rename_pair[0],
            to_name=rename_pair[1],
        )


def rename_assets_in_db(cursor: Cursor, rename_pairs: List[Tuple[str, str]]) -> None:
    """
    Renames assets in all the relevant tables in the Database.

    Takes a list of tuples in the form:
    [(from_name_1, to_name_1), (from_name_2, to_name_2), ...]

    Good from DB version 1 until now.
    """
    # [(to_name_1, from_name_1), (to_name_2, from_name_2), ...]
    changed_symbols = [(e[1], e[0]) for e in rename_pairs]

    cursor.executemany(
        'UPDATE multisettings SET value=? WHERE value=? and name="ignored_asset";',
        changed_symbols,
    )
    rename_assets_in_timed_balances(cursor, rename_pairs)

    replaced_symbols = [e[0] for e in rename_pairs]
    replaced_symbols_q = ['pair LIKE "%' + s + '%"' for s in replaced_symbols]
    query_str = (
        f'SELECT id, pair, fee_currency FROM trades WHERE fee_currency IN '
        f'({",".join("?"*len(replaced_symbols))}) OR ('
        f'{" OR ".join(replaced_symbols_q)})'
    )
    cursor.execute(query_str, replaced_symbols)
    updated_trades = []
    for q in cursor:
        new_pair = q[1]
        for rename_pair in rename_pairs:
            from_asset = rename_pair[0]
            to_asset = rename_pair[1]

            if from_asset not in q[1] and from_asset != q[2]:
                # It's not this rename pair
                continue

            if from_asset in q[1]:
                new_pair = q[1].replace(from_asset, to_asset)

            new_fee_currency = q[2]
            if from_asset == q[2]:
                new_fee_currency = to_asset

            updated_trades.append((new_pair, new_fee_currency, q[0]))

    cursor.executemany(
        'UPDATE trades SET pair=?, fee_currency=? WHERE id=?',
        updated_trades,
    )
