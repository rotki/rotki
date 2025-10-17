import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.makerdao.constants import CPT_VAULT
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_WBTC
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
