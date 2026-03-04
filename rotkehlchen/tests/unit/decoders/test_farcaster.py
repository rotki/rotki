from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.base.modules.farcaster.constants import CPT_FARCASTER
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, SupportedBlockchain, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_manager_connect_at_start', [(
    WeightedNode(
        node_info=NodeName(
            name='base mainnet',
            endpoint='https://mainnet.base.org',
            owned=False,
            blockchain=SupportedBlockchain.BASE,
        ),
        active=True,
        weight=ONE,
    ),
)])
@pytest.mark.parametrize('base_accounts', [['0x602CB34cE1B1d3133219D8a79c773fe9FAe3656e']])
def test_farcaster_pro_purchase(base_inquirer, base_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash(
        '0xaf0d0052eec2231428c5fbf81523c2ef833a8f02ae080a047c1abce3e2b12e83',
    )
    query_internal_txs = (
        'rotkehlchen.chain.evm.transactions.'
        'EvmTransactions._query_and_save_internal_transactions_for_parent_hash'
    )
    with patch(  # ignore internal transactions since not needed and atm no base indexer gives them
        query_internal_txs,
        return_value=[],
    ):
        events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)

    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1761944761000),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000000197978205154'),
            location_label=(user_address := base_accounts[0]),
            notes='Burn 0.000000197978205154 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=219,
            timestamp=TimestampMS(1761944761000),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYMENT,
            asset=Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),
            amount=FVal('119.999955'),
            location_label=user_address,
            notes='Pay 119.999955 USDC for Farcaster Pro tier 1 for 365 days',
            counterparty=CPT_FARCASTER,
            address=string_to_evm_address('0x0BDcA19c9801bb484285362fD5dd0c94592c874C'),
        ),
    ]
