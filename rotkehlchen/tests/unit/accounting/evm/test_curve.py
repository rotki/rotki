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
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USDC, A_USDT
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import Location, Price, Timestamp
from rotkehlchen.utils.misc import ts_sec_to_ms

TIMESTAMP_1_SECS = Timestamp(1624395186)
TIMESTAMP_1_MS = ts_sec_to_ms(TIMESTAMP_1_SECS)

MOCKED_PRICES = {
    'ETH': {
        'EUR': {
            TIMESTAMP_1_SECS: Price(ONE),
        },
    },
    Asset('eip155:1/erc20:0xC25a3A3b969415c80451098fa907EC722572917F').identifier: {
        'EUR': {
            TIMESTAMP_1_SECS: Price(ONE),
        },
    },
    A_DAI.identifier: {
        'EUR': {
            TIMESTAMP_1_SECS: Price(ONE),
        },
    },
    A_USDC.identifier: {
        'EUR': {
            TIMESTAMP_1_SECS: Price(ONE),
        },
    },
    A_USDT.identifier: {
        'EUR': {
            TIMESTAMP_1_SECS: Price(ONE),
        },
    },
    Asset('eip155:1/erc20:0x57Ab1ec28D129707052df4dF418D58a2D46d5f51').identifier: {
        'EUR': {
            TIMESTAMP_1_SECS: Price(ONE),
        },
    },

}

EVM_HASH = make_evm_tx_hash()
USER_ADDRESS = make_evm_address()

DEPOSIT_ENTRIES = [
    EvmEvent(
        tx_hash=EVM_HASH,
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
        tx_hash=EVM_HASH,
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
        tx_hash=EVM_HASH,
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
        tx_hash=EVM_HASH,
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
        tx_hash=EVM_HASH,
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
        tx_hash=EVM_HASH,
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


@pytest.mark.parametrize('mocked_price_queries', [MOCKED_PRICES])
def test_curve_multiple_deposit(accountant: 'Accountant', ethereum_inquirer: 'EvmNodeInquirer'):
    """Test that the default accounting settings for receiving are correct"""
    pot = accountant.pots[0]
    transactions = pot.history_base_entries
    curve_accountant = CurveAccountant(
        node_inquirer=ethereum_inquirer,
        msg_aggregator=ethereum_inquirer.database.msg_aggregator,
    )
    curve_settings = curve_accountant.event_settings(pot)
    transactions.tx_event_settings.update(curve_settings)
    events_iterator = iter(DEPOSIT_ENTRIES)
    for event in events_iterator:
        pot.history_base_entries.process(event=event, events_iterator=events_iterator)

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
