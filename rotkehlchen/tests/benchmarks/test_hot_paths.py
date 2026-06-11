"""Micro-benchmarks for hot pure-python paths (measurement framework §4.4).

Excluded from normal test runs via the global `-m "not benchmark"` addopts.
Run explicitly with:

    uv run python pytestgeventwrapper.py -m benchmark --benchmark-only rotkehlchen/tests/benchmarks

Kept pytest-codspeed compatible: only the plain `benchmark` fixture API is
used, so switching/adding `pytest-codspeed` later is a drop-in.
"""
from typing import TYPE_CHECKING

import pytest

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_USDC
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import deserialize_evm_tx_hash
from rotkehlchen.types import Location, Timestamp, TimestampMS

if TYPE_CHECKING:
    from collections.abc import Callable

N_EVENTS = 1_000


def _make_events() -> list[EvmEvent]:
    address = string_to_evm_address('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    return [
        EvmEvent(
            tx_ref=deserialize_evm_tx_hash(idx.to_bytes(32, 'big')),
            sequence_index=idx % 16,
            timestamp=TimestampMS(1700000000000 + idx * 13_000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_USDC if idx % 3 == 0 else A_ETH,
            amount=FVal(f'{idx + 1}.{idx % 100:02d}'),
            location_label=address,
            counterparty='uniswap-v3' if idx % 5 == 0 else None,
            address=address,
            notes=f'Receive {idx + 1} tokens from somewhere interesting {idx}',
        )
        for idx in range(N_EVENTS)
    ]


@pytest.mark.benchmark
def test_history_event_db_serialization(benchmark: 'Callable') -> None:
    """Write-path serialization of history events, exercised on every
    transaction decode and event edit"""
    events = _make_events()
    benchmark(lambda: [event.serialize_for_db() for event in events])


@pytest.mark.benchmark
def test_history_event_api_serialization(benchmark: 'Callable') -> None:
    """API serialization of history events, exercised on every events page"""
    events = _make_events()
    benchmark(lambda: [event.serialize() for event in events])


@pytest.mark.benchmark
def test_fval_arithmetic(benchmark: 'Callable') -> None:
    """FVal math as done in balance aggregation loops"""
    values = [FVal(f'{idx}.{idx % 1000:03d}') for idx in range(1, N_EVENTS + 1)]
    price = FVal('1234.5678')

    def aggregate() -> FVal:
        total = FVal(0)
        for value in values:
            total += value * price
        return total

    benchmark(aggregate)


@pytest.mark.benchmark
def test_events_filter_query_construction(benchmark: 'Callable') -> None:
    """Filter-query construction + SQL preparation, done per events API call"""
    def build() -> tuple:
        filter_query = EvmEventFilterQuery.make(
            from_ts=Timestamp(1600000000),
            to_ts=Timestamp(1800000000),
            assets=(A_ETH, A_USDC),
            counterparties=['uniswap-v3', 'gas'],
            location_labels=['0x9531C059098e3d194fF87FebB587aB07B30B1306'],
            limit=50,
            offset=0,
        )
        return filter_query.prepare()

    benchmark(build)
