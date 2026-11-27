from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from eth_utils import to_checksum_address

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.symbiosis.constants import (
    CPT_SYMBIOSIS,
    SYMBIOSIS_CPT_DETAILS,
    SYMBIOSIS_DEPLOYMENTS,
)
from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_USDC, A_WETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import (
    LOCATION_ARBITRUM_ONE,
    LOCATION_ETHEREUM,
    LOCATION_POLYGON_POS,
)
from rotkehlchen.tasks.bridges import (
    MATCHED_BRIDGE_KEY,
    get_unmatched_bridge_events,
    match_bridge_transactions,
)
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    SupportedBlockchain,
    TimestampMS,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.db.dbhandler import DBHandler

ETH_BTC_USER = string_to_evm_address('0x5B0f3DBdD49614476e4f5fF5Db6fe13d41fCB516')
ARB_ETH_USDC_USER = string_to_evm_address('0xea9991aCEe7D9d56F591947177d1bCd23A8f894A')
ARB_ETH_NATIVE_SENDER = string_to_evm_address('0x463dD5f23f965D4B3E2bE9E1e33a2276D77d5831')
ARB_ETH_NATIVE_RECIPIENT = string_to_evm_address('0xC4FD39378f5fdBEe5473f88344c312d257e8BBA6')
LEGACY_SCHAIN_USER = string_to_evm_address('0xD43eb3e2A19a274131F73Cf5FA139cBB3cD37e06')
LEGACY_PORTAL_USER = string_to_evm_address('0xECaCd3ef02f3d9dc3c8F5048169211c2A90bd6F4')
REFUND_USER = string_to_evm_address('0xBe821f7f9c1C762A15A8073c2E4EA6CFE07A4752')
BTC_SYNTH_USER = string_to_evm_address('0x7c5d5222f60853159bbDCc058088587618D61B24')
POL_SWAP_USER = string_to_evm_address('0x5A988f1ea42C216c73A0ea0f8aD886616AFaAbaf')

ETH_SYBTC_ADDR = string_to_evm_address('0x01a8b61E7b03891a736B5DF865E0EF9C511850ad')
ETH_BOLD_ADDR = string_to_evm_address('0x6440f144b7e50D6a8439336510312d2F54beB01D')
ETH_PUFETH_ADDR = string_to_evm_address('0xD9A442856C234a39a81a089C06451EBAa4306a72')
ETH_QUAI_ADDR = string_to_evm_address('0x70b7f7044D2ca8E2F1E999B90EF16d7Cb7A0cDA1')
ARB_USDC_ADDR = string_to_evm_address('0xaf88d065e77c8cC2239327C5EDb3A432268e5831')
POL_USDC_ADDR = string_to_evm_address('0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359')
A_ETH_SYBTC = Asset(f'eip155:1/erc20:{ETH_SYBTC_ADDR}')
A_ETH_BOLD = Asset(f'eip155:1/erc20:{ETH_BOLD_ADDR}')
A_ETH_PUFETH = Asset(f'eip155:1/erc20:{ETH_PUFETH_ADDR}')
A_ETH_QUAI = Asset(f'eip155:1/erc20:{ETH_QUAI_ADDR}')
A_ARB_USDC = Asset(f'eip155:42161/erc20:{ARB_USDC_ADDR}')
A_POL_USDC = Asset(f'eip155:137/erc20:{POL_USDC_ADDR}')

ETH_PUBLIC_NODE = (
    WeightedNode(
        node_info=NodeName(
            name='eth-publicnode',
            endpoint='https://ethereum-rpc.publicnode.com',
            owned=False,
            blockchain=SupportedBlockchain.ETHEREUM,
        ),
        active=True,
        weight=ONE,
    ),
)
ARB_PUBLIC_NODE = (
    WeightedNode(
        node_info=NodeName(
            name='arbitrum-rpc',
            endpoint='https://arb1.arbitrum.io/rpc',
            owned=False,
            blockchain=SupportedBlockchain.ARBITRUM_ONE,
        ),
        active=True,
        weight=ONE,
    ),
)
POL_PUBLIC_NODE = (
    WeightedNode(
        node_info=NodeName(
            name='polygon-rpc',
            endpoint='https://polygon.drpc.org',
            owned=False,
            blockchain=SupportedBlockchain.POLYGON_POS,
        ),
        active=True,
        weight=ONE,
    ),
)


def test_symbiosis_constants_and_deployments() -> None:
    """Verify all deployment addresses are properly checksummed and icon asset exists."""
    assert SYMBIOSIS_CPT_DETAILS.identifier == CPT_SYMBIOSIS
    assert SYMBIOSIS_CPT_DETAILS.label == 'Symbiosis'
    assert SYMBIOSIS_CPT_DETAILS.image == 'symbiosis.svg'

    for chain_id, deployment in SYMBIOSIS_DEPLOYMENTS.items():
        assert deployment.portal is not None or deployment.synthesis is not None, chain_id
        for addr in (deployment.portal, deployment.synthesis, deployment.bridge):
            if addr is not None:
                assert addr == to_checksum_address(addr)

    icon_path = (
        Path(__file__).resolve().parents[4] /
        'frontend/app/public/assets/images/protocols/symbiosis.svg'
    )
    assert icon_path.is_file()


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [ETH_PUBLIC_NODE])
@pytest.mark.parametrize('ethereum_accounts', [[ETH_BTC_USER]])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_symbiosis_eth_to_btc_bridge(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Verify Ethereum USDC -> Bitcoin bridge via Symbiosis reclaims pre-bridge swap."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash(
            '0x130b06966ae330142a43f20182d9e4ce722aae6474d3db32af7a89faa63f3614',
        )),
    )
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1788983399000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.002012893141667784'),
            location_label=user_address,
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_USDC,
            amount=FVal('8700'),
            location_label=user_address,
            notes='Bridge 8700 USDC from Ethereum to Bitcoin via Symbiosis',
            counterparty=CPT_SYMBIOSIS,
            address=string_to_evm_address('0xE985e7d7b04eb55c9f20494f0c11165664407F7F'),
            extra_data={'bridge': {
                'from_chain': 1,
                'to_chain': 'btc',
                'from_address': user_address,
                'to_address': 'bc1qkkfaphz6rfrphmnhpawt9qk98tj2nvn4hy5xvz',
            }},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_manager_connect_at_start', [ARB_PUBLIC_NODE])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [ETH_PUBLIC_NODE])
@pytest.mark.parametrize('arbitrum_one_accounts', [[ARB_ETH_NATIVE_SENDER]])
@pytest.mark.parametrize('ethereum_accounts', [[ARB_ETH_NATIVE_RECIPIENT]])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_symbiosis_arbitrum_to_ethereum_native_eth_and_bridge_match(
        database: DBHandler,
        arbitrum_one_inquirer: ArbitrumOneInquirer,
        ethereum_inquirer: EthereumInquirer,
        arbitrum_one_accounts: list[ChecksumEvmAddress],
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Verify Arbitrum native ETH -> Ethereum internal ETH unwrap and cross-chain matching."""
    send_events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=(send_hash := deserialize_evm_tx_hash(
            '0xc064076a4693438cda584fa8519e6e2158e846995ef47ee5ddee8fdf47788b76',
        )),
    )
    recv_events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(recv_hash := deserialize_evm_tx_hash(
            '0xd605d835a9d374682fb549d73eaccc09eaf5463473847b691ebddde8e673f677',
        )),
    )
    sender = arbitrum_one_accounts[0]
    recipient = ethereum_accounts[0]
    transfer_id = '0b09e78c888d8e966bb35c6518fa375175e2441c5e4bffe18b22b1acc1287abe'
    assert send_events == [
        EvmEvent(
            tx_ref=send_hash,
            sequence_index=0,
            timestamp=(send_ts := TimestampMS(1795762466000)),
            location=LOCATION_ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00000600247648'),
            location_label=sender,
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_ref=send_hash,
            sequence_index=1,
            timestamp=send_ts,
            location=LOCATION_ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal('0.68045'),
            location_label=sender,
            notes='Bridge 0.68045 ETH from Arbitrum One to Ethereum via Symbiosis',
            counterparty=CPT_SYMBIOSIS,
            address=string_to_evm_address('0x3743c756b64ECd0770f1d4f47696A73d2A46dcbe'),
            extra_data={'bridge': {
                'from_chain': 42161,
                'to_chain': 1,
                'from_address': sender,
                'to_address': recipient,
                'transfer_id': transfer_id,
            }},
        ),
    ]
    assert recv_events == [
        EvmEvent(
            tx_ref=recv_hash,
            sequence_index=0,
            timestamp=TimestampMS(1795762499000),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal('0.679047143568330982'),
            location_label=recipient,
            notes='Bridge 0.679047143568330982 ETH to Ethereum via Symbiosis',
            counterparty=CPT_SYMBIOSIS,
            address=string_to_evm_address('0x5ad095DE83693ba063941f2f2C5A0dF02383B651'),
            extra_data={'bridge': {
                'to_chain': 1,
                'to_address': recipient,
                'transfer_id': transfer_id,
            }},
        ),
    ]

    match_bridge_transactions(database=database)
    assert get_unmatched_bridge_events(database=database) == ([], [])
    with database.conn.read_ctx() as cursor:
        stored = DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                type_and_subtype_combinations=[
                    (HistoryEventType.DEPOSIT, HistoryEventSubType.BRIDGE),
                    (HistoryEventType.WITHDRAWAL, HistoryEventSubType.BRIDGE),
                ],
            ),
        )
    assert len(stored) == 2
    assert all(
        event.extra_data is not None and MATCHED_BRIDGE_KEY in event.extra_data
        for event in stored
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_manager_connect_at_start', [ARB_PUBLIC_NODE])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [ETH_PUBLIC_NODE])
@pytest.mark.parametrize('arbitrum_one_accounts', [[ARB_ETH_USDC_USER]])
@pytest.mark.parametrize('ethereum_accounts', [[ARB_ETH_USDC_USER]])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_symbiosis_arbitrum_to_ethereum_usdc_swap_and_bridge_match(
        database: DBHandler,
        arbitrum_one_inquirer: ArbitrumOneInquirer,
        ethereum_inquirer: EthereumInquirer,
        arbitrum_one_accounts: list[ChecksumEvmAddress],
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Verify Arbitrum USDC -> Ethereum swapped bridge and cross-chain matching."""
    send_events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=(send_hash := deserialize_evm_tx_hash(
            '0x6254ef2d0639eeb0341ee248d341e35a27144dd3538ff44e61b1cc455fd97c7b',
        )),
    )
    recv_events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(recv_hash := deserialize_evm_tx_hash(
            '0x0912f424d7c8277c8b082fb6261fae61ea2999651cdb7b2731f9fe2c59c79ccd',
        )),
    )
    user_address = arbitrum_one_accounts[0]
    transfer_id = '923123469c51aaaef7364fd5057807f253ac188d440d55e3bdfdd33385027aba'
    assert send_events == [
        EvmEvent(
            tx_ref=send_hash,
            sequence_index=0,
            timestamp=(send_ts := TimestampMS(1795777615000)),
            location=LOCATION_ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000008390399298'),
            location_label=user_address,
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_ref=send_hash,
            sequence_index=1,
            timestamp=send_ts,
            location=LOCATION_ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ARB_USDC,
            amount=FVal('20000'),
            location_label=user_address,
            notes='Bridge 20000 USDC from Arbitrum One to Ethereum via Symbiosis',
            counterparty=CPT_SYMBIOSIS,
            address=string_to_evm_address('0x50cFe7c1938dB66A1a6D2e86D36F39FBef3d5c4a'),
            extra_data={'bridge': {
                'from_chain': 42161,
                'to_chain': 1,
                'from_address': user_address,
                'to_address': user_address,
                'transfer_id': transfer_id,
            }},
        ),
    ]
    assert recv_events == [
        EvmEvent(
            tx_ref=recv_hash,
            sequence_index=159,
            timestamp=TimestampMS(1795777655000),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH_BOLD,
            amount=FVal('19895.862034793561561744'),
            location_label=user_address,
            notes='Bridge 19895.862034793561561744 BOLD to Ethereum via Symbiosis',
            counterparty=CPT_SYMBIOSIS,
            address=string_to_evm_address('0xaddC26a3854feaBFd20d6BF658254088D83a425A'),
            extra_data={'bridge': {
                'to_chain': 1,
                'to_address': user_address,
                'transfer_id': transfer_id,
            }},
        ),
    ]

    match_bridge_transactions(database=database)
    assert get_unmatched_bridge_events(database=database) == ([], [])
    with database.conn.read_ctx() as cursor:
        stored = DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                type_and_subtype_combinations=[
                    (HistoryEventType.DEPOSIT, HistoryEventSubType.BRIDGE),
                    (HistoryEventType.WITHDRAWAL, HistoryEventSubType.BRIDGE),
                ],
            ),
        )
    assert len(stored) == 2
    assert all(
        event.extra_data is not None and MATCHED_BRIDGE_KEY in event.extra_data
        for event in stored
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [ETH_PUBLIC_NODE])
@pytest.mark.parametrize('ethereum_accounts', [[LEGACY_SCHAIN_USER]])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_symbiosis_legacy_schain_destination_resolution(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Verify legacy sChain SynthesizeRequest resolves final destination from OracleRequest."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash(
            '0x34b45d900588c1af9dc27b0759c719d3412e680638bd181cefa6c1c55af52fcf',
        )),
    )
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1729346015000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.0056446431'),
            location_label=user_address,
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=444,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH_PUFETH,
            amount=FVal('0.600119778798199297'),
            location_label=user_address,
            notes='Bridge 0.600119778798199297 pufETH from Ethereum to Arbitrum One via Symbiosis',
            counterparty=CPT_SYMBIOSIS,
            address=string_to_evm_address('0xf621Fb08BBE51aF70e7E0F4EA63496894166Ff7F'),
            extra_data={'bridge': {
                'from_chain': 1,
                'to_chain': 42161,
                'from_address': user_address,
                'to_address': user_address,
                'transfer_id': '6c56513c8567311b6b5c65a2a489c6b524e747aa1e4fd8baa962ce0675cf49b7',
            }},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [ETH_PUBLIC_NODE])
@pytest.mark.parametrize('ethereum_accounts', [[LEGACY_PORTAL_USER]])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_symbiosis_legacy_portal_burn_completed(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Verify legacy Portal BurnCompleted where event topic `to` is the Portal address."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash(
            '0x96cd7a9ab928153c4321e4b0e71f4a1f8e4a14d0d3a118f6b3213008bc6bd84a',
        )),
    )
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1702993511000),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal('0.042597223655729638'),
            location_label=user_address,
            notes='Bridge 0.042597223655729638 ETH to Ethereum via Symbiosis',
            counterparty=CPT_SYMBIOSIS,
            address=string_to_evm_address('0x5ad095DE83693ba063941f2f2C5A0dF02383B651'),
            extra_data={'bridge': {
                'to_chain': 1,
                'to_address': user_address,
                'transfer_id': 'b366ff5eaa905f91f7d234aae7b25576ddd40a4cc9d2e167ce92d9d9d97028db',
            }},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [ETH_PUBLIC_NODE])
@pytest.mark.parametrize('ethereum_accounts', [[REFUND_USER]])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_symbiosis_ethereum_revert_refund(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Verify Portal RevertSynthesizeCompleted on Ethereum decodes as WITHDRAWAL/REFUND."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash(
            '0x7254958dba63a6c2185102b451a4a9d3b502f4ec5cc6b58b5201c4159227158a',
        )),
    )
    portal_address = SYMBIOSIS_DEPLOYMENTS[ChainID.ETHEREUM].portal
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=284,
            timestamp=TimestampMS(1719121187000),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REFUND,
            asset=A_WETH,
            amount=FVal('9.9997'),
            location_label=user_address,
            notes='Receive 9.9997 WETH as refund from Symbiosis',
            counterparty=CPT_SYMBIOSIS,
            address=portal_address,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [ETH_PUBLIC_NODE])
@pytest.mark.parametrize('ethereum_accounts', [[BTC_SYNTH_USER]])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_symbiosis_ethereum_btc_synthesize(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Verify Synthesis BTCSynthesizeCompleted + SynthesizeCompleted on Ethereum."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash(
            '0xa6a0fa0f87fef7fd85e6ab438cf75bec6d5ff9eeb2fd5f2488d1d361265e2436',
        )),
    )
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1681,
            timestamp=TimestampMS(1773424571000),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH_SYBTC,
            amount=FVal('0.00016743'),
            location_label=user_address,
            notes='Bridge 0.00016743 syBTC from Bitcoin to Ethereum via Symbiosis',
            counterparty=CPT_SYMBIOSIS,
            address=string_to_evm_address('0x49d3Fc00f3ACf80FABCb42D7681667B20F60889A'),
            extra_data={'bridge': {
                'from_chain': 'btc',
                'to_chain': 1,
                'to_address': user_address,
                'transfer_id': '3f1aed81c8f2c2ee7a0a0ba482fdcb00521a84c4573098dbd0c819c170fffb42',
            }},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [ETH_PUBLIC_NODE])
@pytest.mark.parametrize('ethereum_accounts', [[BTC_SYNTH_USER]])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_symbiosis_synthesis_completed_and_burn_request(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Verify standalone Synthesis SynthesizeCompleted and BurnRequest on Ethereum."""
    synth_events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(synth_hash := deserialize_evm_tx_hash(
            '0x1c44449f24f77cdbad97130ad58588a5e0f181ade6722894ed70deb81c65c508',
        )),
    )
    burn_events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(burn_hash := deserialize_evm_tx_hash(
            '0xc0e966ddc2b9ee781ba23f31b4692850c4c8f550d2c3402e00f66119f97d62ce',
        )),
    )
    user_address = ethereum_accounts[0]
    assert synth_events == [
        EvmEvent(
            tx_ref=synth_hash,
            sequence_index=530,
            timestamp=TimestampMS(1770208643000),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH_QUAI,
            amount=FVal('7'),
            location_label=user_address,
            notes='Bridge 7 QUAI to Ethereum via Symbiosis',
            counterparty=CPT_SYMBIOSIS,
            address=ZERO_ADDRESS,
            extra_data={'bridge': {
                'to_chain': 1,
                'to_address': user_address,
                'transfer_id': '8a3f936c33a395e401ac150970a5c9fd0b9902277075e9ccf7eb58ad85e23f33',
            }},
        ),
    ]
    assert burn_events == [
        EvmEvent(
            tx_ref=burn_hash,
            sequence_index=0,
            timestamp=(burn_ts := TimestampMS(1772036531000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.0001113631581392'),
            location_label=user_address,
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_ref=burn_hash,
            sequence_index=558,
            timestamp=burn_ts,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH_QUAI,
            amount=FVal('53'),
            location_label=user_address,
            notes='Bridge 53 QUAI from Ethereum to Quai via Symbiosis',
            counterparty=CPT_SYMBIOSIS,
            address=ZERO_ADDRESS,
            extra_data={'bridge': {
                'from_chain': 1,
                'to_chain': 9,
                'from_address': user_address,
                'to_address': user_address,
                'transfer_id': 'c6dfe94b001aec6713ef6fd5da6da19722c8c1370396251827269a84627a4874',
            }},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_manager_connect_at_start', [POL_PUBLIC_NODE])
@pytest.mark.parametrize('polygon_pos_accounts', [[POL_SWAP_USER]])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_symbiosis_polygon_destination_swap(
        polygon_pos_inquirer: PolygonPOSInquirer,
        polygon_pos_accounts: list[ChecksumEvmAddress],
) -> None:
    """Verify Polygon BurnCompleted destination swap decodes as WITHDRAWAL/BRIDGE."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash(
            '0x525119bff5ca40f8cb834b9d1ebb3fc31555bd298292952c9ecde18742a5fbd8',
        )),
    )
    user_address = polygon_pos_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=69,
            timestamp=TimestampMS(1733158288000),
            location=LOCATION_POLYGON_POS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_POL_USDC,
            amount=FVal('948.98967'),
            location_label=user_address,
            notes='Bridge 948.98967 USDC to Polygon POS via Symbiosis',
            counterparty=CPT_SYMBIOSIS,
            address=string_to_evm_address('0x1111111254EEB25477B68fb85Ed929f73A960582'),
            extra_data={'bridge': {
                'to_chain': 137,
                'to_address': user_address,
                'transfer_id': '2347230cd96ec1e415842579ca971bca95e8968acf25b3fd732dacaf9ad5a3ce',
            }},
        ),
    ]
