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
from rotkehlchen.chain.ethereum.modules.curve.accountant import CurveAccountant
from rotkehlchen.chain.ethereum.modules.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USD, A_USDC, A_USDT
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import make_evm_address, make_random_bytes
from rotkehlchen.types import Location, Price, Timestamp, make_evm_tx_hash
from rotkehlchen.utils.misc import ts_sec_to_ms

TIMESTAMP_1_SECS = Timestamp(1624395186)
TIMESTAMP_2_SECS = Timestamp(TIMESTAMP_1_SECS + 5)

TIMESTAMP_1_MS = ts_sec_to_ms(TIMESTAMP_1_SECS)
TIMESTAMP_2_MS = ts_sec_to_ms(TIMESTAMP_2_SECS)

mocked_price_queries_profit = {
    A_USDC.identifier: {
        'EUR': {TIMESTAMP_2_SECS: FVal('1.50')},
        'USD': {TIMESTAMP_2_SECS: FVal('1.50')},
    },
    A_DAI.identifier: {
        'EUR': {TIMESTAMP_2_SECS: FVal('1.50')},
        'USD': {TIMESTAMP_2_SECS: FVal('1.50')},
    },
    A_USDT.identifier: {
        'EUR': {TIMESTAMP_2_SECS: FVal('1.50')},
        'USD': {TIMESTAMP_2_SECS: FVal('1.50')},
    },
    Asset('eip155:1/erc20:0x57Ab1ec28D129707052df4dF418D58a2D46d5f51').identifier: {
        'EUR': {TIMESTAMP_2_SECS: FVal('1.50')},
        'USD': {TIMESTAMP_2_SECS: FVal('1.50')},
    },
}

mocked_price_queries_loss = {
    A_USDC.identifier: {
        'EUR': {TIMESTAMP_2_SECS: FVal('0.45')},
        'USD': {TIMESTAMP_2_SECS: FVal('0.45')},
    },
    A_DAI.identifier: {
        'EUR': {TIMESTAMP_2_SECS: FVal('0.45')},
        'USD': {TIMESTAMP_2_SECS: FVal('0.45')},
    },
    A_USDT.identifier: {
        'EUR': {TIMESTAMP_2_SECS: FVal('0.45')},
        'USD': {TIMESTAMP_2_SECS: FVal('0.45')},
    },
    Asset('eip155:1/erc20:0x57Ab1ec28D129707052df4dF418D58a2D46d5f51').identifier: {
        'EUR': {TIMESTAMP_2_SECS: FVal('0.45')},
        'USD': {TIMESTAMP_2_SECS: FVal('0.45')},
    },
}

EVM_HASH = make_evm_tx_hash(make_random_bytes(32))
EVM_HASH_2 = make_evm_tx_hash(make_random_bytes(32))

USER_ADDRESS = make_evm_address()

DEPOSIT_ENTRIES = [
    EvmEvent(
        event_identifier=EVM_HASH,
        sequence_index=0,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal('0.011180845456491718')),
        location_label=USER_ADDRESS,
        notes='Burned 0.011180845456491718 ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        event_identifier=EVM_HASH,
        sequence_index=76,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:1/erc20:0xC25a3A3b969415c80451098fa907EC722572917F'),
        balance=Balance(amount=FVal('9.423568821947938716')),
        location_label=USER_ADDRESS,
        notes='Receive 9.423568821947938716 crvPlain3andSUSD after depositing in curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD',  # noqa: E501
        counterparty=CPT_CURVE,
        extra_data={'deposit_events_num': 4},
    ), EvmEvent(
        event_identifier=EVM_HASH,
        sequence_index=77,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=A_DAI,
        balance=Balance(amount=FVal('10')),
        location_label=USER_ADDRESS,
        notes='Deposit 10 DAI in curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD',
        counterparty=CPT_CURVE,
    ), EvmEvent(
        event_identifier=EVM_HASH,
        sequence_index=77,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=A_USDC,
        balance=Balance(amount=FVal('0')),
        location_label=USER_ADDRESS,
        notes='Deposit 0 USDC in curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD',
        counterparty=CPT_CURVE,
    ), EvmEvent(
        event_identifier=EVM_HASH,
        sequence_index=78,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=A_USDT,
        balance=Balance(amount=FVal('5')),
        location_label=USER_ADDRESS,
        notes='Deposit 5 USDT in curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD',
        counterparty=CPT_CURVE,
    ), EvmEvent(
        event_identifier=EVM_HASH,
        sequence_index=79,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=Asset('eip155:1/erc20:0x57Ab1ec28D129707052df4dF418D58a2D46d5f51'),
        balance=Balance(amount=FVal('0')),
        location_label=USER_ADDRESS,
        notes='Deposit 0 sUSD in curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD',
        counterparty=CPT_CURVE,
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
        balance=Balance(amount=FVal('0.011180845456491718')),
        location_label=USER_ADDRESS,
        notes='Burned 0.011180845456491718 ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        event_identifier=EVM_HASH_2,
        sequence_index=76,
        timestamp=TIMESTAMP_2_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=Asset('eip155:1/erc20:0xC25a3A3b969415c80451098fa907EC722572917F'),
        balance=Balance(amount=FVal('9.423568821947938716')),
        location_label=USER_ADDRESS,
        notes='Return 9.423568821947938716 crvPlain3andSUSD',
        counterparty=CPT_CURVE,
        extra_data={'withdrawal_events_num': 1},
    ), EvmEvent(
        event_identifier=EVM_HASH_2,
        sequence_index=77,
        timestamp=TIMESTAMP_2_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=A_DAI,
        balance=Balance(amount=FVal('15')),
        location_label=USER_ADDRESS,
        notes='Receive 15 DAI from the curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD',  # noqa: E501
        counterparty=CPT_CURVE,
    ),
]


@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_curve_multiple_deposit(accountant: 'Accountant', ethereum_inquirer: 'EvmNodeInquirer'):
    """Test that the default accounting settings for receiving are correct"""
    pot = accountant.pots[0]
    transactions = pot.transactions
    curve_accountant = CurveAccountant(
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
            notes='Deposit 10 DAI in curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SECS,
            asset=A_DAI,
            free_amount=ZERO,
            taxable_amount=FVal(10),
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),  # Deposits are not taxable
            cost_basis=None,
            index=0,
            extra_data={'tx_hash': EVM_HASH.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Deposit 5 USDT in curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SECS,
            asset=A_USDT,
            free_amount=ZERO,
            taxable_amount=FVal(5),
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),  # Deposits are not taxable
            cost_basis=None,
            index=1,
            extra_data={'tx_hash': EVM_HASH.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Receive 9.423568821947938716 crvPlain3andSUSD after depositing in curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD',  # noqa: E501
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SECS,
            asset=Asset('eip155:1/erc20:0xC25a3A3b969415c80451098fa907EC722572917F'),
            free_amount=FVal('9.423568821947938716'),
            taxable_amount=ZERO,
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),  # Deposits are not taxable
            cost_basis=None,
            index=2,
            extra_data={'tx_hash': EVM_HASH.hex()},  # pylint: disable=no-member
        ),
    ]
    assert pot.processed_events == expected_events


@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('mocked_price_queries', [mocked_price_queries_profit])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_curve_multiple_deposit_and_withdrawal_profit(accountant: 'Accountant', ethereum_inquirer: 'EvmNodeInquirer'):  # noqa: E501
    """Test that the default accounting settings for receiving are correct"""
    pot = accountant.pots[0]
    transactions = pot.transactions
    curve_accountant = CurveAccountant(
        node_inquirer=ethereum_inquirer,
        msg_aggregator=ethereum_inquirer.database.msg_aggregator,
    )
    curve_settings = curve_accountant.event_settings(pot)
    transactions.tx_event_settings.update(curve_settings)
    events_iterator = iter(DEPOSIT_ENTRIES + WITHDRAWAL_ENTRIES)
    with patch('rotkehlchen.assets.asset.Asset.is_fiat', return_value=False):
        for event in events_iterator:
            pot.transactions.process(event=event, events_iterator=events_iterator)

        expected_events = [
            ProcessedAccountingEvent(
                type=AccountingEventType.TRANSACTION_EVENT,
                notes='Deposit 10 DAI in curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD',
                location=Location.ETHEREUM,
                timestamp=TIMESTAMP_1_SECS,
                asset=A_DAI,
                free_amount=ZERO,
                taxable_amount=FVal(10),
                price=Price(ONE),
                pnl=PNL(taxable=ZERO, free=ZERO),  # Deposits are not taxable
                cost_basis=None,
                index=0,
                extra_data={'tx_hash': EVM_HASH.hex()},  # pylint: disable=no-member
            ),
            ProcessedAccountingEvent(
                type=AccountingEventType.TRANSACTION_EVENT,
                notes='Deposit 5 USDT in curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD',
                location=Location.ETHEREUM,
                timestamp=TIMESTAMP_1_SECS,
                asset=A_USDT,
                free_amount=ZERO,
                taxable_amount=FVal(5),
                price=Price(ONE),
                pnl=PNL(taxable=ZERO, free=ZERO),  # Deposits are not taxable
                cost_basis=None,
                index=1,
                extra_data={'tx_hash': EVM_HASH.hex()},  # pylint: disable=no-member
            ),
            ProcessedAccountingEvent(
                type=AccountingEventType.TRANSACTION_EVENT,
                notes='Receive 9.423568821947938716 crvPlain3andSUSD after depositing in curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD',  # noqa: E501
                location=Location.ETHEREUM,
                timestamp=TIMESTAMP_1_SECS,
                asset=Asset('eip155:1/erc20:0xC25a3A3b969415c80451098fa907EC722572917F'),
                free_amount=FVal('9.423568821947938716'),
                taxable_amount=ZERO,
                price=Price(ONE),
                pnl=PNL(taxable=ZERO, free=ZERO),  # Deposits are not taxable
                cost_basis=None,
                index=2,
                extra_data={'tx_hash': EVM_HASH.hex()},  # pylint: disable=no-member
            ),
            ProcessedAccountingEvent(
                type=AccountingEventType.TRANSACTION_EVENT,
                notes='Gained 7.50 USD from withdrawing 15 DAI from curve pool',
                location=Location.ETHEREUM,
                timestamp=TIMESTAMP_2_SECS,
                asset=A_USD,
                free_amount=ZERO,
                taxable_amount=FVal('7.50'),
                price=Price(ONE),
                pnl=PNL(taxable=FVal('7.50'), free=ZERO),  # profit is taxable
                cost_basis=None,
                index=3,
                extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
            ),
            ProcessedAccountingEvent(
                type=AccountingEventType.TRANSACTION_EVENT,
                notes='Receive 15 DAI from the curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD',  # noqa: E501
                location=Location.ETHEREUM,
                timestamp=TIMESTAMP_2_SECS,
                asset=A_DAI,
                free_amount=FVal('15'),
                taxable_amount=ZERO,
                price=Price(FVal('1.50')),
                pnl=PNL(taxable=ZERO, free=ZERO),  # withdrawals are not taxable
                cost_basis=None,
                index=4,
                extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
            ),
            ProcessedAccountingEvent(
                type=AccountingEventType.TRANSACTION_EVENT,
                notes='Return 9.423568821947938716 crvPlain3andSUSD',
                location=Location.ETHEREUM,
                timestamp=TIMESTAMP_2_SECS,
                asset=Asset('eip155:1/erc20:0xC25a3A3b969415c80451098fa907EC722572917F'),
                free_amount=ZERO,
                taxable_amount=FVal('9.423568821947938716'),
                price=Price(ONE),
                pnl=PNL(taxable=ZERO, free=ZERO),
                cost_basis=None,
                index=5,
                extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
            ),
        ]

        expected_events[3].count_cost_basis_pnl = True
        assert pot.processed_events == expected_events


@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('mocked_price_queries', [mocked_price_queries_loss])
def test_curve_multiple_deposit_and_withdrawal_loss(accountant: 'Accountant', ethereum_inquirer: 'EvmNodeInquirer'):  # noqa: E501
    """Test that the default accounting settings for receiving are correct"""
    pot = accountant.pots[0]
    transactions = pot.transactions
    curve_accountant = CurveAccountant(
        node_inquirer=ethereum_inquirer,
        msg_aggregator=ethereum_inquirer.database.msg_aggregator,
    )
    curve_settings = curve_accountant.event_settings(pot)
    transactions.tx_event_settings.update(curve_settings)
    events_iterator = iter(DEPOSIT_ENTRIES + WITHDRAWAL_ENTRIES)
    for event in events_iterator:
        pot.transactions.process(event=event, events_iterator=events_iterator)

    expected_events = [
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Deposit 10 DAI in curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SECS,
            asset=A_DAI,
            free_amount=ZERO,
            taxable_amount=FVal(10),
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),  # Deposits are not taxable
            cost_basis=None,
            index=0,
            extra_data={'tx_hash': EVM_HASH.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Deposit 5 USDT in curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SECS,
            asset=A_USDT,
            free_amount=ZERO,
            taxable_amount=FVal(5),
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),  # Deposits are not taxable
            cost_basis=None,
            index=1,
            extra_data={'tx_hash': EVM_HASH.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Receive 9.423568821947938716 crvPlain3andSUSD after depositing in curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD',  # noqa: E501
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SECS,
            asset=Asset('eip155:1/erc20:0xC25a3A3b969415c80451098fa907EC722572917F'),
            free_amount=FVal('9.423568821947938716'),
            taxable_amount=ZERO,
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),  # Deposits are not taxable
            cost_basis=None,
            index=2,
            extra_data={'tx_hash': EVM_HASH.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Lost 8.25 USD from withdrawing 15 DAI from curve pool',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_2_SECS,
            asset=A_USD,
            free_amount=ZERO,
            taxable_amount=FVal('8.25'),
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),
            cost_basis=None,
            index=3,
            extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Receive 15 DAI from the curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD',  # noqa: E501
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_2_SECS,
            asset=A_DAI,
            free_amount=FVal('15'),
            taxable_amount=ZERO,
            price=Price(FVal('0.45')),
            pnl=PNL(taxable=ZERO, free=ZERO),  # withdrawals are not taxable
            cost_basis=None,
            index=4,
            extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Return 9.423568821947938716 crvPlain3andSUSD',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_2_SECS,
            asset=Asset('eip155:1/erc20:0xC25a3A3b969415c80451098fa907EC722572917F'),
            free_amount=ZERO,
            taxable_amount=FVal('9.423568821947938716'),
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),
            cost_basis=None,
            index=5,
            extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
        ),
    ]

    expected_events[3].count_cost_basis_pnl = True
    assert pot.processed_events == expected_events
