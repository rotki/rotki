from unittest.mock import call, patch

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.externalapis.hyperliquid import EntryContext, HyperliquidAPI, ParsedFillEntry
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import AssetAmount, Timestamp, TimestampMS


def test_dex_discovery_parses_and_caches_perp_dexs() -> None:
    api = HyperliquidAPI()

    with patch.object(
        api,
        '_post_info',
        return_value=[None, {'name': 'xyz'}, {'name': 'abc'}, {'name': 'xyz'}, {}],
    ) as mock_post_info:
        assert api._discover_available_dex_names() == ['abc', 'xyz']
        assert api._discover_available_dex_names() == ['abc', 'xyz']

    mock_post_info.assert_called_once_with({'type': 'perpDexs'})


def test_dex_discovery_handles_malformed_response() -> None:
    api = HyperliquidAPI()

    with patch.object(api, '_post_info', return_value={'name': 'xyz'}):
        assert api._discover_available_dex_names() == []


def test_query_balances_merges_all_discovered_dexs() -> None:
    api = HyperliquidAPI()
    address = string_to_evm_address('0x7fC1b7863251Ac7F83c7a4E83ccd00d129Ee844c')

    def mock_query(address: str, account_type: str, dex_name: str | None = None) -> dict:
        if account_type == 'spotClearinghouseState' and dex_name is None:
            return {'balances': [{'coin': 'USDC', 'total': '10'}]}
        if account_type == 'spotClearinghouseState' and dex_name == 'xyz':
            return {'balances': [{'coin': 'USDC', 'total': '20'}]}
        if account_type == 'clearinghouseState' and dex_name is None:
            return {'crossMarginSummary': {'accountValue': '1'}}
        if account_type == 'clearinghouseState' and dex_name == 'xyz':
            return {'crossMarginSummary': {'accountValue': '2'}}

        raise AssertionError('unexpected query parameters')

    with (
        patch.object(api, '_discover_available_dex_names', return_value=['xyz']),
        patch.object(api, '_query', side_effect=mock_query) as mock_query_call,
    ):
        balances = api.query_balances(address=address, include_discovered_dexs=True)

    assert balances[
        Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831')
    ] == FVal('13')
    assert mock_query_call.call_args_list == [
        call(address=address, account_type='spotClearinghouseState', dex_name=None),
        call(address=address, account_type='clearinghouseState', dex_name=None),
        call(address=address, account_type='clearinghouseState', dex_name='xyz'),
    ]


def test_query_history_events_makes_single_call_per_endpoint() -> None:
    """History endpoints (`userFillsByTime`, `userFunding`,
    `userNonFundingLedgerUpdates`) do not take a `dex` parameter and return a
    mixed response covering the first perp dex, all HIP-3 dexs, and spot. We
    must therefore call each of `_create_ledger_events`, `_create_funding_events`
    and `_create_fill_events` exactly once — not per discovered dex.
    """
    api = HyperliquidAPI()
    address = string_to_evm_address('0x7fC1b7863251Ac7F83c7a4E83ccd00d129Ee844c')
    start_ts = Timestamp(1)
    end_ts = Timestamp(2)

    with (
        patch.object(api, '_discover_available_dex_names') as discover,
        patch.object(api, '_create_ledger_events', return_value=[]) as ledger,
        patch.object(api, '_create_funding_events', return_value=[]) as funding,
        patch.object(api, '_create_fill_events', return_value=[]) as fills,
    ):
        history = api.query_history_events(
            address=address,
            start_ts=start_ts,
            end_ts=end_ts,
        )

    assert history == []
    # Dex discovery must not be invoked for the history path — this is what
    # previously caused Nx3 redundant calls.
    discover.assert_not_called()
    assert ledger.call_args_list == [
        call(address=address, start_ts=start_ts, end_ts=end_ts),
    ]
    assert funding.call_args_list == [
        call(address=address, start_ts=start_ts, end_ts=end_ts),
    ]
    assert fills.call_args_list == [
        call(address=address, start_ts=start_ts, end_ts=end_ts),
    ]


def test_create_fill_events_maps_negative_perp_fee_to_cashback() -> None:
    api = HyperliquidAPI()
    address = string_to_evm_address('0x7fC1b7863251Ac7F83c7a4E83ccd00d129Ee844c')
    context = EntryContext(
        entry={},
        timestamp=TimestampMS(1700000000000),
        unique_id='u1',
        group_identifier='g1',
    )
    parsed = ParsedFillEntry(
        context=context,
        raw_coin='BTC',
        is_spot_fill=False,
        spend=AssetAmount(api.arb_usdc, FVal('100')),
        receive=AssetAmount(api.arb_usdc, FVal('99')),
        fee_amount=FVal('-0.25'),
        fee_asset=api.arb_usdc,
        direction='Open Long',
        extra_data={},
    )

    with (
        patch.object(api, '_iter_entries_by_time', return_value=iter([context])),
        patch.object(api, '_parse_fill_entry', return_value=parsed),
    ):
        events = api._create_fill_events(
            address=address, start_ts=Timestamp(1), end_ts=Timestamp(2),
        )

    assert len(events) == 3
    assert events[2].event_type == HistoryEventType.RECEIVE
    assert events[2].event_subtype == HistoryEventSubType.CASHBACK
    assert events[2].amount == FVal('0.25')


def test_create_fill_events_maps_negative_spot_fee_to_cashback() -> None:
    api = HyperliquidAPI()
    address = string_to_evm_address('0x7fC1b7863251Ac7F83c7a4E83ccd00d129Ee844c')
    context = EntryContext(
        entry={},
        timestamp=TimestampMS(1700000000000),
        unique_id='u2',
        group_identifier='g2',
    )
    parsed = ParsedFillEntry(
        context=context,
        raw_coin='@1',
        is_spot_fill=True,
        spend=AssetAmount(api.arb_usdc, FVal('50')),
        receive=AssetAmount(api.arb_usdc, FVal('49.9')),
        fee_amount=FVal('-0.1'),
        fee_asset=api.arb_usdc,
        direction='Buy',
        extra_data={},
    )

    with (
        patch.object(api, '_iter_entries_by_time', return_value=iter([context])),
        patch.object(api, '_parse_fill_entry', return_value=parsed),
    ):
        events = api._create_fill_events(
            address=address, start_ts=Timestamp(1), end_ts=Timestamp(2),
        )

    assert len(events) == 3
    assert events[2].event_type == HistoryEventType.RECEIVE
    assert events[2].event_subtype == HistoryEventSubType.CASHBACK
    assert events[2].amount == FVal('0.1')


def test_parse_fill_entry_extracts_hip3_dex_prefix() -> None:
    """HIP-3 fills use `{dex}:{coin}` in the `coin` field. The parser must
    strip the prefix to resolve the asset and surface the dex in extra_data.
    """
    api = HyperliquidAPI()
    context = EntryContext(
        entry={
            'coin': 'xyz:BTC',
            'px': '25000',
            'sz': '0.01',
            'side': 'B',
            'time': 1700000000000,
            'tid': 42,
            'hash': '0xtx',
            'fee': '0.01',
            'feeToken': 'USDC',
        },
        timestamp=TimestampMS(1700000000000),
        unique_id='42',
        group_identifier='g1',
    )

    with patch(
        'rotkehlchen.externalapis.hyperliquid.asset_from_hyperliquid',
        return_value=Asset('BTC'),
    ):
        parsed = api._parse_fill_entry(context)

    assert parsed is not None
    assert parsed.raw_coin == 'xyz:BTC'
    assert parsed.extra_data['dex'] == 'xyz'
    assert parsed.extra_data['market'] == 'xyz:BTC'


def test_parse_fill_entry_omits_dex_for_non_hip3_fills() -> None:
    """Non-HIP-3 fills (main perp dex or spot) must not have a `dex` key in
    extra_data, otherwise downstream consumers can't distinguish them from
    HIP-3 fills.
    """
    api = HyperliquidAPI()
    context = EntryContext(
        entry={
            'coin': 'BTC',
            'px': '25000',
            'sz': '0.01',
            'side': 'B',
            'time': 1700000000000,
            'tid': 43,
            'hash': '0xtx',
            'fee': '0.01',
            'feeToken': 'USDC',
        },
        timestamp=TimestampMS(1700000000000),
        unique_id='43',
        group_identifier='g2',
    )

    with patch(
        'rotkehlchen.externalapis.hyperliquid.asset_from_hyperliquid',
        return_value=Asset('BTC'),
    ):
        parsed = api._parse_fill_entry(context)

    assert parsed is not None
    assert 'dex' not in parsed.extra_data
