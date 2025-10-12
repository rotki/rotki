import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.paladin.constants import (
    CPT_PALADIN,
    PALADIN_MERKLE_DISTRIBUTOR_V2,
)
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash
from rotkehlchen.utils.misc import timestamp_to_date


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xA2BF60058C0657C45FDd1741220b4A7F0DA91CA3']])
def test_claim(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x8a2bf33211bb1903ee3db7ca5a7bef10b168fdd68701cd3c9dc17c7b0c60a3f7')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas, amount, period = TimestampMS(1672197467000), '0.00120340458490378', '1079.056809836717269824', 1671062400  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=305,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:1/erc20:0xCdF7028ceAB81fA0C6971208e83fa7872994beE5'),
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Claim {amount} T from Paladin veCRV bribes for the period starting at {timestamp_to_date(period, formatstr="%d/%m/%Y %H:%M:%S")}',  # noqa: E501
            counterparty=CPT_PALADIN,
            address=PALADIN_MERKLE_DISTRIBUTOR_V2,
            product=EvmProduct.BRIBE,
        ),
    ]
    assert events == expected_events
