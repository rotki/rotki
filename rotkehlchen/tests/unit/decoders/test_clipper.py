import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.clipper.constants import CPT_CLIPPER
from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, SupportedBlockchain, TimestampMS, deserialize_evm_tx_hash

CLIPPER_POOL_ETH = string_to_evm_address('0x655eDCE464CC797526600a462A8154650EEe4B77')
CLIPPER_POOL_BASE = string_to_evm_address('0xb32D856cAd3D2EF07C94867A800035E37241247C')


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9dBd35AdF013e26DfDa9741c09c1790Cf8a25Dd1']])
def test_swap_token_to_token_ethereum(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x6b6c3f0810b234a9be3f012e072b3ce2857040cc5266e0429b2d5b4c136be64c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, out_amount, in_amount = ethereum_accounts[0], TimestampMS(1767528011000), '0.000004294030803529', '6.96', '6.957538'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F'),
            amount=FVal(out_amount),
            location_label=user_address,
            notes=f'Swap {out_amount} DAI in Clipper',
            counterparty=CPT_CLIPPER,
            address=CLIPPER_POOL_ETH,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            amount=FVal(in_amount),
            location_label=user_address,
            notes=f'Receive {in_amount} USDC as the result of a swap in Clipper',
            counterparty=CPT_CLIPPER,
            address=CLIPPER_POOL_ETH,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xc2863f32E61d3d95688f0c61322d8A803639E1e1']])
def test_swap_token_to_eth_ethereum(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xaf966689919ab2aebe9bb333150f4e2e16b1c0addf292108460b794eeffc7dca')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, out_amount, in_amount = ethereum_accounts[0], TimestampMS(1768400735000), '0.000236314177734726', '1.5', '0.00045127273560297'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7'),
            amount=FVal(out_amount),
            location_label=user_address,
            notes=f'Swap {out_amount} USDT in Clipper',
            counterparty=CPT_CLIPPER,
            address=CLIPPER_POOL_ETH,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal(in_amount),
            location_label=user_address,
            notes=f'Receive {in_amount} ETH as the result of a swap in Clipper',
            counterparty=CPT_CLIPPER,
            address=CLIPPER_POOL_ETH,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_manager_connect_at_start', [(
    WeightedNode(
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
@pytest.mark.parametrize('base_accounts', [['0xd26a5e62808E501a55ffd91f662387a646E1Beb0']])
def test_swap_eth_to_token_base(base_inquirer, base_accounts, allow_base_routescan, monkeypatch):
    monkeypatch.setattr(
        'rotkehlchen.chain.evm.transactions.EvmTransactions._query_and_save_internal_transactions_for_parent_hash',
        lambda *args, **kwargs: [],
    )
    tx_hash = deserialize_evm_tx_hash('0x6a0359515efbce1047222ad3525c773755596a8635c80ee578ff25c160f88502')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, out_amount, in_amount = base_accounts[0], TimestampMS(1767667255000), '0.000000723596186919', '0.05', '160.40021'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal(out_amount),
            location_label=user_address,
            notes=f'Swap {out_amount} ETH in Clipper',
            counterparty=CPT_CLIPPER,
            address=CLIPPER_POOL_BASE,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),
            amount=FVal(in_amount),
            location_label=user_address,
            notes=f'Receive {in_amount} USDC as the result of a swap in Clipper',
            counterparty=CPT_CLIPPER,
            address=CLIPPER_POOL_BASE,
        ),
    ]
