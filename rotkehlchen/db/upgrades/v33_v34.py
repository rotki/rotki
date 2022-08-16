from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def upgrade_v33_to_v34(db: 'DBHandler') -> None:
    """Upgrades the DB from v33 to v34

    - Recreates the combined_trades_view to fix a bug with the tx_hash after its
    transformation to bytes
    """
    with db.user_write() as write_cursor:
        write_cursor.execute('DROP VIEW combined_trades_view;')
        write_cursor.execute("""
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
            "0x" || lower(hex(txhash)) AS link,
            NULL AS notes /* no notes */
        FROM SWAPS
        UNION ALL /* using union all as there can be no duplicates so no need to handle them */
        SELECT * from trades
        ;
        """)  # noqa: E501
