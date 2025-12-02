from typing import TYPE_CHECKING

import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.summer_fi.constants import CPT_SUMMER_FI
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x7Bee86266A59fd7bAf6983bBBf78cE47Fb20a1b4']])
def test_create_account(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xaeb2f799a5a9beafb035ea664ba50ea525bf684b418467485912d3971c2a8780')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1756734407000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00324618534750664'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=371,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.CREATE,
        asset=A_ETH,
        amount=ZERO,
        location_label=user_address,
        notes='Create Summer.fi smart account 0x32C50edBF3ffEC14Fc345A399d1e52B2A9eFAAb3 with id 3757',  # noqa: E501
        counterparty=CPT_SUMMER_FI,
        address=string_to_evm_address('0xF7B75183A2829843dB06266c114297dfbFaeE2b6'),
        extra_data={'proxy_address': (proxy_address := '0x32C50edBF3ffEC14Fc345A399d1e52B2A9eFAAb3'), 'vault_id': 3757},  # noqa: E501
    )]

    # Also check that the proxy detection works correctly (relies on the tx decoded above).
    proxies = ethereum_inquirer.proxies_inquirer.get_or_query_summer_fi_proxy(
        addresses=[user_address, (other_address := make_evm_address())],
    )
    assert proxies[user_address] == {proxy_address}
    assert other_address not in proxies
