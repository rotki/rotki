from unittest.mock import patch

import pytest

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.balancer.constants import CPT_BALANCER_V1
from rotkehlchen.chain.ethereum.modules.balancer.v1.accountant import Balancerv1Accountant
from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USDC
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import make_evm_address, make_random_bytes
from rotkehlchen.types import Location, Price, Timestamp, make_evm_tx_hash
from rotkehlchen.utils.misc import ts_sec_to_ms

TIMESTAMP_1_SECS = Timestamp(15931863800)
TIMESTAMP_2_SECS = Timestamp(TIMESTAMP_1_SECS + 5)

TIMESTAMP_1_MS = ts_sec_to_ms(TIMESTAMP_1_SECS)
TIMESTAMP_2_MS = ts_sec_to_ms(TIMESTAMP_2_SECS)


EVM_HASH = make_evm_tx_hash(make_random_bytes(32))
EVM_HASH_2 = make_evm_tx_hash(make_random_bytes(32))

USER_ADDRESS = make_evm_address()

mocked_price_queries_profit = {
    A_USDC.identifier: {
        'EUR': {TIMESTAMP_2_SECS: FVal('1.05')},
        'USD': {TIMESTAMP_2_SECS: FVal('1.05')},
    },
    A_DAI.identifier: {
        'EUR': {TIMESTAMP_2_SECS: FVal('1.05')},
        'USD': {TIMESTAMP_2_SECS: FVal('1.05')},
    },
}

mocked_price_queries_loss = {
    A_USDC.identifier: {
        'EUR': {15931863805: FVal('0.45')},
        'USD': {15931863805: FVal('0.45')},
    },
    A_DAI.identifier: {
        'EUR': {15931863805: FVal('0.45')},
        'USD': {15931863805: FVal('0.45')},
    },
}

DEPOSIT_ENTRIES = [
    EvmEvent(
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
    ), EvmEvent(
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
    ), EvmEvent(
        event_identifier=EVM_HASH,
        sequence_index=132,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=A_DAI,
        balance=Balance(amount=FVal('131578.947368421052491563')),
        location_label=USER_ADDRESS,
        notes='Deposit 131578.947368421052491563 DAI to a Balancer v1 pool',
        counterparty=CPT_BALANCER_V1,
        identifier=None,
        extra_data=None,
    ), EvmEvent(
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
    ), EvmEvent(
        event_identifier=EVM_HASH,
        sequence_index=144,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=A_DAI,
        balance=Balance(amount=FVal('6578.947368421052624578')),
        location_label=USER_ADDRESS,
        notes='Refunded 6578.947368421052624578 DAI after depositing in Balancer V1 pool',  # noqa: E501
        counterparty=CPT_BALANCER_V1,
        identifier=None,
        extra_data=None,
    ), EvmEvent(
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
    ), EvmEvent(
        event_identifier=EVM_HASH,
        sequence_index=146,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_DAI,
        balance=Balance(amount=FVal('1.157920892373161954235709850E+59')),
        location_label=USER_ADDRESS,
        notes='Approve 115792089237316195423570985000000000000000000000000000000000 DAI of 0x549C0421c69Be943A2A60e76B19b4A801682cBD3 for spending by 0x9ED47950144e51925166192Bf0aE95553939030a',  # noqa: E501
        counterparty='0x9ED47950144e51925166192Bf0aE95553939030a',
        identifier=None,
        extra_data=None,
    ),
]

WITHDRAWAL_ENTRIES = [
    EvmEvent(
        event_identifier=EVM_HASH_2,
        sequence_index=0,
        timestamp=TIMESTAMP_2_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal('0.00393701451')),
        location_label=USER_ADDRESS,
        notes='Burned 0.00393701451 ETH for gas',
        counterparty='gas',
        identifier=None,
        extra_data=None,
    ), EvmEvent(
        event_identifier=EVM_HASH_2,
        sequence_index=91,
        timestamp=TIMESTAMP_2_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=Asset('eip155:1/erc20:0x72Cd8f4504941Bf8c5a21d1Fd83A96499FD71d2C'),
        balance=Balance(amount=FVal('1675.495956074927519908')),
        location_label=USER_ADDRESS,
        notes='Return 1675.495956074927519908 BPT to a Balancer v1 pool',
        counterparty=CPT_BALANCER_V1,
        identifier=None,
        extra_data={'withdrawal_events_num': 2},
    ), EvmEvent(
        event_identifier=EVM_HASH_2,
        sequence_index=95,
        timestamp=TIMESTAMP_2_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=A_DAI,
        balance=Balance(amount=FVal('124999.999999999999867')),
        location_label=USER_ADDRESS,
        notes='Receive 124999.999999999999867 DAI after removing liquidity from a Balancer v1 pool',  # noqa: E501
        counterparty=CPT_BALANCER_V1,
        identifier=None,
        extra_data=None,
    ), EvmEvent(
        event_identifier=EVM_HASH_2,
        sequence_index=97,
        timestamp=TIMESTAMP_2_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=A_USDC,
        balance=Balance(amount=FVal('124850.618089')),
        location_label=USER_ADDRESS,
        notes='Receive 124850.618089 USDC after removing liquidity from a Balancer v1 pool',  # noqa: E501
        counterparty=CPT_BALANCER_V1,
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
    balancer_v1_accountant = Balancerv1Accountant(
        node_inquirer=ethereum_inquirer,
        msg_aggregator=ethereum_inquirer.database.msg_aggregator,
    )
    balancer_settings = balancer_v1_accountant.event_settings(pot)
    transactions.tx_event_settings.update(balancer_settings)
    events_iterator = iter(DEPOSIT_ENTRIES)
    for event in events_iterator:
        pot.transactions.process(event=event, events_iterator=events_iterator)

    expected_events = [
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Deposit 131578.947368421052491563 DAI to a Balancer v1 pool',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SECS,
            asset=A_DAI,
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
            notes='Refunded 6578.947368421052624578 DAI after depositing in Balancer V1 pool',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SECS,
            asset=A_DAI,
            free_amount=ZERO,
            taxable_amount=FVal('6578.947368421052624578'),
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),  # refunds are not taxable
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
            pnl=PNL(taxable=ZERO, free=ZERO),  # refunds are not taxable
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


@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('mocked_price_queries', [mocked_price_queries_profit])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_balancer_multiple_deposit_and_withdrawal_profit(accountant: 'Accountant', ethereum_inquirer: 'EvmNodeInquirer'):  # noqa: E501
    """Check that PnL is accounted for properly when a change in price for the tokens withdrawn."""
    pot = accountant.pots[0]
    transactions = pot.transactions
    balancer_v1_accountant = Balancerv1Accountant(
        node_inquirer=ethereum_inquirer,
        msg_aggregator=ethereum_inquirer.database.msg_aggregator,
    )
    balancer_settings = balancer_v1_accountant.event_settings(pot)
    transactions.tx_event_settings.update(balancer_settings)
    events_iterator = iter(DEPOSIT_ENTRIES + WITHDRAWAL_ENTRIES)

    with patch('rotkehlchen.assets.asset.Asset.is_fiat', return_value=False):
        for event in events_iterator:
            pot.transactions.process(event=event, events_iterator=events_iterator)

        expected_events = [
            ProcessedAccountingEvent(
                type=AccountingEventType.TRANSACTION_EVENT,
                notes='Deposit 131578.947368421052491563 DAI to a Balancer v1 pool',
                location=Location.ETHEREUM,
                timestamp=TIMESTAMP_1_SECS,
                asset=A_DAI,
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
                notes='Refunded 6578.947368421052624578 DAI after depositing in Balancer V1 pool',
                location=Location.ETHEREUM,
                timestamp=TIMESTAMP_1_SECS,
                asset=A_DAI,
                free_amount=ZERO,
                taxable_amount=FVal('6578.947368421052624578'),
                price=Price(ONE),
                pnl=PNL(taxable=ZERO, free=ZERO),  # refunds are not taxable
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
                pnl=PNL(taxable=ZERO, free=ZERO),  # refunds are not taxable
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
            ProcessedAccountingEvent(
                type=AccountingEventType.TRANSACTION_EVENT,
                notes='Gained 5952.380952380952374633333333 DAI from withdrawing 124999.999999999999867 DAI from balancer-v1 pool',  # noqa: E501
                location=Location.ETHEREUM,
                timestamp=TIMESTAMP_2_SECS,
                asset=A_DAI,
                free_amount=ZERO,
                taxable_amount=FVal('5952.380952380952374633333333'),
                price=Price(FVal('1.05')),
                pnl=PNL(taxable=FVal('6249.999999999999993365'), free=ZERO),  # profit realized is taxable  # noqa: E501
                index=5,
                cost_basis=None,
                extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
            ),
            ProcessedAccountingEvent(
                type=AccountingEventType.TRANSACTION_EVENT,
                notes='Receive 124999.999999999999867 DAI after removing liquidity from a Balancer v1 pool',  # noqa: E501
                location=Location.ETHEREUM,
                timestamp=TIMESTAMP_2_SECS,
                asset=A_DAI,
                free_amount=FVal('124999.999999999999867'),
                taxable_amount=ZERO,
                price=Price(FVal('1.05')),
                pnl=PNL(taxable=ZERO, free=ZERO),  # withdrawals are not taxable
                cost_basis=None,
                index=6,
                extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
            ),
            ProcessedAccountingEvent(
                type=AccountingEventType.TRANSACTION_EVENT,
                notes='Gained 5945.267528047619047619047619 USDC from withdrawing 124850.618089 USDC from balancer-v1 pool',  # noqa: E501
                location=Location.ETHEREUM,
                timestamp=TIMESTAMP_2_SECS,
                asset=A_USDC,
                free_amount=ZERO,
                taxable_amount=FVal('5945.267528047619047619047619'),
                price=Price(FVal('1.05')),
                pnl=PNL(taxable=FVal('6242.530904450000000000000000'), free=ZERO),  # profit realized is taxable  # noqa: E501
                index=7,
                cost_basis=None,
                extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
            ),
            ProcessedAccountingEvent(
                type=AccountingEventType.TRANSACTION_EVENT,
                notes='Receive 124850.618089 USDC after removing liquidity from a Balancer v1 pool',  # noqa: E501
                location=Location.ETHEREUM,
                timestamp=TIMESTAMP_2_SECS,
                asset=A_USDC,
                free_amount=FVal('124850.618089'),
                taxable_amount=ZERO,
                price=Price(FVal('1.05')),
                pnl=PNL(taxable=ZERO, free=ZERO),  # withdrawals are not taxable
                cost_basis=None,
                index=8,
                extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
            ),
            ProcessedAccountingEvent(
                type=AccountingEventType.TRANSACTION_EVENT,
                notes='Return 1675.495956074927519908 BPT to a Balancer v1 pool',
                location=Location.ETHEREUM,
                timestamp=TIMESTAMP_2_SECS,
                asset=Asset('eip155:1/erc20:0x72Cd8f4504941Bf8c5a21d1Fd83A96499FD71d2C'),
                free_amount=ZERO,
                taxable_amount=FVal('1675.495956074927519908'),
                price=Price(ONE),
                pnl=PNL(taxable=ZERO, free=ZERO),
                cost_basis=None,
                index=9,
                extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
            ),
        ]
        # this is needed since `count_cost_basis_pnl`
        # cannot be set at initialization
        expected_events[5].count_cost_basis_pnl = True
        expected_events[7].count_cost_basis_pnl = True
        assert pot.processed_events == expected_events


@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('mocked_price_queries', [mocked_price_queries_loss])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_balancer_multiple_deposit_and_withdrawal_loss(accountant: 'Accountant', ethereum_inquirer: 'EvmNodeInquirer'):  # noqa: E501
    """Check that PnL is accounted for properly when a change in price for the tokens withdrawn."""
    pot = accountant.pots[0]
    transactions = pot.transactions
    balancer_v1_accountant = Balancerv1Accountant(
        node_inquirer=ethereum_inquirer,
        msg_aggregator=ethereum_inquirer.database.msg_aggregator,
    )
    balancer_settings = balancer_v1_accountant.event_settings(pot)
    transactions.tx_event_settings.update(balancer_settings)
    events_iterator = iter(DEPOSIT_ENTRIES + WITHDRAWAL_ENTRIES)

    with patch('rotkehlchen.assets.asset.Asset.is_fiat', return_value=False):
        for event in events_iterator:
            pot.transactions.process(event=event, events_iterator=events_iterator)

        expected_events = [
            ProcessedAccountingEvent(
                type=AccountingEventType.TRANSACTION_EVENT,
                notes='Deposit 131578.947368421052491563 DAI to a Balancer v1 pool',
                location=Location.ETHEREUM,
                timestamp=TIMESTAMP_1_SECS,
                asset=A_DAI,
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
                notes='Refunded 6578.947368421052624578 DAI after depositing in Balancer V1 pool',
                location=Location.ETHEREUM,
                timestamp=TIMESTAMP_1_SECS,
                asset=A_DAI,
                free_amount=ZERO,
                taxable_amount=FVal('6578.947368421052624578'),
                price=Price(ONE),
                pnl=PNL(taxable=ZERO, free=ZERO),  # refunds are not taxable
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
                pnl=PNL(taxable=ZERO, free=ZERO),  # refunds are not taxable
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
                pnl=PNL(taxable=ZERO, free=ZERO),  # withdrawals are not taxable
                cost_basis=None,
                index=4,
                extra_data={'tx_hash': EVM_HASH.hex()},  # pylint: disable=no-member
            ),
            ProcessedAccountingEvent(
                type=AccountingEventType.TRANSACTION_EVENT,
                notes='Lost 152777.7777777777776151888889 DAI from withdrawing 124999.999999999999867 DAI from balancer-v1 pool',  # noqa: E501
                location=Location.ETHEREUM,
                timestamp=TIMESTAMP_2_SECS,
                asset=A_DAI,
                free_amount=ZERO,
                taxable_amount=FVal('152777.7777777777776151888889'),
                price=Price(FVal('0.45')),
                pnl=PNL(taxable=FVal('68749.99999999999992683500000'), free=ZERO),  # profit realized is taxable  # noqa: E501
                index=5,
                cost_basis=None,
                extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
            ),
            ProcessedAccountingEvent(
                type=AccountingEventType.TRANSACTION_EVENT,
                notes='Receive 124999.999999999999867 DAI after removing liquidity from a Balancer v1 pool',  # noqa: E501
                location=Location.ETHEREUM,
                timestamp=TIMESTAMP_2_SECS,
                asset=A_DAI,
                free_amount=FVal('124999.999999999999867'),
                taxable_amount=ZERO,
                price=Price(FVal('0.45')),
                pnl=PNL(taxable=ZERO, free=ZERO),  # withdrawals are not taxable
                cost_basis=None,
                index=6,
                extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
            ),
            ProcessedAccountingEvent(
                type=AccountingEventType.TRANSACTION_EVENT,
                notes='Lost 152595.1998865555555555555556 USDC from withdrawing 124850.618089 USDC from balancer-v1 pool',  # noqa: E501
                location=Location.ETHEREUM,
                timestamp=TIMESTAMP_2_SECS,
                asset=A_USDC,
                free_amount=ZERO,
                taxable_amount=FVal('152595.1998865555555555555556'),
                price=Price(FVal('0.45')),
                pnl=PNL(taxable=FVal('68667.83994895000000000000002'), free=ZERO),  # loss incurred is taxable  # noqa: E501
                index=7,
                cost_basis=None,
                extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
            ),
            ProcessedAccountingEvent(
                type=AccountingEventType.TRANSACTION_EVENT,
                notes='Receive 124850.618089 USDC after removing liquidity from a Balancer v1 pool',  # noqa: E501
                location=Location.ETHEREUM,
                timestamp=TIMESTAMP_2_SECS,
                asset=A_USDC,
                free_amount=FVal('124850.618089'),
                taxable_amount=ZERO,
                price=Price(FVal('0.45')),
                pnl=PNL(taxable=ZERO, free=ZERO),  # withdrawals are not taxable
                cost_basis=None,
                index=8,
                extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
            ),
            ProcessedAccountingEvent(
                type=AccountingEventType.TRANSACTION_EVENT,
                notes='Return 1675.495956074927519908 BPT to a Balancer v1 pool',
                location=Location.ETHEREUM,
                timestamp=TIMESTAMP_2_SECS,
                asset=Asset('eip155:1/erc20:0x72Cd8f4504941Bf8c5a21d1Fd83A96499FD71d2C'),
                free_amount=ZERO,
                taxable_amount=FVal('1675.495956074927519908'),
                price=Price(ONE),
                pnl=PNL(taxable=ZERO, free=ZERO),
                cost_basis=None,
                index=9,
                extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
            ),
        ]
        # this is needed since `count_cost_basis_pnl`
        # cannot be set at initialization
        expected_events[5].count_cost_basis_pnl = True
        expected_events[7].count_cost_basis_pnl = True
        assert pot.processed_events == expected_events
