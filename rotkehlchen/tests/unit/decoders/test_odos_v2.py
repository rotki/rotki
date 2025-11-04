from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.arbitrum_one.modules.odos.v2.constants import ODOS_V2_ROUTER as ARB_ROUTER
from rotkehlchen.chain.base.modules.odos.v2.constants import (
    ODOS_AIRDROP_DISTRIBUTOR,
    ODOS_ASSET_ID,
    ODOS_V2_ROUTER as BASE_ROUTER,
)
from rotkehlchen.chain.base.node_inquirer import BaseInquirer
from rotkehlchen.chain.binance_sc.modules.odos.v2.constants import ODOS_V2_ROUTER as BSC_ROUTER
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.ethereum.modules.odos.v2.constants import ODOS_V2_ROUTER as ETH_ROUTER
from rotkehlchen.chain.evm.decoding.odos.v2.constants import CPT_ODOS_V2
from rotkehlchen.chain.optimism.modules.odos.v2.constants import ODOS_V2_ROUTER as OP_ROUTER
from rotkehlchen.chain.polygon_pos.modules.odos.v2.constants import ODOS_V2_ROUTER as MATIC_ROUTER
from rotkehlchen.chain.scroll.modules.odos.v2.constants import ODOS_V2_ROUTER as SCROLL_ROUTER
from rotkehlchen.constants.assets import (
    A_ARB,
    A_BSC_BNB,
    A_ETH,
    A_POL,
    A_USDC,
    A_WETH,
)
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.unit.decoders.test_aerodrome import A_AERO
from rotkehlchen.tests.unit.decoders.test_metamask import A_OPTIMISM_USDC
from rotkehlchen.tests.unit.decoders.test_zerox import A_ARBITRUM_USDC
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChecksumEvmAddress, Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.binance_sc.node_inquirer import BinanceSCInquirer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd1AcFE3854229682ff38fc6bbdFa81211020DaB8']])
def test_swap_token_to_token(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x0efcdf00cf582b5befb367e4527bcde302c3bb078aa7683c51b3a14df5ae2e1e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, swap_amount, received_amount, gas_fees = TimestampMS(1721202275000), '6421.31', '7037.875022', '0.00129060601'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:1/erc20:0x1aBaEA1f7C830bD89Acc67eC4af516284b1bC33c'),
        amount=FVal(swap_amount),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} EURC in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ETH_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDC,
        amount=FVal(received_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} USDC as the result of a swap in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ETH_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x3097eCF8195aBc13dA5a56a16D686Fc3166EB056']])
def test_swap_token_to_eth(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xf2e7b37c24428631dad93b436019aa1602dbc4315f06a231a87b75b33f2f3491')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, swap_amount, received_amount, gas_fees = TimestampMS(1721210603000), '0.252163033513435945', '0.252169099350692012', '0.00211742541059688'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:1/erc20:0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'),
        amount=FVal(swap_amount),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} stETH in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ETH_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal(received_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} ETH as the result of a swap in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ETH_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd68f1ee4e3f7c54295F296B9a579664767784a2c']])
def test_swap_eth_to_token(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x3bd3fa946e7da66914bd0c90deccea9ed41fd19e6f7b34e23e7a971eaffa48d8')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, swap_amount, gas_fees = TimestampMS(1721215703000), '0.48', '0.000956250976660625'
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal(swap_amount),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} ETH in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ETH_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_WETH,
        amount=FVal(swap_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {swap_amount} WETH as the result of a swap in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ETH_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xB3dB8a7fB7f35CD64A46d5F06992DF99F815e67d']])
def test_swap_multi_to_single(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xedc73ef9cec8f60630a509d87038e8826f6ca334443ffc025e03d212ffa9e267')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, swap_amount_barron, swap_amount_sapo, received_amount, odos_fees, gas_fees = TimestampMS(1721212283000), '21952.133805449', '25347.248642364588152989', '0.008056869560090457', '0.000000805767532763', '0.001959751810319688'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=223,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:1/erc20:0x1F70300BCe8c2302780BD0a153ebb75B8CA7efCb'),
        amount=ZERO,
        location_label=ethereum_accounts[0],
        notes=f'Revoke BARRON spending approval of {ethereum_accounts[0]} by {ETH_ROUTER}',
        address=ETH_ROUTER,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=224,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:1/erc20:0xb48EF10254C688ca0077f45C84459DC466bC83F6'),
        amount=ZERO,
        location_label=ethereum_accounts[0],
        notes=f'Revoke SAPO spending approval of {ethereum_accounts[0]} by {ETH_ROUTER}',
        address=ETH_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=225,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MULTI_TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:1/erc20:0x1F70300BCe8c2302780BD0a153ebb75B8CA7efCb'),
        amount=FVal(swap_amount_barron),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount_barron} BARRON in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ETH_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=226,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MULTI_TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:1/erc20:0xb48EF10254C688ca0077f45C84459DC466bC83F6'),
        amount=FVal(swap_amount_sapo),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount_sapo} SAPO in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ETH_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=227,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MULTI_TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal(received_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} ETH as the result of a swap in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ETH_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=228,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MULTI_TRADE,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(odos_fees),
        location_label=ethereum_accounts[0],
        notes=f'Spend {odos_fees} ETH as an Odos v2 fee',
        counterparty=CPT_ODOS_V2,
        address=ETH_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x62975846Ad2401b4dD9d65D7aE5BD40B4239CB23']])
def test_swap_single_to_multi(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xa331b8a62ccf8a62960a6a4edda43f3b835c0a76b5c6365691936077787a5507')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, swap_amount, received_amount_sfrax, received_amount_rgusd, odos_fees_sfrax, odos_fees_rgusd, gas_fees = TimestampMS(1721103275000), '0.01', '16.393269664059458706', '17.599136295574420014', '0.001639490915497496', '0.001760089638521295', '0.00234938705101066'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MULTI_TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal(swap_amount),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} ETH in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ETH_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MULTI_TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:1/erc20:0xA663B02CF0a4b149d2aD41910CB81e23e1c41c32'),
        amount=FVal(received_amount_sfrax),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount_sfrax} sFRAX as the result of a swap in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ETH_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MULTI_TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:1/erc20:0x78da5799CF427Fee11e9996982F4150eCe7a99A7'),
        amount=FVal(received_amount_rgusd),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount_rgusd} rgUSD as the result of a swap in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ETH_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=4,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MULTI_TRADE,
        event_subtype=HistoryEventSubType.FEE,
        asset=Asset('eip155:1/erc20:0xA663B02CF0a4b149d2aD41910CB81e23e1c41c32'),
        amount=FVal(odos_fees_sfrax),
        location_label=ethereum_accounts[0],
        notes=f'Spend {odos_fees_sfrax} sFRAX as an Odos v2 fee',
        counterparty=CPT_ODOS_V2,
        address=ETH_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=5,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MULTI_TRADE,
        event_subtype=HistoryEventSubType.FEE,
        asset=Asset('eip155:1/erc20:0x78da5799CF427Fee11e9996982F4150eCe7a99A7'),
        amount=FVal(odos_fees_rgusd),
        location_label=ethereum_accounts[0],
        notes=f'Spend {odos_fees_rgusd} rgUSD as an Odos v2 fee',
        counterparty=CPT_ODOS_V2,
        address=ETH_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd0392C8cE1b658f1f3D5dFcbacA159F90625E87F']])
def test_swap_multi_to_multi(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2ae9298c00c76fc63df4112a7924a5deb908f095cb9d41d284e890aee31ca114')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, swap_amount_sweth, swap_amount_usdc, received_amount_eth, received_amount_cbeth, odos_fees_eth, odos_fees_cbeth, gas_fees = TimestampMS(1720651511000), '0.300942750197910709', '5.085873', '0.21177820231350276', '0.101348638838421792', '0.000021179938225173', '0.000010135877471590', '0.00194866414'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=247,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:1/erc20:0xf951E335afb289353dc249e82926178EaC7DEd78'),
        amount=ZERO,
        location_label=ethereum_accounts[0],
        notes=f'Revoke swETH spending approval of {ethereum_accounts[0]} by {ETH_ROUTER}',
        address=ETH_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=248,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MULTI_TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:1/erc20:0xf951E335afb289353dc249e82926178EaC7DEd78'),
        amount=FVal(swap_amount_sweth),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount_sweth} swETH in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ETH_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=249,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MULTI_TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDC,
        amount=FVal(swap_amount_usdc),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount_usdc} USDC in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ETH_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=250,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MULTI_TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal(received_amount_eth),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount_eth} ETH as the result of a swap in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ETH_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=251,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MULTI_TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:1/erc20:0xBe9895146f7AF43049ca1c1AE358B0541Ea49704'),
        amount=FVal(received_amount_cbeth),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount_cbeth} cbETH as the result of a swap in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ETH_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=252,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MULTI_TRADE,
        event_subtype=HistoryEventSubType.FEE,
        asset=Asset('eip155:1/erc20:0xBe9895146f7AF43049ca1c1AE358B0541Ea49704'),
        amount=FVal(odos_fees_cbeth),
        location_label=ethereum_accounts[0],
        notes=f'Spend {odos_fees_cbeth} cbETH as an Odos v2 fee',
        counterparty=CPT_ODOS_V2,
        address=ETH_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=253,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MULTI_TRADE,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(odos_fees_eth),
        location_label=ethereum_accounts[0],
        notes=f'Spend {odos_fees_eth} ETH as an Odos v2 fee',
        counterparty=CPT_ODOS_V2,
        address=ETH_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x437AD8a22CeeD33cBC4e661f8ef33D57a390d287']])
def test_swap_on_arbitrum_one(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0xab0ca6d2749425e0e45a60dc66daa5059276bf2b97db5939949e24564dff9826')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, swap_amount, received_amount, gas_fees = TimestampMS(1721303364000), '5', '3.797619', '0.000006397028928'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=arbitrum_one_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_ARB,
        amount=ZERO,
        location_label=arbitrum_one_accounts[0],
        notes=f'Revoke ARB spending approval of {arbitrum_one_accounts[0]} by {ARB_ROUTER}',
        address=ARB_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ARB,
        amount=FVal(swap_amount),
        location_label=arbitrum_one_accounts[0],
        notes=f'Swap {swap_amount} ARB in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ARB_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ARBITRUM_USDC,
        amount=FVal(received_amount),
        location_label=arbitrum_one_accounts[0],
        notes=f'Receive {received_amount} USDC as the result of a swap in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ARB_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x19B43787fbC106d427Be3ca3307d4Fb0A73D83Dc']])
def test_swap_on_base(base_inquirer, base_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2029ab1ad9985a21c8a064be8384b531d55864f37f16a1716a00da8577891aab')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    timestamp, approval_amount, swap_amount, received_amount, gas_fees = TimestampMS(1721303613000), '9007199254724259.054195778508578652', '10.586121519928495085', '0.003163240870272189', '0.00000767513097358'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=base_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_AERO,
        amount=FVal(approval_amount),
        location_label=base_accounts[0],
        notes=f'Set AERO spending approval of {base_accounts[0]} by {BASE_ROUTER} to {approval_amount}',  # noqa: E501
        address=BASE_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.BASE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_AERO,
        amount=FVal(swap_amount),
        location_label=base_accounts[0],
        notes=f'Swap {swap_amount} AERO in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=BASE_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=4,
        timestamp=timestamp,
        location=Location.BASE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal(received_amount),
        location_label=base_accounts[0],
        notes=f'Receive {received_amount} ETH as the result of a swap in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=BASE_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x1a8C829cA8F9525AB2bc812460BE4Ba8f32B586E']])
def test_swap_on_optimism(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0xc7c9b85ba66e6d262a5bf23afd75a49ffb6c079979587d5bbc1dddd647afc906')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, approval_amount, swap_amount_usdc, swap_amount_usdce, received_amount, odos_fees, gas_fees = TimestampMS(1721310953000), '115792089237316195423570985008687907853269984665640564039457584007913129.447868', '1.199279', '0.192067', '0.000401886614321588', '0.000000040192680701', '0.000015691756359161'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=optimism_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=87,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
        amount=FVal(approval_amount),
        location_label=optimism_accounts[0],
        notes=f'Set USDC.e spending approval of {optimism_accounts[0]} by {OP_ROUTER} to {approval_amount}',  # noqa: E501
        address=OP_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=88,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.MULTI_TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_OPTIMISM_USDC,
        amount=FVal(swap_amount_usdc),
        location_label=optimism_accounts[0],
        notes=f'Swap {swap_amount_usdc} USDC in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=OP_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=89,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.MULTI_TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
        amount=FVal(swap_amount_usdce),
        location_label=optimism_accounts[0],
        notes=f'Swap {swap_amount_usdce} USDC.e in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=OP_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=90,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.MULTI_TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal(received_amount),
        location_label=optimism_accounts[0],
        notes=f'Receive {received_amount} ETH as the result of a swap in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=OP_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=91,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.MULTI_TRADE,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(odos_fees),
        location_label=optimism_accounts[0],
        notes=f'Spend {odos_fees} ETH as an Odos v2 fee',
        counterparty=CPT_ODOS_V2,
        address=OP_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0xB14cF335808931BDED4B232c6d01C65e5E73237F']])
def test_swap_on_polygon(polygon_pos_inquirer, polygon_pos_accounts):
    tx_hash = deserialize_evm_tx_hash('0x82bd45bcf1faf80f4b2e0d12b3e45c5801d1065a7e6a7daf68cd35a3a33c5fc7')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, approval_amount, swap_amount, received_amount, gas_fees = TimestampMS(1721305107000), '0.0000001', '0.0000019', '0.217325398483406396', '0.006751666697583186'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_POL,
        amount=FVal(gas_fees),
        location_label=polygon_pos_accounts[0],
        notes=f'Burn {gas_fees} POL for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:137/erc20:0x2297aEbD383787A160DD0d9F71508148769342E3'),
        amount=FVal(approval_amount),
        location_label=polygon_pos_accounts[0],
        notes=f'Set BTC.b spending approval of {polygon_pos_accounts[0]} by {MATIC_ROUTER} to {approval_amount}',  # noqa: E501
        address=MATIC_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:137/erc20:0x2297aEbD383787A160DD0d9F71508148769342E3'),
        amount=FVal(swap_amount),
        location_label=polygon_pos_accounts[0],
        notes=f'Swap {swap_amount} BTC.b in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=MATIC_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=4,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_POL,
        amount=FVal(received_amount),
        location_label=polygon_pos_accounts[0],
        notes=f'Receive {received_amount} POL as the result of a swap in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=MATIC_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('scroll_accounts', [['0x0a32d140700edb28165C88D1000A910c247dFDCA']])
def test_swap_on_scroll(scroll_inquirer, scroll_accounts):
    tx_hash = deserialize_evm_tx_hash('0x442e968d8a5c6adb81bf087041ed3dd19dc2f20725044c7f9c435bf6234d9992')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=scroll_inquirer, tx_hash=tx_hash)
    timestamp, swap_amount, received_amount, gas_fees = TimestampMS(1721305362000), '0.042810448486080933', '0.049288894534015152', '0.000033784756880726'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.SCROLL,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=scroll_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.SCROLL,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:534352/erc20:0xf610A9dfB7C89644979b4A0f27063E9e7d7Cda32'),
        amount=FVal(swap_amount),
        location_label=scroll_accounts[0],
        notes=f'Swap {swap_amount} wstETH in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=SCROLL_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.SCROLL,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:534352/erc20:0xa25b25548B4C98B0c7d3d27dcA5D5ca743d68b7F'),
        amount=FVal(received_amount),
        location_label=scroll_accounts[0],
        notes=f'Receive {received_amount} wrsETH as the result of a swap in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=SCROLL_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('binance_sc_accounts', [['0x4d29a5fdB0787690bd1c68e0107753c3ad1cF67B']])
def test_swap_on_binance_sc(
        binance_sc_inquirer: 'BinanceSCInquirer',
        binance_sc_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x21d24bd239db461b7fe53aef5b82d0d3b7c3a62241a3a3fd3a2ba9434bf4a53d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=binance_sc_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, gas_amount, swap_amount, receive_amount, fee_amount = binance_sc_accounts[0], TimestampMS(1736524750000), '0.000168374', '0.003', '2.07239458068046454', '0.001247178283258054'  # noqa: E501
    a_bsc_usdc = Asset('eip155:56/erc20:0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d')
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BSC_BNB,
        amount=FVal(gas_amount),
        location_label=user_address,
        notes=f'Burn {gas_amount} BNB for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_BSC_BNB,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} BNB in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=BSC_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=a_bsc_usdc,
        amount=FVal(receive_amount),
        location_label=user_address,
        notes=f'Receive {receive_amount} USDC as the result of a swap in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=BSC_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.FEE,
        asset=a_bsc_usdc,
        amount=FVal(fee_amount),
        location_label=user_address,
        notes=f'Spend {fee_amount} USDC as an Odos v2 fee',
        counterparty=CPT_ODOS_V2,
        address=BSC_ROUTER,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_airdrop_claim(
        base_inquirer: BaseInquirer,
        base_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x7d78887e1f615d83e95d2fd2cddd72b1042131d8b194bceb9630580ea596a14c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    timestamp, received_amount, gas_fees = TimestampMS(1734686937000), '1739.7281675210563', '0.000025147925631755'  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=base_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=351,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.AIRDROP,
        asset=Asset(ODOS_ASSET_ID),
        amount=FVal(received_amount),
        location_label=base_accounts[0],
        notes=f'Claim {received_amount} ODOS from Odos airdrop',
        address=ODOS_AIRDROP_DISTRIBUTOR,
        counterparty=CPT_ODOS_V2,
        extra_data={AIRDROP_IDENTIFIER_KEY: 'odos'},
    )]
