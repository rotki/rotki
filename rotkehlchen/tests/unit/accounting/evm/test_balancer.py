from typing import TYPE_CHECKING

import pytest
from more_itertools import peekable

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.balancer.constants import CPT_BALANCER_V1
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_USDC
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import Location, Price, Timestamp
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.accounting.accountant import Accountant

TIMESTAMP_1_SECS = Timestamp(15931863800)
TIMESTAMP_1_MS = ts_sec_to_ms(TIMESTAMP_1_SECS)


EVM_HASH = make_evm_tx_hash()
USER_ADDRESS = make_evm_address()

DEPOSIT_ENTRIES = [
    EvmEvent(
        tx_hash=EVM_HASH,
        sequence_index=131,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:1/erc20:0x72Cd8f4504941Bf8c5a21d1Fd83A96499FD71d2C'),
        balance=Balance(amount=FVal('1675.495956074927519908')),
        location_label=USER_ADDRESS,
        notes='Receive 1675.495956074927519908 BPT from a Balancer v1 pool',
        counterparty=CPT_BALANCER_V1,
        identifier=None,
        extra_data={'deposit_events_num': 4},
    ), EvmEvent(
        tx_hash=EVM_HASH,
        sequence_index=132,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=Asset('eip155:1/erc20:0xe2f2a5C287993345a840Db3B0845fbC70f5935a5'),
        balance=Balance(amount=FVal('131578.947368421052491563')),
        location_label=USER_ADDRESS,
        notes='Deposit 131578.947368421052491563 mUSD to a Balancer v1 pool',
        counterparty=CPT_BALANCER_V1,
        identifier=None,
        extra_data=None,
    ), EvmEvent(
        tx_hash=EVM_HASH,
        sequence_index=134,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=A_USDC,
        balance=Balance(amount=FVal('131421.703252')),
        location_label=USER_ADDRESS,
        notes='Deposit 131421.703252 USDC to a Balancer v1 pool',
        counterparty=CPT_BALANCER_V1,
        identifier=None,
        extra_data=None,
    ), EvmEvent(
        tx_hash=EVM_HASH,
        sequence_index=144,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REFUND,
        asset=Asset('eip155:1/erc20:0xe2f2a5C287993345a840Db3B0845fbC70f5935a5'),
        balance=Balance(amount=FVal('6578.947368421052624578')),
        location_label=USER_ADDRESS,
        notes='Refunded 6578.947368421052624578 mUSD after depositing in Balancer V1 pool',
        counterparty=CPT_BALANCER_V1,
        identifier=None,
        extra_data=None,
    ), EvmEvent(
        tx_hash=EVM_HASH,
        sequence_index=145,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REFUND,
        asset=A_USDC,
        balance=Balance(amount=FVal('6571.085163')),
        location_label=USER_ADDRESS,
        notes='Refunded 6571.085163 USDC after depositing in Balancer V1 pool',
        counterparty=CPT_BALANCER_V1,
        identifier=None,
        extra_data=None,
    ), EvmEvent(
        tx_hash=EVM_HASH,
        sequence_index=146,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:1/erc20:0xe2f2a5C287993345a840Db3B0845fbC70f5935a5'),
        balance=Balance(amount=FVal('1.157920892373161954235709850E+59')),
        location_label=USER_ADDRESS,
        notes='Approve 115792089237316195423570985000000000000000000000000000000000 mUSD of 0x549C0421c69Be943A2A60e76B19b4A801682cBD3 for spending by 0x9ED47950144e51925166192Bf0aE95553939030a',  # noqa: E501
        counterparty='0x9ED47950144e51925166192Bf0aE95553939030a',
        identifier=None,
        extra_data=None,
    ),
]


@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('accounting_initialize_parameters', [True])
def test_balancer_multiple_deposit(accountant: 'Accountant'):
    """Test that the default accounting settings for balancer are correct"""
    pot = accountant.pots[0]
    events_iterator = peekable(DEPOSIT_ENTRIES)
    for event in events_iterator:
        pot.events_accountant.process(event=event, events_iterator=events_iterator)  # type: ignore

    expected_events = [
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Deposit 131578.947368421052491563 mUSD to a Balancer v1 pool',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SECS,
            asset=Asset('eip155:1/erc20:0xe2f2a5C287993345a840Db3B0845fbC70f5935a5'),
            free_amount=ZERO,
            taxable_amount=FVal('131578.947368421052491563'),
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),  # Deposits are not taxable
            cost_basis=None,
            index=0,
            extra_data={'tx_hash': EVM_HASH.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Deposit 131421.703252 USDC to a Balancer v1 pool',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SECS,
            asset=A_USDC,
            free_amount=ZERO,
            taxable_amount=FVal('131421.703252'),
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),  # Deposits are not taxable
            cost_basis=None,
            index=1,
            extra_data={'tx_hash': EVM_HASH.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Refunded 6578.947368421052624578 mUSD after depositing in Balancer V1 pool',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SECS,
            asset=Asset('eip155:1/erc20:0xe2f2a5C287993345a840Db3B0845fbC70f5935a5'),
            free_amount=ZERO,
            taxable_amount=FVal('6578.947368421052624578'),
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),  # Withdrawals/refunds are not taxable
            cost_basis=None,
            index=2,
            extra_data={'tx_hash': EVM_HASH.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Refunded 6571.085163 USDC after depositing in Balancer V1 pool',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SECS,
            asset=A_USDC,
            free_amount=ZERO,
            taxable_amount=FVal('6571.085163'),
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),  # Withdrawals/refunds are not taxable
            cost_basis=None,
            index=3,
            extra_data={'tx_hash': EVM_HASH.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Receive 1675.495956074927519908 BPT from a Balancer v1 pool',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SECS,
            asset=Asset('eip155:1/erc20:0x72Cd8f4504941Bf8c5a21d1Fd83A96499FD71d2C'),
            free_amount=FVal('1675.495956074927519908'),
            taxable_amount=ZERO,
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),  # Deposits are not taxable
            cost_basis=None,
            index=4,
            extra_data={'tx_hash': EVM_HASH.hex()},  # pylint: disable=no-member
        ),
    ]
    assert pot.processed_events == expected_events
