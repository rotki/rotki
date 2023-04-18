from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.uniswap.constants import CPT_UNISWAP_V2
from rotkehlchen.chain.ethereum.modules.uniswap.v2 import Uniswapv2Accountant
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USDC
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import make_evm_address, make_random_bytes
from rotkehlchen.types import Location, Price, Timestamp, make_evm_tx_hash
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.accounting.accountant import Accountant
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer


TIMESTAMP_1_SECS = Timestamp(1624395186)
TIMESTAMP_2_SECS = Timestamp(TIMESTAMP_1_SECS + 5)

TIMESTAMP_1_MS = ts_sec_to_ms(TIMESTAMP_1_SECS)
TIMESTAMP_2_MS = ts_sec_to_ms(TIMESTAMP_2_SECS)

EVM_HASH = make_evm_tx_hash(make_random_bytes(32))
EVM_HASH_2 = make_evm_tx_hash(make_random_bytes(32))

USER_ADDRESS = make_evm_address()

mocked_price_queries_profit = {
    A_USDC.identifier: {
        'EUR': {TIMESTAMP_2_SECS: FVal('1.50')},
        'USD': {TIMESTAMP_2_SECS: FVal('1.50')},
    },
    A_DAI.identifier: {
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
        balance=Balance(amount=FVal('0.002931805211106758')),
        location_label=USER_ADDRESS,
        notes='Burned 0.002931805211106758 ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        event_identifier=EVM_HASH,
        sequence_index=118,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=A_USDC,
        balance=Balance(amount=FVal('25')),
        location_label=USER_ADDRESS,
        notes='Deposit 25 USDC to uniswap-v2 LP 0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5',  # noqa: E501
        counterparty=CPT_UNISWAP_V2,
    ), EvmEvent(
        event_identifier=EVM_HASH,
        sequence_index=119,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=A_DAI,
        balance=Balance(amount=FVal('24.994824629555601269')),
        location_label=USER_ADDRESS,
        notes='Deposit 24.994824629555601269 DAI to uniswap-v2 LP 0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5',  # noqa: E501
        counterparty=CPT_UNISWAP_V2,
    ), EvmEvent(
        event_identifier=EVM_HASH,
        sequence_index=120,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:1/erc20:0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5'),
        balance=Balance(amount=FVal('0.000022187913295974')),
        location_label=USER_ADDRESS,
        notes='Receive 0.000022187913295974 UNI-V2 from uniswap-v2 pool',
        counterparty=CPT_UNISWAP_V2,
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
        balance=Balance(amount=FVal('0.002931805211106758')),
        location_label=USER_ADDRESS,
        notes='Burned 0.002931805211106758 ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        event_identifier=EVM_HASH_2,
        sequence_index=118,
        timestamp=TIMESTAMP_2_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=A_USDC,
        balance=Balance(amount=FVal('25')),
        location_label=USER_ADDRESS,
        notes='Remove 25 USDC from uniswap-v2 LP 0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5',  # noqa: E501
        counterparty=CPT_UNISWAP_V2,
    ), EvmEvent(
        event_identifier=EVM_HASH_2,
        sequence_index=119,
        timestamp=TIMESTAMP_2_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=A_DAI,
        balance=Balance(amount=FVal('24.994824629555601269')),
        location_label=USER_ADDRESS,
        notes='Remove 24.994824629555601269 DAI from uniswap-v2 LP 0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5',  # noqa: E501
        counterparty=CPT_UNISWAP_V2,
    ), EvmEvent(
        event_identifier=EVM_HASH_2,
        sequence_index=120,
        timestamp=TIMESTAMP_2_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=Asset('eip155:1/erc20:0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5'),
        balance=Balance(amount=FVal('0.000022187913295974')),
        location_label=USER_ADDRESS,
        notes='Send 0.000022187913295974 UNI-V2 to uniswap-v2 pool',
        counterparty=CPT_UNISWAP_V2,
    ),
]


@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('mocked_price_queries', [mocked_price_queries_profit])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_uniswap_v2_multiple_deposit_and_withdrawal_profit(accountant: 'Accountant', ethereum_inquirer: 'EvmNodeInquirer'):  # noqa: E501
    """Test that PnL calculation during withdrawal are correct."""
    pot = accountant.pots[0]
    transactions = pot.transactions
    uniswap_accountant = Uniswapv2Accountant(
        node_inquirer=ethereum_inquirer,
        msg_aggregator=ethereum_inquirer.database.msg_aggregator,
    )
    uniswap_settings = uniswap_accountant.event_settings(pot)
    transactions.tx_event_settings.update(uniswap_settings)
    events_iterator = iter(DEPOSIT_ENTRIES + WITHDRAWAL_ENTRIES)
    for event in events_iterator:
        pot.transactions.process(event=event, events_iterator=events_iterator)

    expected_events = [
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Deposit 25 USDC to uniswap-v2 LP 0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SECS,
            asset=A_USDC,
            free_amount=ZERO,
            taxable_amount=FVal(25),
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),  # Deposits are not taxable
            cost_basis=None,
            index=0,
            extra_data={'tx_hash': EVM_HASH.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Deposit 24.994824629555601269 DAI to uniswap-v2 LP 0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5',  # noqa: E501
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SECS,
            asset=A_DAI,
            free_amount=ZERO,
            taxable_amount=FVal('24.994824629555601269'),
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),  # Deposits are not taxable
            cost_basis=None,
            index=1,
            extra_data={'tx_hash': EVM_HASH.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Receive 0.000022187913295974 UNI-V2 from uniswap-v2 pool',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SECS,
            asset=Asset('eip155:1/erc20:0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5'),
            free_amount=FVal('0.000022187913295974'),
            taxable_amount=ZERO,
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),
            cost_basis=None,
            index=2,
            extra_data={'tx_hash': EVM_HASH.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Gained 8.333333333333333333333333333 USDC from withdrawing 25 USDC from uniswap-v2 pool',  # noqa: E501
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_2_SECS,
            asset=A_USDC,
            free_amount=ZERO,
            taxable_amount=FVal('8.333333333333333333333333333'),
            price=Price(FVal('1.50')),
            pnl=PNL(taxable=FVal('12.50000000000000000000000000'), free=ZERO),  # profit is taxable
            cost_basis=None,
            index=3,
            extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Remove 25 USDC from uniswap-v2 LP 0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5',  # noqa: E501
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_2_SECS,
            asset=A_USDC,
            free_amount=FVal('25'),
            taxable_amount=ZERO,
            price=Price(FVal('1.50')),
            pnl=PNL(taxable=ZERO, free=ZERO),  # withdrawals are not taxable
            cost_basis=None,
            index=4,
            extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Gained 8.331608209851867089666666667 DAI from withdrawing 24.994824629555601269 DAI from uniswap-v2 pool',  # noqa: E501
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_2_SECS,
            asset=A_DAI,
            free_amount=ZERO,
            taxable_amount=FVal('8.331608209851867089666666667'),
            price=Price(FVal('1.50')),
            pnl=PNL(taxable=FVal('12.49741231477780063450000000'), free=ZERO),  # profit is taxable
            cost_basis=None,
            index=5,
            extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Remove 24.994824629555601269 DAI from uniswap-v2 LP 0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5',  # noqa: E501
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_2_SECS,
            asset=A_DAI,
            free_amount=FVal('24.994824629555601269'),
            taxable_amount=ZERO,
            price=Price(FVal('1.50')),
            pnl=PNL(taxable=ZERO, free=ZERO),  # withdrawals are not taxable
            cost_basis=None,
            index=6,
            extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Send 0.000022187913295974 UNI-V2 to uniswap-v2 pool',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_2_SECS,
            asset=Asset('eip155:1/erc20:0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5'),
            free_amount=ZERO,
            taxable_amount=FVal('0.000022187913295974'),
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),
            cost_basis=None,
            index=7,
            extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
        ),
    ]

    expected_events[3].count_cost_basis_pnl = True
    expected_events[5].count_cost_basis_pnl = True
    assert pot.processed_events == expected_events


@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('mocked_price_queries', [mocked_price_queries_loss])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_uniswap_v2_multiple_deposit_and_withdrawal_loss(accountant: 'Accountant', ethereum_inquirer: 'EvmNodeInquirer'):  # noqa: E501
    """Test that PnL calculation during withdrawal are correct."""
    pot = accountant.pots[0]
    transactions = pot.transactions
    uniswap_accountant = Uniswapv2Accountant(
        node_inquirer=ethereum_inquirer,
        msg_aggregator=ethereum_inquirer.database.msg_aggregator,
    )
    uniswap_settings = uniswap_accountant.event_settings(pot)
    transactions.tx_event_settings.update(uniswap_settings)
    events_iterator = iter(DEPOSIT_ENTRIES + WITHDRAWAL_ENTRIES)
    for event in events_iterator:
        pot.transactions.process(event=event, events_iterator=events_iterator)

    expected_events = [
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Deposit 25 USDC to uniswap-v2 LP 0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SECS,
            asset=A_USDC,
            free_amount=ZERO,
            taxable_amount=FVal(25),
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),  # Deposits are not taxable
            cost_basis=None,
            index=0,
            extra_data={'tx_hash': EVM_HASH.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Deposit 24.994824629555601269 DAI to uniswap-v2 LP 0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5',  # noqa: E501
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SECS,
            asset=A_DAI,
            free_amount=ZERO,
            taxable_amount=FVal('24.994824629555601269'),
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),  # Deposits are not taxable
            cost_basis=None,
            index=1,
            extra_data={'tx_hash': EVM_HASH.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Receive 0.000022187913295974 UNI-V2 from uniswap-v2 pool',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SECS,
            asset=Asset('eip155:1/erc20:0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5'),
            free_amount=FVal('0.000022187913295974'),
            taxable_amount=ZERO,
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),
            cost_basis=None,
            index=2,
            extra_data={'tx_hash': EVM_HASH.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Lost 30.55555555555555555555555556 USDC from withdrawing 25 USDC from uniswap-v2 pool',  # noqa: E501
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_2_SECS,
            asset=A_USDC,
            free_amount=ZERO,
            taxable_amount=FVal('30.55555555555555555555555556'),
            price=Price(FVal('0.45')),
            pnl=PNL(taxable=FVal('13.75000000000000000000000000'), free=ZERO),  # loss is taxable
            cost_basis=None,
            index=3,
            extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Remove 25 USDC from uniswap-v2 LP 0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5',  # noqa: E501
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_2_SECS,
            asset=A_USDC,
            free_amount=FVal('25'),
            taxable_amount=ZERO,
            price=Price(FVal('0.45')),
            pnl=PNL(taxable=ZERO, free=ZERO),  # withdrawals are not taxable
            cost_basis=None,
            index=4,
            extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Lost 30.54923010279017932877777778 DAI from withdrawing 24.994824629555601269 DAI from uniswap-v2 pool',  # noqa: E501
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_2_SECS,
            asset=A_DAI,
            free_amount=ZERO,
            taxable_amount=FVal('30.54923010279017932877777778'),
            price=Price(FVal('0.45')),
            pnl=PNL(taxable=FVal('13.74715354625558069795000000'), free=ZERO),  # loss is taxable
            cost_basis=None,
            index=5,
            extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Remove 24.994824629555601269 DAI from uniswap-v2 LP 0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5',  # noqa: E501
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_2_SECS,
            asset=A_DAI,
            free_amount=FVal('24.994824629555601269'),
            taxable_amount=ZERO,
            price=Price(FVal('0.45')),
            pnl=PNL(taxable=ZERO, free=ZERO),  # withdrawals are not taxable
            cost_basis=None,
            index=6,
            extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
            notes='Send 0.000022187913295974 UNI-V2 to uniswap-v2 pool',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_2_SECS,
            asset=Asset('eip155:1/erc20:0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5'),
            free_amount=ZERO,
            taxable_amount=FVal('0.000022187913295974'),
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),
            cost_basis=None,
            index=7,
            extra_data={'tx_hash': EVM_HASH_2.hex()},  # pylint: disable=no-member
        ),
    ]

    expected_events[3].count_cost_basis_pnl = True
    expected_events[5].count_cost_basis_pnl = True
    assert pot.processed_events == expected_events
