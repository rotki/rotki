import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.zapper.constants import CPT_ZAPPER, ZAPPER_SWAP_CONTRACT
from rotkehlchen.constants.assets import A_ETH, A_USDC
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_ETHEREUM
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x3163Bb273E8D9960Ce003fD542bF26b4C529f515']])
def test_zapper_token_to_token(ethereum_inquirer, ethereum_accounts):
    """Test decoding a legacy Zapper.fi MultiExchangeSwap from USDC to PICKLE."""
    tx_hash = deserialize_evm_tx_hash('0xd270ac99b5aca2e674201d9d31aa157690d5ad3a76ae2b961f8ec42d4c5117a9')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1601497491000)),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.0219795598'),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDC,
        amount=FVal(spend_amount := '58.134106'),
        location_label=user_address,
        notes=f'Swap {spend_amount} USDC in Zapper',
        counterparty=CPT_ZAPPER,
        address=ZAPPER_SWAP_CONTRACT,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:1/erc20:0x429881672B9AE42b8EbA0E26cD9C73711b891Ca5'),
        amount=FVal(receive_amount := '2.031910083749346692'),
        location_label=user_address,
        notes=f'Receive {receive_amount} PICKLE as the result of a swap in Zapper',
        counterparty=CPT_ZAPPER,
        address=ZAPPER_SWAP_CONTRACT,
    )]
