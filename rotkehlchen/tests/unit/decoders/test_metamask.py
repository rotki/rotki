from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.arbitrum_one.modules.metamask.constants import (
    METAMASK_ROUTER as METAMASK_ROUTER_ARB,
)
from rotkehlchen.chain.binance_sc.modules.metamask.constants import (
    METAMASK_ROUTER as METAMASK_ROUTER_BSC,
)
from rotkehlchen.chain.ethereum.modules.metamask.constants import (
    METAMASK_ROUTER as METAMASK_ROUTER_ETH,
)
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.metamask.constants import CPT_METAMASK_SWAPS
from rotkehlchen.chain.optimism.modules.metamask.constants import (
    METAMASK_ROUTER as METAMASK_ROUTER_OPT,
)
from rotkehlchen.chain.polygon_pos.modules.metamask.constants import (
    METAMASK_ROUTER as METAMASK_ROUTER_MATIC,
)
from rotkehlchen.constants.assets import (
    A_AAVE,
    A_BSC_BNB,
    A_ETH,
    A_POLYGON_POS_MATIC,
    A_USDC,
    A_USDT,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.constants import A_OPTIMISM_USDT
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.binance_sc.node_inquirer import BinanceSCInquirer
    from rotkehlchen.types import ChecksumEvmAddress

A_LUX = Asset('eip155:1/erc20:0x88dafebb769311d7fbbeb9a21431fa026d4100d0')
A_OTACON = Asset('eip155:1/erc20:0x0F17eeCcc84739b9450C88dE0429020e2DEC05eb')
A_INU = Asset('eip155:1/erc20:0xc76d53f988820fe70e01eccb0248b312c2f1c7ca')
A_MOG = Asset('eip155:1/erc20:0xaaeE1A9723aaDB7afA2810263653A34bA2C21C7a')
A_INJ = Asset('eip155:1/erc20:0xe28b3B32B6c345A34Ff64674606124Dd5Aceca30')
A_ARBITRUM_USDC = Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831')
A_OPTIMISM_USDC = Asset('eip155:10/erc20:0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85')
A_POLYGON_USDC = Asset('eip155:137/erc20:0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174')


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x7e6Ee5d52825B3A3d9C500E7B8b0a2BAa1c91545']])
def test_metamask_swap_token_to_eth(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash(
        '0x9b675024d8648c3b590eff411fcf75a1199d10d1a3fe2ddbe50e166ce8b87cc9',
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1696160411000)
    approval_amount, swap_amount, received_amount, gas_fees, metamask_fee = '115792089237316195423570985008687907853269984665640564032906.862642668551001919', '6550.721365244578638016', '0.017595546435556104', '0.001533786820220988', '0.000153961031311116'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_LUX,
        amount=FVal(approval_amount),
        location_label=user_address,
        notes=f'Set LUX spending approval of {user_address} by {METAMASK_ROUTER_ETH} to {approval_amount}',  # noqa: E501
        address=METAMASK_ROUTER_ETH,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_LUX,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} LUX in metamask',
        counterparty=CPT_METAMASK_SWAPS,
        address=METAMASK_ROUTER_ETH,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=4,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal(received_amount),
        notes=f'Receive {received_amount} ETH as the result of a metamask swap',
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=5,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(metamask_fee),
        notes=f'Spend {metamask_fee} ETH as metamask fees',
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x4bc63637428B1cb65E646d6CF3216A4B4C84f446']])
def test_metamask_swap_eth_to_token(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash(
        '0xf1ac0081467b2f758758d2ff6afc7149b7937efa1f79904082c4c6d4a810e57b',
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1702292675000)
    swap_amount, received_amount, gas_fees, fee_amount = '0.0495625', '2595.147664794130524115', '0.004927174848537517', '0.0004375'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} ETH in metamask',
        counterparty=CPT_METAMASK_SWAPS,
        address=METAMASK_ROUTER_ETH,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_OTACON,
        amount=FVal(received_amount),
        notes=f'Receive {received_amount} OTACON as the result of a metamask swap',
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(fee_amount),
        notes=f'Spend {fee_amount} ETH as metamask fees',
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x4E2A6f9F27AC0B4bd4E1729640e06888F432030C']])
def test_metamask_swap_usdt_to_token(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash(
        '0xc31b87085cf0195c63d536bbfd2fc42194d27462cfc1cdf7a8eaa885ce6dff38',
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1702376699000)
    swap_amount, received_amount, gas_fees, fee_amount = '568.614655', '157279690809.103532500734254552', '0.007519637280969888', '5.019297'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} USDT in metamask',
        counterparty=CPT_METAMASK_SWAPS,
        address=METAMASK_ROUTER_ETH,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_INU,
        amount=FVal(received_amount),
        notes=f'Receive {received_amount} INU as the result of a metamask swap',
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USDT,
        amount=FVal(fee_amount),
        notes=f'Spend {fee_amount} USDT as metamask fees',
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xDe0A989c715C594Eadc98a1b97a9aa65d3cECb48']])
def test_metamask_swap_token_to_usdc(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash(
        '0x17e8c0e123081c77b5bb553bd3cf553d4031547f5d8884b31c8d74bb76057add',
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1702376675000)
    swap_amount, received_amount, gas_fees, fee_amount = '52000000000', '2837.148343', '0.01015815871814444', '24.824308'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_MOG,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} Mog in metamask',
        counterparty=CPT_METAMASK_SWAPS,
        address=METAMASK_ROUTER_ETH,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDC,
        amount=FVal(received_amount),
        notes=f'Receive {received_amount} USDC as the result of a metamask swap',
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USDC,
        amount=FVal(fee_amount),
        notes=f'Spend {fee_amount} USDC as metamask fees',
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x94c3951a05df16b2e744937574778fFeb10a51b2']])
def test_metamask_swap_token_to_token(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash(
        '0x5f67ce35264b7c9313cb626b133c0d99e38fcd5fd40518920aa2deb4ea67303c',
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1702399619000)
    swap_amount, received_amount, gas_fees, fee_amount, approval_amount = '89.301543595802992849', '323.028598123743886055', '0.036588478688486165', '0.788286009042397163', '90071443.400914235154609988'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=289,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_AAVE,
        amount=FVal(approval_amount),
        location_label=user_address,
        notes=f'Set AAVE spending approval of {user_address} by {METAMASK_ROUTER_ETH} to {approval_amount}',  # noqa: E501
        address=METAMASK_ROUTER_ETH,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=290,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_AAVE,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} AAVE in metamask',
        counterparty=CPT_METAMASK_SWAPS,
        address=METAMASK_ROUTER_ETH,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=291,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_INJ,
        amount=FVal(received_amount),
        notes=f'Receive {received_amount} INJ as the result of a metamask swap',
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=292,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_AAVE,
        amount=FVal(fee_amount),
        notes=f'Spend {fee_amount} AAVE as metamask fees',
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x517725Caf62Fca000C0ea950497116933f813E38']])
def test_metamask_swap_arbitrum(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash(
        '0x91733fb94bbb2de9d7fccfd87e41d5498245b74583902ddf02debe8c70a44d7e',
    )
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    user_address = arbitrum_one_accounts[0]
    timestamp = TimestampMS(1702461343000)
    swap_amount, received_amount, gas_fees, metamask_fee = '44.903625', '0.020630400240849773', '0.0003196843', '0.396375'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ARBITRUM_USDC,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} USDC in metamask',
        counterparty=CPT_METAMASK_SWAPS,
        address=METAMASK_ROUTER_ARB,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal(received_amount),
        notes=f'Receive {received_amount} ETH as the result of a metamask swap',
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ARBITRUM_USDC,
        amount=FVal(metamask_fee),
        notes=f'Spend {metamask_fee} USDC as metamask fees',
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0xc29067833665820b3505953a87F8265C9f1A517b']])
def test_metamask_swap_optimism(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash(
        '0x9c5debedbbd19fdcb1701e9905a2f0ebf31159eb8073f66de62ffda5680d1d14',
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    user_address = optimism_accounts[0]
    timestamp = TimestampMS(1702469285000)
    swap_amount, received_amount, gas_fees, fee_amount = '148.6875', '148.608467', '0.000354333259086529', '1.3125'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_OPTIMISM_USDT,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} USDT in metamask',
        counterparty=CPT_METAMASK_SWAPS,
        address=METAMASK_ROUTER_OPT,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_OPTIMISM_USDC,
        amount=FVal(received_amount),
        notes=f'Receive {received_amount} USDC as the result of a metamask swap',
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_OPTIMISM_USDT,
        amount=FVal(fee_amount),
        notes=f'Spend {fee_amount} USDT as metamask fees',
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('polygon_pos_accounts', [['0xB12897740478eeC7B86b9eBf14245cDAcBBa4F2f']])
def test_metamask_swap_polygon(polygon_pos_inquirer, polygon_pos_accounts):
    tx_hash = deserialize_evm_tx_hash(
        '0x9862e755e27b5e88f8b782c8264b0a8f55934084dd57d97753be8d540ee8ec67',
    )
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=tx_hash,
    )
    user_address = polygon_pos_accounts[0]
    timestamp = TimestampMS(1702471426000)
    approval_amount, swap_amount, received_amount, gas_fees, fee_amount = '115792089237316195423570985008687907853269984665640564039457584007913105.669754', '18.804192', '22.278327092660803452', '0.079877964587736024', '0.165989'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_POLYGON_POS_MATIC,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} POL for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=244,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_POLYGON_USDC,
        amount=FVal(approval_amount),
        location_label=user_address,
        notes=f'Set USDC spending approval of {user_address} by {METAMASK_ROUTER_MATIC} to {approval_amount}',  # noqa: E501
        address=METAMASK_ROUTER_MATIC,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=245,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_POLYGON_USDC,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} USDC in metamask',
        counterparty=CPT_METAMASK_SWAPS,
        address=METAMASK_ROUTER_MATIC,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=246,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_POLYGON_POS_MATIC,
        amount=FVal(received_amount),
        notes=f'Receive {received_amount} POL as the result of a metamask swap',
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=247,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_POLYGON_USDC,
        amount=FVal(fee_amount),
        notes=f'Spend {fee_amount} USDC as metamask fees',
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('binance_sc_accounts', [['0x113A6424CF48C467EDF367973B8Dfb4A18a0623A']])
def test_metamask_swap_binance_sc(
        binance_sc_inquirer: 'BinanceSCInquirer',
        binance_sc_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0xa08ff8cf928f0d1c5731b8320bf9055c2adf11dc9e8343ce6e5ff6c570330e14')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=binance_sc_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp = binance_sc_accounts[0], TimestampMS(1736517910000)
    gas_amount, swap_amount, received_amount, fee_amount, approve_amount = '0.000596574', '10', '0.014389342482790536', '0.000125906746724417', '115792089237316195423570985008687907853269984665640564039447.584007913129639935'  # noqa: E501
    a_bsc_usd = Asset('eip155:56/erc20:0x55d398326f99059fF775485246999027B3197955')
    assert events == [EvmEvent(
        tx_hash=tx_hash,
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
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=71,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=a_bsc_usd,
        amount=FVal(approve_amount),
        location_label=user_address,
        notes=f'Set BSC-USD spending approval of {user_address} by {METAMASK_ROUTER_BSC} to {approve_amount}',  # noqa: E501
        address=METAMASK_ROUTER_BSC,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=72,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.SPEND,
        asset=a_bsc_usd,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} BSC-USD in metamask',
        counterparty=CPT_METAMASK_SWAPS,
        address=METAMASK_ROUTER_BSC,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=73,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BSC_BNB,
        amount=FVal(received_amount),
        notes=f'Receive {received_amount} BNB as the result of a metamask swap',
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=74,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BSC_BNB,
        amount=FVal(fee_amount),
        notes=f'Spend {fee_amount} BNB as metamask fees',
    )]
