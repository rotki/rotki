from copy import deepcopy
from unittest.mock import Mock

import pytest

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.constants import DEPOSIT_TOPIC_V3, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
from rotkehlchen.chain.evm.decoding.flying_tulip.constants import CPT_FLYING_TULIP
from rotkehlchen.chain.evm.decoding.flying_tulip.ftusd.constants import (
    FLYING_TULIP_FTUSD_DEPLOYMENTS,
    MINTED_TOPIC,
)
from rotkehlchen.chain.evm.decoding.flying_tulip.ftusd.decoder import FlyingTulipFtusdCommonDecoder
from rotkehlchen.chain.evm.decoding.flying_tulip.lend.constants import (
    FLYING_TULIP_LEND_DEPLOYMENTS,
    PM_REPAY_TOPIC,
)
from rotkehlchen.chain.evm.decoding.flying_tulip.lend.decoder import FlyingTulipLendCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import DecoderContext
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.constants import ONE
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.factories import (
    CUSTOM_USDT,
    make_ethereum_event,
    make_ethereum_transaction,
    make_evm_address,
)
from rotkehlchen.types import ChainID, TokenKind
from rotkehlchen.user_messages import MessagesAggregator


@pytest.mark.parametrize('has_protocol_payout', [False, True])
def test_ftusd_swap_requires_protocol_transfers(has_protocol_payout):
    """An unrelated equal-amount receive cannot complete a swap or cause a half-decoded spend."""
    base = Mock(spec=BaseEvmDecoderTools)
    base.any_tracked.return_value = True
    ftusd = EvmToken.initialize(
        address=FLYING_TULIP_FTUSD_DEPLOYMENTS[ChainID.ETHEREUM].ftusd_token,
        chain_id=ChainID.ETHEREUM, token_kind=TokenKind.ERC20,
        symbol='ftUSD', decimals=6,
    )
    base.get_or_create_evm_token.return_value = CUSTOM_USDT
    decoder = FlyingTulipFtusdCommonDecoder(
        evm_inquirer=Mock(chain_id=ChainID.ETHEREUM),
        base_tools=base,
        msg_aggregator=MessagesAggregator(),
    )
    manager = FLYING_TULIP_FTUSD_DEPLOYMENTS[ChainID.ETHEREUM].mint_and_redeem
    user = make_evm_address()
    transaction = make_ethereum_transaction()
    spend = make_ethereum_event(
        index=1, tx_ref=transaction.tx_hash, location_label=user,
        event_type=HistoryEventType.SPEND, address=manager,
    )
    unrelated = make_ethereum_event(
        index=2, tx_ref=transaction.tx_hash, location_label=user,
        event_type=HistoryEventType.RECEIVE, asset=ftusd, address=make_evm_address(),
    )
    events = [spend, unrelated]
    if has_protocol_payout:
        events.append(make_ethereum_event(
            index=3, tx_ref=transaction.tx_hash, location_label=user,
            event_type=HistoryEventType.RECEIVE, asset=ftusd, address=manager,
        ))
    original = deepcopy(events)
    context = DecoderContext(
        transaction=transaction,
        tx_log=EvmTxReceiptLog(
            log_index=4, address=manager,
            topics=[MINTED_TOPIC, bytes.fromhex(user[2:]).rjust(32, b'\x00'),
                    bytes.fromhex(user[2:]).rjust(32, b'\x00'),
                    bytes.fromhex(CUSTOM_USDT.evm_address[2:]).rjust(32, b'\x00')],
            data=bytes(64) + (10 ** CUSTOM_USDT.decimals).to_bytes(32) * 2,
        ),
        decoded_events=events, all_logs=[], action_items=[],
    )
    output = decoder.addresses_to_decoders()[manager][0](context)
    assert output.process_swaps is has_protocol_payout
    assert unrelated == original[1]
    if has_protocol_payout:
        assert [(event.event_type, event.event_subtype) for event in (spend, events[-1])] == [
            (HistoryEventType.TRADE, HistoryEventSubType.SPEND),
            (HistoryEventType.TRADE, HistoryEventSubType.RECEIVE),
        ]
        assert spend.counterparty == events[-1].counterparty == CPT_FLYING_TULIP
        assert spend.amount == events[-1].amount == ONE
    else:
        assert events == original


@pytest.mark.parametrize('transfer_count', [1, 2])
def test_lending_does_not_reuse_repaid_transfer(transfer_count):
    """A repayment's spend cannot also fund a deposit of the same amount in the same token."""
    base = Mock(spec=BaseEvmDecoderTools)
    base.is_tracked.return_value = True
    base.get_or_create_evm_token.return_value = CUSTOM_USDT
    decoder = FlyingTulipLendCommonDecoder(
        evm_inquirer=Mock(chain_id=ChainID.ETHEREUM),
        base_tools=base,
        msg_aggregator=MessagesAggregator(),
    )
    manager = FLYING_TULIP_LEND_DEPLOYMENTS[ChainID.ETHEREUM].positions_manager
    user = make_evm_address()
    transaction = make_ethereum_transaction()
    events = [make_ethereum_event(
        index=index, tx_ref=transaction.tx_hash, location_label=user,
        event_type=HistoryEventType.SPEND, address=manager,
    ) for index in range(transfer_count)]
    unrelated = make_ethereum_event(
        index=5, tx_ref=transaction.tx_hash, location_label=user,
        event_type=HistoryEventType.RECEIVE, address=ZERO_ADDRESS,
    )
    events.append(unrelated)
    original_unrelated = deepcopy(unrelated)
    logs = [EvmTxReceiptLog(
        log_index=index + 10, address=manager,
        topics=[topic, bytes.fromhex(user[2:]).rjust(32, b'\x00'),
                bytes.fromhex(CUSTOM_USDT.evm_address[2:]).rjust(32, b'\x00')],
        data=(10 ** CUSTOM_USDT.decimals).to_bytes(32) + bytes(32),
    ) for index, topic in enumerate((PM_REPAY_TOPIC, DEPOSIT_TOPIC_V3))]
    rule = decoder.post_decoding_rules()[CPT_FLYING_TULIP][0][1]
    result = rule(transaction, events, logs)
    assert len(result) == transfer_count + 1
    assert [(event.event_type, event.event_subtype, event.amount) for event in result[:-1]] == [
        (HistoryEventType.SPEND, HistoryEventSubType.PAYBACK_DEBT, ONE),
        (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL, ONE),
    ][:transfer_count]
    assert unrelated == original_unrelated
    snapshot = deepcopy(result)
    assert rule(transaction, result, logs) == snapshot
    base.make_event.assert_not_called()
