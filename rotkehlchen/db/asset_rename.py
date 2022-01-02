from sqlite3 import Cursor
from typing import TYPE_CHECKING, List, Tuple

from rotkehlchen.fval import FVal

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def rename_asset_in_timed_balances_before_v21(
        cursor: Cursor,
        from_name: str,
        to_name: str,
) -> None:
    """This function renames assets saved in timed balances before v21

    If we need to rename assets after v21 we need a different version which
    also takes category into account
    """

    query = cursor.execute(
        'SELECT COUNT(*) FROM timed_balances WHERE currency=?', (to_name,),
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
        'SELECT time, amount, usd_value FROM timed_balances WHERE currency=?',
        (to_name,),
    )
    for entry in query:
        to_balances.append((
            entry[0],
            entry[1],
            entry[2],
        ))

    from_balances = []
    query = cursor.execute(
        'SELECT time, amount, usd_value  FROM timed_balances WHERE currency=?',
        (from_name,),
    )
    for entry in query:
        from_balances.append((
            entry[0],
            entry[1],
            entry[2],
        ))

    final_balances = []
    for from_balance in from_balances:
        match_idx = None

        for idx, to_balance in enumerate(to_balances):
            if to_balance[0] == from_balance[0]:  # same time
                match_idx = idx
                break

        if match_idx is not None:
            to_merge_balance = to_balances.pop(match_idx)
            amount = str(
                FVal(to_merge_balance[1]) + FVal(from_balance[1]),
            )
            usd_value = str(
                FVal(to_merge_balance[2]) + FVal(from_balance[2]),
            )
            from_balance = (from_balance[0], amount, usd_value)

        final_balances.append((
            from_balance[0],  # time
            to_name,
            from_balance[1],  # amount
            from_balance[2],  # usd_value
        ))

    # If any to_balances remain unmerged, also add them to the final balances
    for to_balance in to_balances:
        final_balances.append((
            to_balance[0],  # time
            to_name,
            to_balance[1],  # amount
            to_balance[2],  # usd_value
        ))

    # now delete all the current DB entries
    cursor.execute('DELETE FROM timed_balances WHERE currency=?', (from_name,))
    cursor.execute('DELETE FROM timed_balances WHERE currency=?', (to_name,))
    # and replace with the final merged balances
    cursor.executemany(
        'INSERT INTO timed_balances(time, currency, amount, usd_value) VALUES (?, ?, ?, ?)',  # noqa: E501
        final_balances,
    )


def rename_assets_in_timed_balances_before_v21(
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

    Would need to use a different function if we rename assets after v21
    """
    for rename_pair in rename_pairs:
        rename_asset_in_timed_balances_before_v21(
            cursor=cursor,
            from_name=rename_pair[0],
            to_name=rename_pair[1],
        )


def rename_assets_in_db(db: 'DBHandler', rename_pairs: List[Tuple[str, str]]) -> None:
    """
    Renames assets in all the relevant tables in the Database.

    Takes a list of tuples in the form:
    [(from_name_1, to_name_1), (from_name_2, to_name_2), ...]

    Good from DB version 1 until now.
    """
    cursor = db.conn.cursor()
    # [(to_name_1, from_name_1), (to_name_2, from_name_2), ...]
    changed_symbols = [(e[1], e[0]) for e in rename_pairs]

    cursor.executemany(
        'UPDATE multisettings SET value=? WHERE value=? and name="ignored_asset";',
        changed_symbols,
    )
    db_version = db.get_version()
    if db_version <= 20:
        rename_assets_in_timed_balances_before_v21(cursor, rename_pairs)
    else:
        raise NotImplementedError('Need to implement asset renaming during upgrade for > v21')

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
