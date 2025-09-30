from typing import TYPE_CHECKING

import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.airdrops.decoder import ENS_ADDRESS
from rotkehlchen.chain.ethereum.modules.hedgey.constants import CPT_HEDGEY, VOTING_TOKEN_LOCKUPS
from rotkehlchen.constants.assets import A_ENS, A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChecksumEvmAddress, Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_delegate_vested_tokens_with_vault_creation(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list[ChecksumEvmAddress],
):
    tx_hash = deserialize_evm_tx_hash('0x50dc56b705219f9f26e1749d4dabefbac7fae4e60925f4c57cb8a42687adf703')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas, user_address = TimestampMS(1738025567000), '0.002012111196478005', ethereum_accounts[0]  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=479,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=A_ENS,
            amount=ZERO,
            location_label=user_address,
            notes=f'Change ENS delegate for {user_address} Hedgey token lockup 290 to 0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',  # noqa: E501
            tx_hash=tx_hash,
            counterparty=CPT_HEDGEY,
            address=ENS_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_delegate_plans(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list[ChecksumEvmAddress],
):
    tx_hash = deserialize_evm_tx_hash('0xf5317d7926c5b3f269604ea983a8ed9a6240dfdbabcccd33a12dd135b9b2389a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas, user_address = TimestampMS(1738067495000), '0.000156863123427816', ethereum_accounts[0]  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=502,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=A_ENS,
            amount=ZERO,
            location_label=user_address,
            notes=f'Change ENS delegate for {user_address} Hedgey token lockup 290 from 0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12 to 0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',  # noqa: E501
            tx_hash=tx_hash,
            counterparty=CPT_HEDGEY,
            address=ENS_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x54BeCc7560a7Be76d72ED76a1f5fee6C5a2A7Ab6']])
def test_redeem_plans(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list[ChecksumEvmAddress],
):
    tx_hash = deserialize_evm_tx_hash('0xb85eb3fb6496fa51ac3d43d230ea729b52593bd2781b2b9dfab638aab7011719')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas, user_address, amount = TimestampMS(1737473963000), '0.000964573778269605', ethereum_accounts[0], '119.425418569253784576'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=386,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ENS,
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Redeem {amount} ENS from Hedgey token lockup 14',
            tx_hash=tx_hash,
            counterparty=CPT_HEDGEY,
            address=VOTING_TOKEN_LOCKUPS,
        ),
    ]
    assert events == expected_events
