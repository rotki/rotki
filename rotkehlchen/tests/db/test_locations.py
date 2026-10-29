from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH, A_EUR, A_USDC
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.locations.constants import (
    LOCATION_BINANCE,
    LOCATION_BLOCKFI,
    LOCATION_COINBASE,
    LOCATION_CRYPTOCOM,
    LOCATION_EXTERNAL,
    LOCATION_KRAKEN,
    LOCATION_NEXO,
    LOCATION_POLONIEX,
)
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    TimestampMS,
)


def test_associated_locations(database):
    """Test that locations imported in different places are correctly stored in database"""
    # Add multiple entries for same exchange + connected exchange
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[AssetMovement(
                timestamp=TimestampMS(1595833195000),
                location=LOCATION_CRYPTOCOM,
                asset=A_EUR,
                event_subtype=HistoryEventSubType.RECEIVE,
                amount=ONE,
            ), AssetMovement(
                timestamp=TimestampMS(1587825824000),
                location=LOCATION_CRYPTOCOM,
                asset=A_ETH,
                event_subtype=HistoryEventSubType.SPEND,
                amount=FVal('50.0'),
            ), AssetMovement(
                timestamp=TimestampMS(1596014214000),
                location=LOCATION_BLOCKFI,
                asset=A_ETH,
                event_subtype=HistoryEventSubType.RECEIVE,
                amount=FVal('50.0'),
            ), AssetMovement(
                timestamp=TimestampMS(1565888464000),
                location=LOCATION_NEXO,
                asset=A_ETH,
                event_subtype=HistoryEventSubType.SPEND,
                amount=FVal('50.0'),
            ), AssetMovement(
                timestamp=TimestampMS(1596014214000),
                location=LOCATION_NEXO,
                asset=A_ETH,
                event_subtype=HistoryEventSubType.RECEIVE,
                amount=FVal('50.0'),
                notes='',
            ), AssetMovement(
                timestamp=TimestampMS(1612051199000),
                location=LOCATION_BLOCKFI,
                asset=A_USDC,
                event_subtype=HistoryEventSubType.SPEND,
                amount=FVal('6404.6'),
                notes='One Time',
            ), AssetMovement(
                timestamp=TimestampMS(1595833195000),
                location=LOCATION_POLONIEX,
                event_subtype=HistoryEventSubType.RECEIVE,
                asset=A_ETH,
                amount=ONE,
            ), AssetMovement(
                timestamp=TimestampMS(1596429934000),
                location=LOCATION_COINBASE,
                asset=A_ETH,
                event_subtype=HistoryEventSubType.SPEND,
                amount=FVal('0.00061475'),
            ), AssetMovement(
                timestamp=TimestampMS(1596429934000),
                location=LOCATION_EXTERNAL,
                asset=A_ETH,
                event_subtype=HistoryEventSubType.RECEIVE,
                amount=ONE,
            )],
        )

    kraken_api_key1 = ApiKey('kraken_api_key')
    kraken_api_secret1 = ApiSecret(b'a3Jha2VuX2FwaV9zZWNyZXQ=')
    kraken_api_key2 = ApiKey('kraken_api_key2')
    kraken_api_secret2 = ApiSecret(b'a3Jha2VuX2FwaV9zZWNyZXQy')
    binance_api_key = ApiKey('binance_api_key')
    binance_api_secret = ApiSecret(b'binance_api_secret')
    # add mock kraken and binance
    database.add_exchange('kraken1', LOCATION_KRAKEN, kraken_api_key1, kraken_api_secret1)
    database.add_exchange('kraken2', LOCATION_KRAKEN, kraken_api_key2, kraken_api_secret2)
    database.add_exchange('binance', LOCATION_BINANCE, binance_api_key, binance_api_secret)
    expected_locations = {
        LOCATION_KRAKEN,
        LOCATION_BINANCE,
        LOCATION_BLOCKFI,
        LOCATION_NEXO,
        LOCATION_CRYPTOCOM,
        LOCATION_POLONIEX,
        LOCATION_COINBASE,
        LOCATION_EXTERNAL,
    }

    assert set(database.get_associated_locations()) == expected_locations
