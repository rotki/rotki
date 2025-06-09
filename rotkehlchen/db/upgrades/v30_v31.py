from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


def _do_upgrade(cursor: 'DBCursor', progress_handler: 'DBUpgradeProgressHandler') -> None:
    progress_handler.new_step(name='Deleting all ignored ethereum transaction ids.')
    # Should exist -- but we are being extremely pedantic here
    ignored_actions_exists = cursor.execute(  # always returns value
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='ignored_actions';",
    ).fetchone()[0]
    # Delete all ignored ethereum transaction ids
    if ignored_actions_exists == 1:
        cursor.execute("DELETE FROM ignored_actions WHERE type='C';")
    else:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ignored_actions (
        type CHAR(1) NOT NULL DEFAULT('A') REFERENCES action_type(type),
        identifier TEXT,
        PRIMARY KEY (type, identifier)
        );
        """)

    progress_handler.new_step(name='Deleting all kraken trades and their used query ranges.')
    # Delete kraken trades so they can be requeried
    cursor.execute("DELETE FROM trades WHERE location='B';")
    cursor.execute(
        'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?', ('kraken\\_trades\\_%', '\\'),
    )

    progress_handler.new_step(name='Updating eth2 tables.')
    # Add all new tables
    cursor.execute('DROP TABLE IF EXISTS eth2_deposits;')
    cursor.execute('DROP TABLE IF EXISTS eth2_daily_staking_details;')
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS eth2_validators (
    validator_index INTEGER NOT NULL PRIMARY KEY,
    public_key TEXT NOT NULL UNIQUE,
    ownership_proportion TEXT NOT NULL
    );""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS eth2_deposits (
    tx_hash BLOB NOT NULL,
    tx_index INTEGER NOT NULL,
    from_address VARCHAR[42] NOT NULL,
    timestamp INTEGER NOT NULL,
    pubkey TEXT NOT NULL,
    withdrawal_credentials TEXT NOT NULL,
    amount TEXT NOT NULL,
    usd_value TEXT NOT NULL,
    FOREIGN KEY(pubkey) REFERENCES eth2_validators(public_key) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY(tx_hash, pubkey, amount) /* multiple deposits can exist for same pubkey */
    );""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS eth2_daily_staking_details (
    validator_index INTEGER NOT NULL,
    timestamp integer NOT NULL,
    start_usd_price TEXT NOT NULL,
    end_usd_price TEXT NOT NULL,
    pnl TEXT NOT NULL,
    start_amount TEXT NOT NULL,
    end_amount TEXT NOT NULL,
    missed_attestations INTEGER,
    orphaned_attestations INTEGER,
    proposed_blocks INTEGER,
    missed_blocks INTEGER,
    orphaned_blocks INTEGER,
    included_attester_slashings INTEGER,
    proposer_attester_slashings INTEGER,
    deposits_number INTEGER,
    amount_deposited TEXT,
    FOREIGN KEY(validator_index) REFERENCES eth2_validators(validator_index) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (validator_index, timestamp));""")  # noqa: E501
    cursor.execute("""
CREATE VIEW IF NOT EXISTS combined_trades_view AS
    WITH amounts_query AS (
        SELECT
        A.tx_hash AS txhash,
        A.log_index AS logindex,
        A.timestamp AS time,
        A.location AS location,
        FE.amount1_in AS first1in,
        FE.amount0_in AS first0in,
        FE.token0_identifier AS firsttoken0,
        FE.token1_identifier AS firsttoken1,
        LE.amount0_out AS last0out,
        LE.amount1_out AS last1out,
        LE.token0_identifier AS lasttoken0,
        LE.token1_identifier AS lasttoken1
        FROM amm_swaps A
        LEFT JOIN amm_swaps FE ON
        FE.tx_hash = A.tx_hash AND FE.log_index=(SELECT MIN(log_index) FROM amm_swaps WHERE tx_hash=A.tx_hash)
        LEFT JOIN amm_swaps LE ON
        LE.tx_hash = A.tx_hash AND LE.log_index=(SELECT MAX(log_index) FROM amm_swaps WHERE tx_hash=A.tx_hash)
        WHERE A.tx_hash IN (SELECT DISTINCT tx_hash FROM amm_swaps) GROUP BY A.tx_hash
    ), C1 AS (
        SELECT lasttoken0 AS base1, firsttoken0 AS quote1, last0out AS amount1, cast(first0in AS REAL) / CAST(last0out AS REAL) AS rate1, txhash, logindex, time, location
        FROM amounts_query
        WHERE first0in > 0 AND last0out > 0 AND first1in == 0 AND last1out == 0
    ), C2 AS (
        SELECT lasttoken1 AS base1, firsttoken0 AS quote1, last1out AS amount1, cast(first0in AS REAL) / CAST(last1out AS REAL) AS rate1, txhash, logindex, time, location
        FROM amounts_query
        WHERE first0in > 0 AND last1out > 0 AND first1in == 0 AND last0out == 0
    ), C3 AS (
        SELECT lasttoken0 AS base1, firsttoken1 AS quote1, last0out AS amount1, CAST(first1in AS REAL) / CAST(last0out AS REAL) AS rate1, txhash, logindex, time, location
        FROM amounts_query
        WHERE first1in > 0 AND last0out > 0 AND first0in == 0 AND last1out == 0
    ), C4 AS (
        SELECT lasttoken1 AS base1, firsttoken1 AS quote1, last1out AS amount1, CAST(first1in AS REAL) / CAST(last1out AS REAL) AS rate1, txhash, logindex, time, location
        FROM amounts_query
        WHERE first1in > 0 AND last1out > 0 AND first0in == 0 AND last0out == 0
    ), C5 AS (
        SELECT
            lasttoken1 AS base1,
            firsttoken1 AS quote1,
            (CAST(last1out AS REAL) / 2) AS amount1,
            CAST(first1in AS REAL) / (CAST(last1out AS REAL) / 2) as rate1,
            lasttoken1 AS base2,
            firsttoken0 AS quote2,
            (CAST(last1out AS REAL) / 2) AS amount2,
            CAST(first0in AS REAL) / (CAST(last1out AS REAL) / 2) AS rate2,
            txhash, logindex, time, location
        FROM amounts_query
        WHERE first1in > 0 AND first0in > 0 AND last1out > 0 AND last0out == 0
    ), C6 AS (
        SELECT
            lasttoken1 AS base1,
            firsttoken1 AS quote1,
            last1out AS amount1,
            CAST(first1in AS REAL) / CAST(last1out AS REAL) AS rate1,
            lasttoken0 AS base2,
            firsttoken0 AS quote2,
            last0out AS amount2,
            CAST(first0in AS REAL) / CAST(last0out AS REAL) AS rate2,
            txhash, logindex, time, location
        FROM amounts_query
        WHERE first1in > 0 AND first0in > 0 AND last1out > 0 AND last0out > 0
    ), SWAPS AS (
    SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C1
    UNION ALL /* using union all as there can be no duplicates so no need to handle them */
    SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C2
    UNION ALL /* using union all as there can be no duplicates so no need to handle them */
    SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C3
    UNION ALL /* using union all as there can be no duplicates so no need to handle them */
    SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C4
    UNION ALL /* using union all as there can be no duplicates so no need to handle them */
    SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C5
    UNION ALL /* using union all as there can be no duplicates so no need to handle them */
    SELECT base2 AS base_asset, quote2 AS quote_asset, amount2 AS amount, rate2 AS rate, txhash, logindex, time, location FROM C5
    UNION ALL /* using union all as there can be no duplicates so no need to handle them */
    SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C6
    UNION ALL /* using union all as there can be no duplicates so no need to handle them */
    SELECT base2 AS base_asset, quote2 AS quote_asset, amount2 AS amount, rate2 AS rate, txhash, logindex, time, location FROM C6
)
SELECT
    txhash + logindex AS id,
    time,
    location,
    base_asset,
    quote_asset,
    'A' AS type, /* always a BUY */
    amount,
    rate,
    NULL AS fee, /* no fee */
    NULL AS fee_currency, /* no fee */
    txhash AS link,
    NULL AS notes /* no notes */
FROM SWAPS
UNION ALL /* using union all as there can be no duplicates so no need to handle them */
SELECT * from trades
;""")  # noqa: E501
    cursor.execute("""CREATE TABLE IF NOT EXISTS history_events (
    identifier TEXT NOT NULL PRIMARY KEY,
    event_identifier TEXT NOT NULL,
    sequence_index INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    location TEXT NOT NULL,
    location_label TEXT,
    asset TEXT NOT NULL,
    amount TEXT NOT NULL,
    usd_value TEXT NOT NULL,
    notes TEXT,
    type TEXT NOT NULL,
    subtype TEXT
    );""")


def upgrade_v30_to_v31(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v30 to v31

    - Add the new eth2 validator table and upgrade the old ones to have foreign key relationships.
    - Delete all ignored ethereum transaction ids as now the identifier
    is the one specified by the backend.
    - Delete all kraken trades and their used query ranges since we can now also fetch app trades
    and insta trades which are only visible through the kraken ledger query.
    """
    progress_handler.set_total_steps(3)
    with db.user_write() as cursor:
        _do_upgrade(cursor=cursor, progress_handler=progress_handler)
