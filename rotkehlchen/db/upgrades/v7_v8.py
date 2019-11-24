from typing import TYPE_CHECKING, Union

from rotkehlchen.crypto import sha3
from rotkehlchen.db.upgrades.v6_v7 import (
    v6_deserialize_location_from_db,
    v6_deserialize_trade_type_from_db,
    v6_generate_trade_id,
)
from rotkehlchen.errors import DBUpgradeError
from rotkehlchen.typing import AssetMovementCategory, Location

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


MCDAI_LAUNCH_TS = 1574035200

# https://blog.kraken.com/post/3061/kraken-is-supporting-dais-multi-collateral-upgrade/
# November 18th, 14:00 UTC
# For Kraken any DAI trade before this date is SAI and after it, should be MCDAI (DAI)
KRAKEN_DAI_UPGRADE_TS = 1574085600

# https://support.coinbase.com/customer/portal/articles/2982947
# Between November 18 and December 2 any MCDAI sent to Coinbase will be stored in temporary
# MCDAI wallet. Any DAI sent after November 18 will be shown as DAI. On December 2nd all Single
# collateral DAI will be turned to Multicollateral and DAI will mean the multicollateral
# counterpart MCDAI will cease to exist. After December 2nd any single collateral DAI
# sent to coinbase will be shown as SAI. SAI support may be dropped from Coinbase at any time.
COINBASE_DAI_UPGRADE_TS = MCDAI_LAUNCH_TS

# https://bittrex.zendesk.com/hc/en-us/articles/360035866431-Support-for-the-Dai-DAI-Multi-Collateral-Dai-Upgrade
# After November 18 DAI is renamed to SAI and both pairs exist in the exchange.
BITTREX_DAI_UPGRADE_TS = MCDAI_LAUNCH_TS


def v7_deserialize_asset_movement_category(symbol: str) -> AssetMovementCategory:
    """We copy the deserialize_asset_movement_category_from_db() function at v6

    This is done in case the function ever changes in the future. Also another
    difference is that instead of DeserializationError this throws a DBUpgradeError
    """
    if not isinstance(symbol, str):
        raise DBUpgradeError(
            f'Failed to deserialize asset movement category symbol from '
            f'{type(symbol)} DB enum entry',
        )

    if symbol == 'A':
        return AssetMovementCategory.DEPOSIT
    elif symbol == 'B':
        return AssetMovementCategory.WITHDRAWAL

    # else
    raise DBUpgradeError(
        f'Failed to deserialize asset movement category symbol from DB enum entry.'
        f'Unknown symbol {symbol}',
    )


def v7_generate_asset_movement_id(
        location: Location,
        category: AssetMovementCategory,
        time: Union[str, int],
        asset: str,
        fee_asset: str,
        link: str,
) -> str:
    """We copy the identifier() property of an asset movement at v7

    This is done in case the function ever changes in the future.
    """
    source_str = (
        str(location) +
        str(category) +
        str(time) +
        asset +
        fee_asset +
        link
    )
    return sha3(source_str).hex()


def _upgrade_asset_movements_table(db: 'DBHandler') -> None:
    """Upgrade the deposits/withdrawals for DAI->SAI renaming"""
    cursor = db.conn.cursor()
    # This is the data we need from asset_movements table at v7
    query = cursor.execute(
        'SELECT id,'
        '  location,'
        '  category,'
        '  time,'
        '  asset,'
        '  amount,'
        '  fee_asset,'
        '  fee,'
        '  link FROM asset_movements ',
    )

    entries_to_edit = []
    for result in query:
        old_id = result[0]
        db_location = result[1]
        db_category = result[2]
        time = int(result[3])
        asset = result[4]
        amount = result[5]
        fee_asset = result[6]
        fee = result[7]
        link = result[8]

        should_edit = time < MCDAI_LAUNCH_TS and (asset == 'DAI' or fee_asset == 'DAI')
        if should_edit:
            # Delete old asset movement from the DB
            cursor.execute(f'DELETE FROM asset_movements where id="{old_id}"')
            location = v6_deserialize_location_from_db(db_location)
            category = v7_deserialize_asset_movement_category(db_category)
            if asset == 'DAI':
                asset = 'SAI'
            if fee_asset == 'DAI':
                fee_asset = 'SAI'
            new_id = v7_generate_asset_movement_id(
                location=location,
                category=category,
                time=time,
                asset=asset,
                fee_asset=fee_asset,
                link=link,
            )
            entries_to_edit.append((
                new_id, db_location, db_category, time, asset, amount, fee_asset, fee, link,
            ))

    # Insert all newly edited asset movements back in the DB
    query = """
        INSERT INTO asset_movements(
          id,
          location,
          category,
          time,
          asset,
          amount,
          fee_asset,
          fee,
          link)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    cursor.executemany(query, entries_to_edit)
    db.conn.commit()


def _upgrade_trades_table(db: 'DBHandler') -> None:
    """Upgrade the trades for DAI->SAI renaming"""
    cursor = db.conn.cursor()
    # This is the data we need from trades table at v6
    query = cursor.execute(
        'SELECT id,'
        '  time,'
        '  location,'
        '  pair,'
        '  type,'
        '  amount,'
        '  rate,'
        '  fee,'
        '  fee_currency,'
        '  link,'
        '  notes FROM trades;',
    )
    trades_to_edit = []
    for result in query:
        # for each trade get all the relevant data
        old_trade_id = result[0]
        time = int(result[1])
        db_location = result[2]
        pair = result[3]
        db_trade_type = result[4]
        amount = result[5]
        rate = result[6]
        fee = result[7]
        fee_currency = result[8]
        link = result[9]
        notes = result[10]

        should_edit_trade = (
            time < MCDAI_LAUNCH_TS and
            ('DAI' in pair or fee_currency == 'DAI')
        )
        if should_edit_trade:
            # Delete old trade
            cursor.execute(f'DELETE FROM trades where id="{old_trade_id}"')
            # Generate data for new trade
            location = v6_deserialize_location_from_db(db_location)
            trade_type = v6_deserialize_trade_type_from_db(db_trade_type)
            trades_to_edit.append(
            )
            pair = pair.replace('DAI_', 'SAI_')
            pair = pair.replace('_DAI', '_SAI')
            if fee_currency == 'DAI':
                fee_currency = 'SAI'

            new_trade_id = v6_generate_trade_id(
                location=location,
                time=time,
                trade_type=trade_type,
                pair=pair,
                amount=amount,
                rate=rate,
                link=link,
            )
            trades_to_edit.append((
                new_trade_id, time, db_location, pair, db_trade_type,
                amount, rate, fee, fee_currency, link, notes,
            ))

    # add all newly edited trades back in the DB
    query = """
    INSERT INTO trades(
          id,
          time,
          location,
          pair,
          type,
          amount,
          rate,
          fee,
          fee_currency,
          link,
          notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    cursor.executemany(query, trades_to_edit)
    db.conn.commit()


def _upgrade_multisettings_table(db: 'DBHandler') -> None:
    """Upgrade the owned ETH tokens for DAI->SAI renaming"""
    cursor = db.conn.cursor()
    has_dai = cursor.execute(
        'SELECT count(*) FROM multisettings WHERE name="eth_token" AND name="DAI"',
    ).fetchone()[0] > 0
    has_sai = cursor.execute(
        'SELECT count(*) FROM multisettings WHERE name="eth_token" AND name="SAI"',
    ).fetchone()[0] > 0
    if has_sai:
        raise DBUpgradeError('SAI eth_token detected in DB before the DAI->SAI renaming upgrade')

    if has_dai:
        cursor.execute('INSERT INTO multisettings(name, value) VALUES(eth_token, SAI);')
    db.conn.commit()


def _upgrade_timed_balances_table(db: 'DBHandler') -> None:
    """Upgrade the timed_balances table to switch any old DAI balances to SAI"""
    cursor = db.conn.cursor()
    query_str = f"""
    UPDATE timed_balances SET currency="SAI"
    WHERE CURRENCY=="DAI" and time<{MCDAI_LAUNCH_TS}
    """
    cursor.execute(query_str)
    db.conn.commit()


def upgrade_v7_to_v8(db: 'DBHandler') -> None:
    """Upgrades the DB from v7 to v8

    - upgrades trades table for the DAI->SAI renaming
    - upgrades asset movements table for the DAI->SAI renaming
    - upgrades multisettings table for the DAI->SAI renaming
    - upgrades timed_balances table for the DAI->SAI renaming
    """
    _upgrade_trades_table(db)
    _upgrade_asset_movements_table(db)
    _upgrade_multisettings_table(db)
    _upgrade_timed_balances_table(db)
