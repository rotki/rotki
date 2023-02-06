from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.types import ChainID, EVMTxHash, Location, TimestampMS


def test_get_customized_event_identifiers(database):
    db = DBHistoryEvents(database)
    with db.db.user_write() as write_cursor:
        db.add_history_event(
            write_cursor=write_cursor,
            event=HistoryBaseEntry(
                event_identifier=EVMTxHash('0x75ceef8e258c08fc2724c1286da0426cb6ec8df208a9ec269108430c30262791'),  # noqa: E501
                sequence_index=1,
                timestamp=TimestampMS(1),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                balance=Balance(1),
            ),
            mapping_values={HISTORY_MAPPING_KEY_STATE: HISTORY_MAPPING_STATE_CUSTOMIZED},
        )
        db.add_history_events(
            write_cursor=write_cursor,
            history=[
                HistoryBaseEntry(
                    event_identifier=EVMTxHash('0x15ceef8e258c08fc2724c1286da0426cb6ec8df208a9ec269108430c30262791'),  # noqa: E501
                    sequence_index=1,
                    timestamp=TimestampMS(1),
                    location=Location.OPTIMISM,
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_ETH,
                    balance=Balance(1),
                ), HistoryBaseEntry(
                    event_identifier=EVMTxHash('0x25ceef8e258c08fc2724c1286da0426cb6ec8df208a9ec269108430c30262791'),  # noqa: E501
                    sequence_index=1,
                    timestamp=TimestampMS(2),
                    location=Location.OPTIMISM,
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_ETH,
                    balance=Balance(2),
                ),
            ],
        )
        db.add_history_event(
            write_cursor=write_cursor,
            event=HistoryBaseEntry(
                event_identifier=EVMTxHash('0x35ceef8e258c08fc2724c1286da0426cb6ec8df208a9ec269108430c30262791'),  # noqa: E501
                sequence_index=1,
                timestamp=TimestampMS(3),
                location=Location.OPTIMISM,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                balance=Balance(1),
            ),
            mapping_values={HISTORY_MAPPING_KEY_STATE: HISTORY_MAPPING_STATE_CUSTOMIZED},
        )

    with db.db.conn.read_ctx() as cursor:
        assert db.get_customized_event_identifiers(cursor, chain_id=None) == [1, 4]
        assert db.get_customized_event_identifiers(cursor, chain_id=ChainID.ETHEREUM) == [1]
        assert db.get_customized_event_identifiers(cursor, chain_id=ChainID.OPTIMISM) == [4]
