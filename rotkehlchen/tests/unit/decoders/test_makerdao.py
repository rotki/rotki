import pytest

from rotkehlchen.chain.ethereum.modules.makerdao.constants import CPT_VAULT
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS, CPT_SDAI
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_SDAI, A_WBTC
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x648aA14e4424e0825A5cE739C8C68610e143FB79']])
def test_makerdao_simple_transaction(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x95de47059bcc084ebb8bdd60f48fbcf05619c2af84bf612fdc27a6bbf9b5097e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1593572988000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=(gas := FVal('0.00926134')),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            amount=(amount := FVal('0.6')),
            location_label=ethereum_accounts[0],
            notes=f'Withdraw {amount} ETH from ETH-A MakerDAO vault',
            counterparty=CPT_VAULT,
            address=string_to_evm_address('0x809aade1B623d8cDAeb86484d3366A03F8841FBc'),
            extra_data={'vault_type': 'ETH-A'},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xE4916bF722d5B2d397fd2F3A925029d2c4e83B51']])
def test_withdraw_with_transfer_after(ethereum_inquirer, ethereum_accounts):
    """Test withdraw/deposit with the transfer coming after the log event (happens for recent vault interactions"""  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0xb8f625820b7449ac7c83cffb4dbd33cf7c7cb64e5d69429e61df3c67c8c70d9c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1746420407000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=(gas := FVal('0.000147117137791243')),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=438,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_WBTC,
            amount=(amount := FVal('0.8')),
            location_label=ethereum_accounts[0],
            notes=f'Withdraw {amount} WBTC from WBTC-A MakerDAO vault',
            counterparty=CPT_VAULT,
            address=string_to_evm_address('0xa4aF35efa3b56d0C4F864B6484Af0C5FCD0B13e2'),
            extra_data={'vault_type': 'WBTC-A'},
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xa217BDa86b0EDb86eE7d4D6e34F493eDF1ea4F29']])
def test_withdraw_dai_from_sdai(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x6b2a1f836cfc7c28002e4ac60297daa6d79fcde892d9c3b9ca723dea2f21af5c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, sdai = ethereum_accounts[0], TimestampMS(1695854591000), A_SDAI.resolve_to_evm_token()  # noqa: E501
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.001301015216220134'),
            location_label=user_address,
            notes='Burn 0.001301015216220134 ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_SDAI,
            amount=FVal('16.020774067834506624'),
            location_label=user_address,
            notes='Return 16.020774067834506624 sDAI to sDAI contract',
            tx_hash=tx_hash,
            counterparty=CPT_SDAI,
            address=sdai.evm_address,
        ), EvmEvent(
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_DAI,
            amount=FVal('16.601085935411927527'),
            location_label=user_address,
            notes='Withdraw 16.601085935411927527 DAI from sDAI contract',
            tx_hash=tx_hash,
            counterparty=CPT_SDAI,
            address=sdai.evm_address,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xa217BDa86b0EDb86eE7d4D6e34F493eDF1ea4F29']])
def test_deposit_dai_to_sdai(ethereum_inquirer, ethereum_accounts):
    user_address = ethereum_accounts[0]
    tx_hash = deserialize_evm_tx_hash('0x27bd72a2ccd999a44c2a7aaed9090572f34045d62e153362a34715a70ca7a6a7')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, address = TimestampMS(1695089927000), A_SDAI.resolve_to_evm_token().evm_address
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(0.00152049387145495),
            location_label=user_address,
            notes='Burn 0.00152049387145495 ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_DAI,
            amount=FVal(16.58145794),
            location_label=user_address,
            notes='Deposit 16.58145794 DAI to sDAI contract',
            tx_hash=tx_hash,
            counterparty=CPT_SDAI,
            address=address,
        ), EvmEvent(
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_SDAI,
            amount=FVal('16.020774067834506624'),
            location_label=user_address,
            notes='Withdraw 16.020774067834506624 sDAI from sDAI contract',
            tx_hash=tx_hash,
            counterparty=CPT_SDAI,
            address=address,
        ),
    ]
