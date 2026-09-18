from dataclasses import replace
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.balances.historical import HistoricalBalancesManager
from rotkehlchen.chain.evm.decoding.structures import DecoderContext
from rotkehlchen.chain.evm.decoding.uniswap.v3.constants import (
    COLLECT_LIQUIDITY_SIGNATURE,
    POOL_COLLECT_SIGNATURE,
)
from rotkehlchen.chain.evm.decoding.uniswap.v3.utils import (
    decode_uniswap_v3_like_deposit_or_withdrawal,
)
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.hyperliquid.modules.project_x.constants import PROJECT_X_NFT_MANAGER
from rotkehlchen.chain.hyperliquid.modules.project_x.decoder import ProjectXDecoder
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_WHYPE
from rotkehlchen.db.constants import HistoryMappingState
from rotkehlchen.db.filtering import HistoricalBalancesFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import (
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.locations.constants import (
    LOCATION_ETHEREUM,
    LOCATION_HYPERLIQUID,
)
from rotkehlchen.tasks.historical_balances import process_historical_balances
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1
from rotkehlchen.tests.utils.factories import (
    make_ethereum_transaction,
    make_evm_address,
    make_evm_tx_hash,
)
from rotkehlchen.types import ChainID, Timestamp, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.hyperliquid.manager import HyperliquidManager
    from rotkehlchen.chain.hyperliquid.node_inquirer import HyperliquidInquirer
    from rotkehlchen.db.dbhandler import DBHandler

pytestmark = [
    pytest.mark.accounting_update,
    pytest.mark.parametrize('use_clean_caching_directory', [True]),
]


def _make_event(
        timestamp: int,
        asset: Asset,
        amount: str,
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType = HistoryEventSubType.NONE,
        *,
        counterparty: str | None = None,
        liquidity_pool: bool = False,
) -> EvmEvent:
    return EvmEvent(
        tx_ref=make_evm_tx_hash(), sequence_index=0, timestamp=TimestampMS(timestamp * 1000),
        location=LOCATION_ETHEREUM, event_type=event_type, event_subtype=event_subtype,
        asset=asset, amount=FVal(amount), location_label=TEST_ADDR1, counterparty=counterparty,
        extra_data={'liquidity_pool': True} if liquidity_pool else None,
    )


@pytest.mark.parametrize('counterparty', [
    'project-x', 'uniswap-v3', 'uniswap-v4', 'quickswap-v3', 'quickswap-v4',
    'velodrome', 'aerodrome', 'another-lp',
])
@pytest.mark.parametrize('db_settings', [
    {'auto_create_profit_events': False}, {'auto_create_profit_events': True},
])
def test_imbalanced_liquidity_withdrawal_preserves_wallet_proceeds(
        database: DBHandler,
        counterparty: str,
) -> None:
    events = [
        _make_event(1, A_ETH, '1', HistoryEventType.RECEIVE),
        _make_event(2, A_DAI, '100', HistoryEventType.RECEIVE),
        _make_event(
            3, A_ETH, '1', HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            counterparty=counterparty, liquidity_pool=True,
        ),
        _make_event(
            4, A_DAI, '100', HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            counterparty=counterparty, liquidity_pool=True,
        ),
        _make_event(
            5, A_DAI, '150', HistoryEventType.WITHDRAWAL,
            HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            counterparty=counterparty, liquidity_pool=True,
        ),
    ]
    history = DBHistoryEvents(database)
    with database.user_write() as cursor:
        history.add_history_events(cursor, events)
    for from_ts in (None, TimestampMS(5000), None):
        assert process_historical_balances(database, database.msg_aggregator, from_ts)
        assert HistoricalBalancesManager(database).get_balances(
            HistoricalBalancesFilterQuery.make(timestamp=Timestamp(5)),
        ) == (False, {A_DAI: FVal(150)})
        with database.conn.read_ctx() as cursor:
            assert cursor.execute(
                "SELECT COUNT(*) FROM data_issues WHERE kind='negative_balance'",
            ).fetchone()[0] == 0
            assert cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == 5
            assert cursor.execute(
                'SELECT COUNT(*) FROM event_metrics WHERE protocol IS NOT NULL',
            ).fetchone()[0] == 0


def test_edit_liquidity_withdrawal_preserves_pool_marker(database: DBHandler) -> None:
    withdrawal = _make_event(
        5, A_DAI, '150', HistoryEventType.WITHDRAWAL, HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
        counterparty='uniswap-v3', liquidity_pool=True,
    )
    history = DBHistoryEvents(database)
    with database.user_write() as cursor:
        withdrawal.identifier = history.add_history_event(cursor, withdrawal)
    assert withdrawal.identifier is not None

    withdrawal.extra_data = None
    with database.user_write() as cursor:
        history.edit_history_event(cursor, withdrawal, HistoryMappingState.CUSTOMIZED)
    assert withdrawal.extra_data == {'liquidity_pool': True}


def test_fungible_lp_redemption_uses_wallet_balances(database: DBHandler) -> None:
    with database.user_write() as cursor:
        DBHistoryEvents(database).add_history_events(cursor, [
            _make_event(1, A_ETH, '1', HistoryEventType.RECEIVE),
            _make_event(
                2, A_ETH, '1', HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
                counterparty='curve',
            ),
            _make_event(
                3, A_DAI, '150', HistoryEventType.WITHDRAWAL, HistoryEventSubType.REDEEM_WRAPPED,
                counterparty='curve',
            ),
        ])
    assert process_historical_balances(database, database.msg_aggregator)
    assert HistoricalBalancesManager(database).get_balances(
        HistoricalBalancesFilterQuery.make(timestamp=Timestamp(3)),
    ) == (False, {A_DAI: FVal(150)})


@pytest.mark.parametrize('already_decoded', [False, True])
def test_shared_liquidity_decoder_marks_transfers_without_archive_queries(
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        already_decoded: bool,
) -> None:
    inquirer = ethereum_transaction_decoder.evm_inquirer
    tx = make_ethereum_transaction()
    manager = make_evm_address()
    log = EvmTxReceiptLog(
        log_index=10, address=manager,
        topics=[COLLECT_LIQUIDITY_SIGNATURE, (42).to_bytes(32)], data=b'',
    )
    receipt = _make_event(1, A_DAI, '150', HistoryEventType.RECEIVE)
    with patch.object(
        inquirer, 'call_contract', side_effect=AssertionError('Unexpected RPC query'),
    ):
        output = decode_uniswap_v3_like_deposit_or_withdrawal(
            context=DecoderContext(
                tx_log=log, transaction=tx, action_items=[], all_logs=[log],
                decoded_events=[receipt] if already_decoded else [],
            ),
            is_deposit=False, counterparty='uniswap-v3', position_id=42, evm_inquirer=inquirer,
            token0_raw_address=A_DAI.resolve_to_evm_token().evm_address,
            token1_raw_address=A_DAI.resolve_to_evm_token().evm_address,
            amount0_raw=150 * 10**18, amount1_raw=0,
        )
    if already_decoded:
        assert receipt.event_type == HistoryEventType.WITHDRAWAL
        assert receipt.extra_data == {'liquidity_pool': True}
    else:
        assert output.action_items[0].extra_data == {'liquidity_pool': True}
    assert not output.events


def test_project_x_burned_position_uses_receipt_pool_without_archive_state(
        hyperliquid_inquirer: HyperliquidInquirer,
        hyperliquid_manager: HyperliquidManager,
) -> None:
    inquirer = hyperliquid_inquirer
    decoder = ProjectXDecoder(
        inquirer, hyperliquid_manager.transactions_decoder.base, inquirer.database.msg_aggregator,
    )
    tx = replace(make_ethereum_transaction(), chain_id=ChainID.HYPERLIQUID)
    recipient = bytes.fromhex(TEST_ADDR1[2:]).rjust(32, b'\x00')
    data = recipient + bytes(32) + (150 * 10**18).to_bytes(32)
    pool_log = EvmTxReceiptLog(
        log_index=9, address=make_evm_address(), data=data,
        topics=[
            POOL_COLLECT_SIGNATURE,
            bytes.fromhex(PROJECT_X_NFT_MANAGER[2:]).rjust(32, b'\x00'),
        ],
    )
    manager_log = EvmTxReceiptLog(
        log_index=10, address=PROJECT_X_NFT_MANAGER, data=data,
        topics=[COLLECT_LIQUIDITY_SIGNATURE, (42).to_bytes(32)],
    )
    receipt = _make_event(1, A_WHYPE, '150', HistoryEventType.RECEIVE)
    receipt.location = LOCATION_HYPERLIQUID
    token0 = get_or_create_evm_token(
        userdb=inquirer.database,
        evm_address=string_to_evm_address('0x33Af3c2540Ba72054e044EFe504867B39aE421f5'),
        chain_id=ChainID.HYPERLIQUID, decimals=18, name='Unit Plasma', symbol='UXPL',
    )
    with patch.object(inquirer, 'call_contract', side_effect=[
        token0.evm_address,
        A_WHYPE.resolve_to_evm_token().evm_address,
    ]) as calls:
        result = decoder._decode_liquidity(DecoderContext(
            tx_log=manager_log, transaction=tx, action_items=[],
            all_logs=[pool_log, manager_log], decoded_events=[receipt],
        ))
    assert receipt.event_type == HistoryEventType.WITHDRAWAL
    assert receipt.extra_data == {'liquidity_pool': True}
    assert not result.events
    assert [call.kwargs['method_name'] for call in calls.call_args_list] == ['token0', 'token1']
    assert all('block_identifier' not in call.kwargs for call in calls.call_args_list)
