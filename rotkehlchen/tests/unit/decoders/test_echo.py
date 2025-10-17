
import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.base.modules.echo.constants import CPT_ECHO
from rotkehlchen.chain.base.modules.echo.decoder import FUNDING_CONDUIT
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

USDC_TOKEN = Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0xB196cd166602BfcD879Bf12925e348689F6881B8']])
def test_echo_fund(base_inquirer, base_accounts):
    tx_hash = deserialize_evm_tx_hash('0x6f16132d373dbba06259d04bd1e83771343c7ac17ac0a4e74fad645ed9d809de')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    timestamp, fund_amount, deal_address = TimestampMS(1736535363000), '5887', string_to_evm_address('0xeC14eD2470FaCe0a60a41c945Cc586aFbcc3273C')  # noqa: E501
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=262,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=USDC_TOKEN,
            amount=FVal(5887),
            location_label=base_accounts[0],
            notes=f'Set USDC spending approval of {base_accounts[0]} by {FUNDING_CONDUIT} to {fund_amount}',  # noqa:E501
            address=FUNDING_CONDUIT,
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=265,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=USDC_TOKEN,
            amount=FVal(5887),
            location_label=base_accounts[0],
            counterparty=CPT_ECHO,
            notes=f'Fund {fund_amount} USDC to {deal_address} on Echo',
            address=deal_address,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x867eaD8851912894a20fCFe55AFefB33BD30fBc6']])
def test_echo_refund(base_inquirer, base_accounts):
    tx_hash = deserialize_evm_tx_hash('0xfaeea0e01cecda7849efb3f27aa216c567366e10237b717a75587ff05ad7a7c6')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    timestamp, deal_address = TimestampMS(1730227259000), string_to_evm_address('0x241F8222D1c80a4FDc25f9FC00181Eec770131A2')  # noqa: E501
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=492,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=USDC_TOKEN,
            amount=FVal(2000),
            location_label=base_accounts[0],
            counterparty=CPT_ECHO,
            notes=f'Refund 2000 USDC from {deal_address} on Echo',
            address=deal_address,
        ),
    ]
