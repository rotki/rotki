from typing import Any
from unittest.mock import patch

import pytest

from rotkehlchen.chain.evm.decoding.relay.constants import (
    CPT_RELAY,
    RELAY_CPT_DETAILS,
    RELAY_SOLVERS,
)
from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    Location,
    SupportedBlockchain,
    TimestampMS,
    deserialize_evm_tx_hash,
)


def test_relay_solver_configuration() -> None:
    assert RELAY_CPT_DETAILS.image == 'relay.svg'
    assert set(RELAY_SOLVERS) == {
        ChainID.ETHEREUM,
        ChainID.OPTIMISM,
        ChainID.BINANCE_SC,
        ChainID.GNOSIS,
        ChainID.POLYGON_POS,
        ChainID.HYPERLIQUID,
        ChainID.BASE,
        ChainID.ARBITRUM_ONE,
        ChainID.AVALANCHE,
        ChainID.CELO,
        ChainID.ARBITRUM_NOVA,
        ChainID.CRONOS,
        ChainID.BOBA,
        ChainID.ZKSYNC_ERA,
        ChainID.SCROLL,
        ChainID.SONIC,
        ChainID.LINEA,
        ChainID.MONAD,
        ChainID.INK,
        ChainID.MEGAETH,
    }
    assert all(
        string_to_evm_address('0xf70da97812CB96acDF810712Aa562db8dfA3dbEF') in solvers
        for solvers in RELAY_SOLVERS.values()
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_relay_bridge_receive(ethereum_inquirer: Any, ethereum_accounts: Any) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash(
            '0x9832bb339be859b2cba7166444c83f47f1485db332835e62c19e7604fa8510a9',
        )),
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=TimestampMS(1783071503000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=A_ETH,
        amount=FVal('0.034555752880651201'),
        location_label=ethereum_accounts[0],
        notes=(
            'Bridge 0.034555752880651201 ETH to '
            f'{ethereum_accounts[0]} at Ethereum via Relay'
        ),
        counterparty=CPT_RELAY,
        address=string_to_evm_address('0xA5a5491bCa93dD4C076e4906e79E7673F4A5A142'),
        extra_data={'bridge': {
            'to_chain': 1,
            'to_address': ethereum_accounts[0],
            'transfer_id': '4865275a0ce3b45d06b859019d78246f27ab851a689ba92ad9225999aa2d0753',
        }},
    )]


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
@pytest.mark.parametrize('base_accounts', [['0x4179Ec0c2137C63934Dc765BC7ECe7b70c92EE2c']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_relay_bridge_receive_on_base(base_inquirer: Any, base_accounts: Any) -> None:
    with patch(
        'rotkehlchen.chain.evm.transactions.'
        'EvmTransactions._query_and_save_internal_transactions_for_parent_hash',
        return_value=[],
    ):
        events, _ = get_decoded_events_of_transaction(
            evm_inquirer=base_inquirer,
            tx_hash=(tx_hash := deserialize_evm_tx_hash(
                '0x1c1cbf8ab0a6f4a3e4cc90ad60fb650f1e2080e86e9ff9981eab19ca3c34d73b',
            )),
        )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=TimestampMS(1785411023000),
        location=Location.BASE,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=A_ETH,
        amount=FVal('0.000678619569520312'),
        location_label=base_accounts[0],
        notes=(
            'Bridge 0.000678619569520312 ETH to '
            f'{base_accounts[0]} at Base via Relay'
        ),
        counterparty=CPT_RELAY,
        address=string_to_evm_address('0xA5a5491bCa93dD4C076e4906e79E7673F4A5A142'),
        extra_data={'bridge': {
            'to_chain': 8453,
            'to_address': base_accounts[0],
            'transfer_id': 'c4abb6054f09feff0b94bc0e9e5be972bc79a6bcec80bc0cdec75d44fb8cb685',
        }},
    )]
