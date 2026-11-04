from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

from rotkehlchen.constants.assets import A_BTC, A_CRV, A_ETH, A_EUR, A_HYPE, A_USD
from rotkehlchen.data_import.importers.krak import KrakImporter
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import (
    EventDirection,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.locations.constants import LOCATION_KRAK
from rotkehlchen.types import TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
WALLET = 'Everyday'


def _get_events(database: DBHandler) -> list[HistoryBaseEntry]:
    with database.conn.read_ctx() as cursor:
        return DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(order_by_rules=[
                ('timestamp', True),
                ('history_events_identifier', True),
            ]),
        )


def _balances(events: list[HistoryBaseEntry]) -> dict[Asset, FVal]:
    """Replay the balance of each asset from the events"""
    balances: defaultdict[Asset, FVal] = defaultdict(FVal)
    for event in events:
        if (direction := event.maybe_get_direction(for_balance_tracking=True)) == EventDirection.IN:  # noqa: E501
            balances[event.asset] += event.amount
        elif direction == EventDirection.OUT:
            balances[event.asset] -= event.amount

    return dict(balances)


def _swap(
        identifier: int,
        timestamp: int,
        reference: str,
        subtype: HistoryEventSubType,
        asset: Asset,
        amount: str,
        notes: str | None = None,
) -> SwapEvent:
    return SwapEvent(
        identifier=identifier,
        timestamp=TimestampMS(timestamp),
        location=LOCATION_KRAK,
        event_subtype=subtype,  # type: ignore[arg-type]  # the test only passes swap subtypes
        asset=asset,
        amount=FVal(amount),
        group_identifier=f'KRK_{reference}',
        location_label=WALLET,
        notes=notes,
    )


def test_import_issue_sample(database: DBHandler) -> None:
    """The anonymized sample of the issue, exported before Krak added the `Fee` column.
    Fees only exist in fiat there and are converted back to the row's asset, and the
    pending rows are skipped until a later export settles them."""
    importer = KrakImporter(db=database)
    assert importer.import_csv(filepath=DATA_DIR / 'krak_sample.csv') == (True, '')
    assert importer.total_entries == 16
    assert importer.imported_entries == 11
    assert [x['row'] for x in importer.import_msgs] == [12, 13, 14, 15, 16]
    assert all('is_error' not in x and x['msg'].startswith('Skipped pending') for x in importer.import_msgs)  # noqa: E501

    assert _get_events(database) == [AssetMovement(
        identifier=1,
        group_identifier='KRK_FTaA3D7-RZ2NUX9NGPTZ2V9VYLWH5V',
        timestamp=TimestampMS(1783260402000),
        location=LOCATION_KRAK,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_EUR,
        amount=FVal('372.94'),
        location_label=WALLET,
        extra_data={'reference': 'FTaA3D7-RZ2NUX9NGPTZ2V9VYLWH5V'},
    ), AssetMovement(
        identifier=2,
        group_identifier='KRK_FTj8FM3-5QMPPJCD8JZZBKHMHQWGJB',
        timestamp=TimestampMS(1783266340000),
        location=LOCATION_KRAK,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_CRV,
        amount=FVal('230.0396529252'),
        location_label=WALLET,
        extra_data={'reference': 'FTj8FM3-5QMPPJCD8JZZBKHMHQWGJB'},
    ),
        _swap(7, 1783266525000, 'TSZ56PZ-8KH46-2BXD3P', HistoryEventSubType.SPEND, A_CRV, '175.1047974'),  # noqa: E501
        _swap(8, 1783266525000, 'TSZ56PZ-8KH46-2BXD3P', HistoryEventSubType.RECEIVE, A_ETH, '0.0226568214'),  # noqa: E501
        _swap(9, 1783266525000, 'TSZ56PZ-8KH46-2BXD3P', HistoryEventSubType.FEE, A_ETH, '0.0002243064'),  # 0.5164 EUR at 2,302.2083  # noqa: E501
        _swap(10, 1783266548000, 'TSLWX9E-UXRUT-542ZHX', HistoryEventSubType.SPEND, A_ETH, '0.0262750279'),  # noqa: E501
        _swap(11, 1783266548000, 'TSLWX9E-UXRUT-542ZHX', HistoryEventSubType.RECEIVE, A_HYPE, '0.7337921'),  # noqa: E501
        _swap(12, 1783266548000, 'TSLWX9E-UXRUT-542ZHX', HistoryEventSubType.FEE, A_ETH, '0.0002627477'),  # noqa: E501
        HistoryEvent(
        identifier=3,
        group_identifier='KRK_PAY6J2M-5G3HAP-NUQ6MX',
        sequence_index=0,
        timestamp=TimestampMS(1783315437000),
        location=LOCATION_KRAK,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.PAYMENT,
        asset=A_EUR,
        amount=FVal('9.35'),
        location_label=WALLET,
        notes='Pay 9.35 EUR with the Krak card to Merchant 1',
    ), HistoryEvent(
        identifier=4,
        group_identifier='KRK_PAYM85X-P6NNV6-MFRUB5',
        sequence_index=0,
        timestamp=TimestampMS(1783315439000),
        location=LOCATION_KRAK,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.CASHBACK,
        asset=A_BTC,
        amount=FVal('0.0000045229'),
        location_label=WALLET,
        notes='Receive 0.0000045229 BTC as Krak card cashback for a payment to Merchant 1',
    ), HistoryEvent(
        identifier=5,
        group_identifier=(earn_group := 'KRK_ELTAQBL-JD6FN-H4DNZT'),
        sequence_index=0,
        timestamp=(earn_ts := TimestampMS(1783393466000)),
        location=LOCATION_KRAK,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REWARD,
        asset=A_HYPE,
        amount=FVal('0.0000196'),
        location_label=WALLET,
        notes='Receive 0.0000196 HYPE as Krak earn reward',
    ), HistoryEvent(
        identifier=6,
        group_identifier=earn_group,
        sequence_index=1,
        timestamp=earn_ts,
        location=LOCATION_KRAK,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_HYPE,
        amount=FVal('0.0000047147'),
        location_label=WALLET,
        notes='Pay 0.0000047147 HYPE as Krak fee',
    ),  # Krak names the outgoing HYPE leg of this crypto funded payment `Buy`
        _swap(13, 1786973520000, 'TS6H9QH-E3GDU-HQTLS8', HistoryEventSubType.SPEND, A_HYPE, '3.700747', notes='Krak buy with Merchant 2'),  # noqa: E501
        _swap(14, 1786973520000, 'TS6H9QH-E3GDU-HQTLS8', HistoryEventSubType.RECEIVE, A_EUR, '275.29'),  # noqa: E501
    ]


def test_import_with_fee_column(database: DBHandler) -> None:
    """Exports since November 2026 carry the fee in the row's asset. The balance change of a
    row is `Amount - Fee`, so converting a whole ETH balance and then all the ETH it bought
    must leave nothing behind."""
    importer = KrakImporter(db=database)
    assert importer.import_csv(filepath=DATA_DIR / 'krak_sample_with_fee_column.csv') == (True, '')
    assert importer.total_entries == 13
    assert importer.imported_entries == 12
    assert [x['row'] for x in importer.import_msgs] == [12]

    events = _get_events(database)
    assert _balances(events) == {
        A_EUR: FVal('19.35'),  # 1250 in, 1200 to the bank, 25.4 card, 0.25 cashback, 10.5 to and 5 from a Krak user  # noqa: E501
        A_CRV: FVal(0),
        A_ETH: FVal(0),
        A_HYPE: FVal('0.3607'),  # 0.36 bought and 0.001 of reward minus its 0.0003 fee
    }
    assert events[0] == AssetMovement(
        identifier=1,
        group_identifier='KRK_TRK4D2M-7QPLA-W8ZN3E',
        timestamp=TimestampMS(1777713011000),
        location=LOCATION_KRAK,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_EUR,
        amount=FVal('1250'),
        location_label=WALLET,
        notes='Krak transfer from QRST-4K7M-2PZW-9HX3',
        extra_data={'reference': 'TRK4D2M-7QPLA-W8ZN3E', 'krak_transfer': True},
    )
    assert events[1] == AssetMovement(
        identifier=2,
        group_identifier='KRK_FTQ8x2K-LmN4pRs7Tu1Vw3Xy5Za9Bc',
        timestamp=TimestampMS(1777713340000),
        location=LOCATION_KRAK,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_EUR,
        amount=FVal('1200'),
        location_label=WALLET,
        notes='Krak withdrawal to Account Holder',
        extra_data={'reference': 'FTQ8x2K-LmN4pRs7Tu1Vw3Xy5Za9Bc'},
    )
    assert events[4] == HistoryEvent(  # an outgoing transfer without counterparty pays a Krak user
        identifier=5,
        group_identifier='KRK_TRB7Y4N-K2QXM-H9D3PL',
        sequence_index=0,
        timestamp=TimestampMS(1777881600000),
        location=LOCATION_KRAK,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_EUR,
        amount=FVal('10.5'),
        location_label=WALLET,
        notes='Send 10.5 EUR to another Krak user',
    )
    assert events[-1] == HistoryEvent(  # an incoming one is a payment from a Krak user
        identifier=9,
        group_identifier='KRK_TRP3X8D-N6QKW-Z4VJ2R',
        sequence_index=0,
        timestamp=TimestampMS(1778265000000),
        location=LOCATION_KRAK,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_EUR,
        amount=FVal('5'),
        location_label=WALLET,
        notes='Receive 5 EUR from another Krak user',
    )


def test_reimport_after_pending_rows_settle(database: DBHandler, tmp_path: Path) -> None:
    """A later export repeats each settled row with the same reference. Importing it adds
    only the rows that were pending before and creates no duplicates."""
    importer = KrakImporter(db=database)
    assert importer.import_csv(filepath=DATA_DIR / 'krak_sample.csv') == (True, '')
    assert len(_get_events(database)) == 14

    settled_values = iter((
        '"2,000.0000","0.0069","0.0230"',  # ETH reward and its fee
        '"80.0000","0.0270","0.0899"',  # HYPE reward and its fee
        '"1","0","-444.88"',
        '"70,000.0000","0","3.7586"',
        '"1","0","405.5506"',
    ))
    (settled := tmp_path / 'krak_settled.csv').write_text(''.join(
        line.replace('"-","-","-"', next(settled_values)) if '"-"' in line else line
        for line in (DATA_DIR / 'krak_sample.csv').read_text().splitlines(keepends=True)
    ))
    assert importer.import_csv(filepath=settled) == (True, '')
    assert importer.total_entries == importer.imported_entries == 16
    assert all(x['msg'].startswith('Skipped duplicate') for x in importer.import_msgs)

    events = _get_events(database)
    assert len(events) == 21  # 14 before, plus 2 rewards with their fees, 2 card events, 1 transfer  # noqa: E501
    assert len({(x.group_identifier, x.sequence_index) for x in events}) == 21
    assert [(x.event_subtype, x.amount) for x in events if x.group_identifier == 'KRK_ELF4SV7-JBN22-9UUF8F'] == [  # noqa: E501
        (HistoryEventSubType.REWARD, FVal('0.0000114908')),
        (HistoryEventSubType.FEE, FVal('0.00000345')),  # 0.0069 EUR at 2,000
    ]

    assert importer.import_csv(filepath=settled) == (True, '')  # importing it again adds nothing
    assert len(_get_events(database)) == 21


def test_import_other_fiat_and_unsupported_rows(database: DBHandler, tmp_path: Path) -> None:
    """Krak names the fiat columns after the account currency. Rows with an unknown shape
    are reported without stopping the import."""
    (filepath := tmp_path / 'krak_usd.csv').write_text(
        '"Date (UTC)","Type","Subtype","Asset","Asset Name","Wallet","Amount","Price (USD)","Fee (USD)","Value (USD)","Counter party","Reference"\n'  # noqa: E501
        '"2026-06-01 10:00:00","Trade","Convert","USD","US Dollar","Everyday","-50.00","1","0","-50.00","Krak","TSAAAA1-BBBBB-CCCCC1"\n'  # noqa: E501
        '"2026-06-01 10:00:00","Trade","Convert","ETH","Ethereum","Everyday","0.0200000000","2,500.0000","0.5000","50.00","Krak","TSAAAA1-BBBBB-CCCCC1"\n'  # noqa: E501
        '"2026-06-02 10:00:00","Trade","Convert","ETH","Ethereum","Everyday","-0.0100000000","2,500.0000","0","-25.00","Krak","TSDDDD2-EEEEE-FFFFF2"\n'  # noqa: E501
        '"2026-06-03 10:00:00","Krak Card","Cashback Reward","BTC","Bitcoin","Everyday","-0.0000010000","70,000.0000","0","-0.07","Merchant 5","PAYGGGG-HHHHHH-IIIII3"\n'  # noqa: E501
        '"2026-06-04 10:00:00","Gift","Card","USD","US Dollar","Everyday","10.00","1","0","10.00","","GFJJJJ4-KKKKK-LLLLL4"\n',  # noqa: E501
    )
    importer = KrakImporter(db=database)
    assert importer.import_csv(filepath=filepath) == (True, '')
    assert importer.total_entries == 5
    assert importer.imported_entries == 2
    assert {(x['row'], x['msg']) for x in importer.import_msgs} == {
        (3, 'Krak trade TSDDDD2-EEEEE-FFFFF2 does not have exactly one outgoing and one incoming leg'),  # noqa: E501
        (4, 'Unsupported Krak entry Krak Card/Cashback Reward with amount -0.000001'),
        (5, 'Unsupported Krak entry Gift/Card with amount 10'),
    }
    assert [(x.event_subtype, x.asset, x.amount) for x in _get_events(database)] == [
        (HistoryEventSubType.SPEND, A_USD, FVal('50')),
        (HistoryEventSubType.RECEIVE, A_ETH, FVal('0.02')),
        (HistoryEventSubType.FEE, A_ETH, FVal('0.0002')),  # 0.5 USD at 2,500
    ]


def test_import_rejects_other_files(database: DBHandler, tmp_path: Path) -> None:
    (filepath := tmp_path / 'not_krak.csv').write_text('"Date","Amount"\n"2026-06-01","1"\n')
    assert KrakImporter(db=database).import_csv(filepath=filepath) == (
        False,
        'Krak CSV is missing the columns Date (UTC), Type, Subtype, Asset, Wallet, Counter party, Reference',  # noqa: E501
    )
