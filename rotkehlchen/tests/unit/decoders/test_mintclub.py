import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.base.modules.mintclub.constants import CPT_MINTCLUB
from rotkehlchen.chain.base.transactions import BaseTransactions
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import (
    EvmIndexer,
    NodeName,
    SerializableChainIndexerOrder,
    WeightedNode,
    string_to_evm_address,
)
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    Location,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', [{
    'evm_indexers_order': SerializableChainIndexerOrder(
        order={ChainID.BASE: [EvmIndexer.ROUTESCAN]},
    ),
}])
@pytest.mark.parametrize('base_manager_connect_at_start', [(
    WeightedNode(  # give some open RPC for Base to get the data from
        node_info=NodeName(
            name='base-open-rpc',
            endpoint='https://mainnet.base.org',
            owned=False,
            blockchain=SupportedBlockchain.BASE,
        ),
        active=True,
        weight=ONE,
    ),
)])
@pytest.mark.parametrize('base_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_mintclub_claim(base_inquirer, base_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0xfaa51ffecb5388ef59808d4f3f5e6e07b8a47d4a7d195c467bf77c24ee77b287')  # noqa: E501
    transactions = BaseTransactions(base_inquirer, base_inquirer.database)
    transactions.single_address_query_transactions(  # temporary hack at the time of writing get_decoded_events_of_transaction does not respect the `evm_indexers_order` so we do this here to use the given order  # noqa: E501
        address=base_accounts[0],
        start_ts=Timestamp(1761941900),
        end_ts=Timestamp(1761942100),
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        timestamp=(timestamp := TimestampMS(1761942001000)),
        sequence_index=0,
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000000466992770498')),
        location_label=(user := base_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        timestamp=timestamp,
        sequence_index=36,
        location=Location.BASE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=Asset('eip155:8453/erc20:0x18b6f6049A0af4Ed2BBe0090319174EeeF89f53a'),
        amount=(claim_amount := FVal('417.333333333333333333')),
        location_label=user,
        notes=f'Claim {claim_amount} RUNNER from MintClub distribution #4653',
        counterparty=CPT_MINTCLUB,
        address=string_to_evm_address('0x1349A9DdEe26Fe16D0D44E35B3CB9B0CA18213a4'),
    )]
