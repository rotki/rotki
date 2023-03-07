import pytest

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.balancer.constants import CPT_BALANCER_V1
from rotkehlchen.chain.ethereum.modules.balancer.v1.accountant import Balancerv1Accountant
from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
from rotkehlchen.constants.assets import A_ETH, A_USDC
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import make_evm_address, make_random_bytes
from rotkehlchen.types import Location, Price, Timestamp, make_evm_tx_hash
from rotkehlchen.utils.misc import ts_sec_to_ms

TIMESTAMP_1_SECS = Timestamp(15931863800)
TIMESTAMP_1_MS = ts_sec_to_ms(TIMESTAMP_1_SECS)


EVM_HASH = make_evm_tx_hash(make_random_bytes(32))
USER_ADDRESS = make_evm_address()

DEPOSIT_ENTRIES = [
    HistoryBaseEntry(
        event_identifier=EVM_HASH,
        sequence_index=0,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal('0.01452447')),
        location_label=USER_ADDRESS,
        notes='Burned 0.01452447 ETH for gas',
        counterparty='gas',
        identifier=None,
        extra_data=None,
    ), HistoryBaseEntry(
        event_identifier=EVM_HASH,
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
    ), HistoryBaseEntry(
        event_identifier=EVM_HASH,
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
    ), HistoryBaseEntry(
        event_identifier=EVM_HASH,
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
    ), HistoryBaseEntry(
        event_identifier=EVM_HASH,
        sequence_index=144,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=Asset('eip155:1/erc20:0xe2f2a5C287993345a840Db3B0845fbC70f5935a5'),
        balance=Balance(amount=FVal('6578.947368421052624578')),
        location_label=USER_ADDRESS,
        notes='Refunded 6578.947368421052624578 mUSD after depositing in Balancer V1 pool',  # noqa: E501
        counterparty=CPT_BALANCER_V1,
        identifier=None,
        extra_data=None,
    ), HistoryBaseEntry(
        event_identifier=EVM_HASH,
        sequence_index=145,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=A_USDC,
        balance=Balance(amount=FVal('6571.085163')),
        location_label=USER_ADDRESS,
        notes='Refunded 6571.085163 USDC after depositing in Balancer V1 pool',
        counterparty=CPT_BALANCER_V1,
        identifier=None,
        extra_data=None,
    ), HistoryBaseEntry(
        event_identifier=EVM_HASH,
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
def test_balancer_multiple_deposit(accountant: 'Accountant', ethereum_inquirer: 'EvmNodeInquirer'):
    """Test that the default accounting settings for balancer are correct"""
    pot = accountant.pots[0]
    transactions = pot.transactions
    curve_accountant = Balancerv1Accountant(
        node_inquirer=ethereum_inquirer,
        msg_aggregator=ethereum_inquirer.database.msg_aggregator,
    )
    curve_settings = curve_accountant.event_settings(pot)
    transactions.tx_event_settings.update(curve_settings)
    events_iterator = iter(DEPOSIT_ENTRIES)
    for event in events_iterator:
        pot.transactions.process(event=event, events_iterator=events_iterator)

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
