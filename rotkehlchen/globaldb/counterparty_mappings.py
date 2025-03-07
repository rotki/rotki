from rotkehlchen.errors.asset import UnknownCounterpartyMapping
from rotkehlchen.globaldb.handler import GlobalDBHandler


def get_asset_id_by_counterparty(symbol: str, counterparty: str) -> str:
    """
    Fetch asset id mapped from the symbol and counterparty combination.

    May raise:
        - UnknownCounterpartyMapping
    """
    with GlobalDBHandler().conn.read_ctx() as cursor:
        cursor.execute(
            'SELECT local_id FROM counterparty_asset_mappings WHERE '
            'symbol=? AND counterparty=?',
            (symbol, counterparty),
        )
        if (result := cursor.fetchone()) is not None:
            return result[0]

        raise UnknownCounterpartyMapping(symbol=symbol, counterparty=counterparty)
