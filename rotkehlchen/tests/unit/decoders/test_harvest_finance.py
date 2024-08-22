import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.ethereum.modules.harvest_finance.constants import (
    CPT_HARVEST_FINANCE,
    GRAIN_TOKEN_ID,
    HARVEST_GRAIN_CLAIM,
)
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x7F248e4301F5A16B2a8289989584A509f7157845']])
def test_claim_grain(ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x5d0464be1198872d88507a3da2a876fe32c9d4427fb9ba7254c29fef0a94698c')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hex)
    timestamp, gas_str, amount_str = TimestampMS(1613015691000), '0.007051027', '1373.104541023509385198'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(FVal(gas_str)),
            location_label=ethereum_accounts[0],
            notes=f'Burned {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=223,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=EvmToken(GRAIN_TOKEN_ID),
            balance=Balance(FVal(amount_str)),
            location_label=ethereum_accounts[0],
            notes=f'Claim {amount_str} GRAIN from the harvest finance hack compensation airdrop',
            counterparty=CPT_HARVEST_FINANCE,
            address=HARVEST_GRAIN_CLAIM,
            extra_data={AIRDROP_IDENTIFIER_KEY: 'grain'},
        )]
    assert events == expected_events
