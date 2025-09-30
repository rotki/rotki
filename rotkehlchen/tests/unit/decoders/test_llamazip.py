import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.arbitrum_one.modules.llamazip.decoder import (
    ROUTER_ADDRESSES as ARBITRUM_ROUTER_ADDRESSES,
)
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.llamazip.constants import CPT_LLAMAZIP
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.modules.llamazip.decoder import (
    ROUTER_ADDRESSES as OPTIMISM_ROUTER_ADDRESSES,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xbF79b07d1311DF96CdDC53C71397271Ae8a2B0E9']])
def test_llamazip_optimism_swap_token_to_eth(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0xa6271df026c97691148b0bcd53096cdbec91394b74f93e6e86ab046852f4a115')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, fee_amount, spend_amount, receive_amount = TimestampMS(1724034205000), '0.000000114027950239', '1.653522515434244221', '0.000626208109106399'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=optimism_accounts[0],
            notes=f'Burn {fee_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:10/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1'),
            amount=FVal(spend_amount),
            location_label=optimism_accounts[0],
            notes=f'Swap {spend_amount} DAI in LlamaZip',
            counterparty=CPT_LLAMAZIP,
            address=string_to_evm_address('0x03aF20bDAaFfB4cC0A521796a223f7D85e2aAc31'),
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal(receive_amount),
            location_label=optimism_accounts[0],
            notes=f'Receive {receive_amount} ETH as the result of a swap in LlamaZip',
            counterparty=CPT_LLAMAZIP,
            address=string_to_evm_address('0x03aF20bDAaFfB4cC0A521796a223f7D85e2aAc31'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xa521E425f37aCC731651565B41Ce3E5022274F4F']])
def test_llamazip_optimism_swap_eth_to_token(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0x6caae7d1a32abecf9dcc23c89e11fecfb9fccd2b21e718c0f62c6f001eb7a626')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, fee_amount, spend_amount, receive_amount = TimestampMS(1724081427000), '0.000000754413255739', '0.005', '12.918744'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=optimism_accounts[0],
            notes=f'Burn {fee_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal(spend_amount),
            location_label=optimism_accounts[0],
            notes=f'Swap {spend_amount} ETH in LlamaZip',
            counterparty=CPT_LLAMAZIP,
            address=OPTIMISM_ROUTER_ADDRESSES[0],
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
            amount=FVal(receive_amount),
            location_label=optimism_accounts[0],
            notes=f'Receive {receive_amount} USDC.e as the result of a swap in LlamaZip',
            counterparty=CPT_LLAMAZIP,
            address=OPTIMISM_ROUTER_ADDRESSES[0],
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x1D84C9Ab259372Ab07BEE9549a6aCF28DC111001']])
def test_llamazip_optimism_swap_token_to_token(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0x92e9af072a20b74d730037b80a96bf7ab02168679624bc87de8b3427e88882fd')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, fee_amount, spend_amount, receive_amount = TimestampMS(1724074841000), '0.000000292773423793', '24.786522600837181987', '24.780601'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=optimism_accounts[0],
            notes=f'Burn {fee_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:10/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1'),
            amount=FVal(spend_amount),
            location_label=optimism_accounts[0],
            notes=f'Swap {spend_amount} DAI in LlamaZip',
            counterparty=CPT_LLAMAZIP,
            address=string_to_evm_address('0xbf16ef186e715668AA29ceF57e2fD7f9D48AdFE6'),
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
            amount=FVal(receive_amount),
            location_label=optimism_accounts[0],
            notes=f'Receive {receive_amount} USDC.e as the result of a swap in LlamaZip',
            counterparty=CPT_LLAMAZIP,
            address=string_to_evm_address('0xbf16ef186e715668AA29ceF57e2fD7f9D48AdFE6'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x635Cb8149C292Ff96F71a1a49120D04053c7eE7A']])
def test_llamazip_arbitrum_swap_token_to_eth(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0x5a3e6748dd62b943918508a7495df0dc481a054af9dc607a7b85f167a9cc54c2')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, fee_amount, spend_amount, receive_amount, a_usdce = TimestampMS(1679552792000), '0.0000306163', '36', '0.020467522941555658', Asset('eip155:42161/erc20:0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8')  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Burn {fee_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=a_usdce,
            amount=ZERO,
            location_label=arbitrum_one_accounts[0],
            notes=f'Revoke USDC.e spending approval of {arbitrum_one_accounts[0]} by {ARBITRUM_ROUTER_ADDRESSES[0]}',  # noqa: E501
            address=ARBITRUM_ROUTER_ADDRESSES[0],
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=a_usdce,
            amount=FVal(spend_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Swap {spend_amount} USDC.e in LlamaZip',
            counterparty=CPT_LLAMAZIP,
            address=string_to_evm_address('0xC31E54c7a869B9FcBEcc14363CF510d1c41fa443'),
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=4,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal(receive_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Receive {receive_amount} ETH as the result of a swap in LlamaZip',
            counterparty=CPT_LLAMAZIP,
            address=string_to_evm_address('0xC31E54c7a869B9FcBEcc14363CF510d1c41fa443'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x5Ef3D4F41791f0B9f1CEe6D739d77748f81FCa3A']])
def test_llamazip_arbitrum_swap_eth_to_token(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0xd75a0b795e0748dffdedc80b731710e9596f6af5fbc77274482cc785ed4c1cd3')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, fee_amount, spend_amount, receive_amount = TimestampMS(1679521589000), '0.0000419029', '0.125', '215.453696'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Burn {fee_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal(spend_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Swap {spend_amount} ETH in LlamaZip',
            counterparty=CPT_LLAMAZIP,
            address=ARBITRUM_ROUTER_ADDRESSES[0],
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:42161/erc20:0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9'),
            amount=FVal(receive_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Receive {receive_amount} USDT as the result of a swap in LlamaZip',
            counterparty=CPT_LLAMAZIP,
            address=ARBITRUM_ROUTER_ADDRESSES[0],
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x9fAe1b2Be0A8D7e64780fd740F8AD05188E8170A']])
def test_llamazip_arbitrum_swap_token_to_token(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0xb1f65779afe9b92edd791af3b95ea36c46d6a6e8f8cc60f4740bb11b79993a92')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, fee_amount, spend_amount, receive_amount, a_weth = TimestampMS(1679511150000), '0.0000360038', '0.071985413648931875', '0.00454144', Asset('eip155:42161/erc20:0x82aF49447D8a07e3bd95BD0d56f35241523fBab1')  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Burn {fee_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=a_weth,
            amount=ZERO,
            location_label=arbitrum_one_accounts[0],
            notes=f'Revoke WETH spending approval of {arbitrum_one_accounts[0]} by {ARBITRUM_ROUTER_ADDRESSES[0]}',  # noqa: E501
            address=ARBITRUM_ROUTER_ADDRESSES[0],
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=a_weth,
            amount=FVal(spend_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Swap {spend_amount} WETH in LlamaZip',
            counterparty=CPT_LLAMAZIP,
            address=string_to_evm_address('0x2f5e87C9312fa29aed5c179E456625D79015299c'),
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:42161/erc20:0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f'),
            amount=FVal(receive_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Receive {receive_amount} WBTC as the result of a swap in LlamaZip',
            counterparty=CPT_LLAMAZIP,
            address=string_to_evm_address('0x2f5e87C9312fa29aed5c179E456625D79015299c'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xa716c2ef62B60cF82B8119947030ea7E26A39908']])
def test_llamazip_arbitrum_swap_eth_to_arb(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0xf9d2cb0f7593181f3a296647205a184f820dcba36273a4e8486cad545ad1bf39')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, fee_amount, spend_amount, receive_amount = TimestampMS(1724091866000), '0.00000154191', '0.0001', '0.487303878224941508'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Burn {fee_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal(spend_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Swap {spend_amount} ETH in LlamaZip',
            counterparty=CPT_LLAMAZIP,
            address=ARBITRUM_ROUTER_ADDRESSES[1],
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:42161/erc20:0x912CE59144191C1204E64559FE8253a0e49E6548'),
            amount=FVal(receive_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Receive {receive_amount} ARB as the result of a swap in LlamaZip',
            counterparty=CPT_LLAMAZIP,
            address=ARBITRUM_ROUTER_ADDRESSES[1],
        ),
    ]
