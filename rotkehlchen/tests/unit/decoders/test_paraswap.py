import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.paraswap.constants import (
    PARASWAP_AUGUSTUS_ROUTER,
    PARASWAP_TOKEN_TRANSFER_PROXY,
)
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.paraswap.constants import CPT_PARASWAP
from rotkehlchen.constants.assets import A_ENS, A_ETH, A_LINK, A_SUSHI, A_USDC, A_USDT, A_WBTC
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

A_ROUTE = Asset('eip155:1/erc20:0x16ECCfDbb4eE1A85A33f3A9B21175Cd7Ae753dB4')
A_stETH = Asset('eip155:1/erc20:0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84')
A_MPL = Asset('eip155:1/erc20:0x33349B282065b0284d756F0577FB39c158F935e6')
A_TKST = Asset('eip155:1/erc20:0x7CdBfC86A0BFa20F133748B0CF5cEa5b787b182c')
A_PRISMA = Asset('eip155:1/erc20:0xdA47862a83dac0c112BA89c6abC2159b95afd71C')
A_UDOODLE = Asset('eip155:1/erc20:0xa07dCC1aBFe20D29D87a32E2bA89876145DAfB0a')


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xf8fa0bB0798489445577fA7387dcB2125C361c28']])
def test_simple_swap_no_fee(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xeab04bca5abb6a794fd83e3c336b128824a2d3a72abf565d82a6ecd39d5929ef')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704814775000)
    swap_amount, received_amount, approval_amount, gas_fees = '3860.977240111926214656', '3997.851328', '115792089237316195423570985008687907853269984665640564034996.606767801203425279', '0.003865522700588692'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=user_address,
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=296,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_SUSHI,
        balance=Balance(amount=FVal(approval_amount)),
        location_label=user_address,
        notes=f'Set SUSHI spending approval of {user_address} by {PARASWAP_TOKEN_TRANSFER_PROXY} to {approval_amount}',  # noqa: E501
        counterparty=None,
        address=PARASWAP_TOKEN_TRANSFER_PROXY,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=297,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_SUSHI,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=user_address,
        notes=f'Swap {swap_amount} SUSHI in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=298,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDT,
        balance=Balance(amount=FVal(received_amount)),
        location_label=user_address,
        notes=f'Receive {received_amount} USDT as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x711ee578860F6f621401A6148b09F69c1F8508B2']])
def test_simple_swap_eth_fee(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xeeea20b39f157fe59fa4904fd4b62f8971188b53d05c6831e0ed67ee157e40c2')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704806231000)
    swap_amount, received_amount, gas_fees = '3.020129914302378395', '2.990432283065311187', '0.00680806307180382'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=user_address,
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_stETH,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=user_address,
        notes=f'Swap {swap_amount} stETH in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        balance=Balance(amount=FVal(received_amount)),
        location_label=user_address,
        notes=f'Receive {received_amount} ETH as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    # TODO: it should also expect a fee event here, but it's not supported yet
    # https://github.com/orgs/rotki/projects/11?pane=issue&itemId=49582891
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xd3669637F3C520d73eE922EA62D2C33F547F9Cd6']])
def test_simple_swap_token_fee(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xf4d28d1c46dde983fac73db8e651514fe7299edaf40870766462362b1b1a1d83')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704797495000)
    swap_amount, received_amount, gas_fees, paraswap_fee = '138.2851', '1190.359719', '0.0034595', '11.308417'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=user_address,
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_ROUTE,
        balance=Balance(amount=ZERO),
        location_label=user_address,
        notes=f'Revoke ROUTE spending approval of {user_address} by {PARASWAP_TOKEN_TRANSFER_PROXY}',  # noqa: E501
        counterparty=None,
        address=PARASWAP_TOKEN_TRANSFER_PROXY,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ROUTE,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=user_address,
        notes=f'Swap {swap_amount} ROUTE in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDC,
        balance=Balance(amount=FVal(received_amount)),
        location_label=user_address,
        notes=f'Receive {received_amount} USDC as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=4,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USDC,
        balance=Balance(amount=FVal(paraswap_fee)),
        location_label=user_address,
        notes=f'Spend {paraswap_fee} USDC as a paraswap fee',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xf84C3222D213e53a053A97E426738Cb12c50CBA5']])
def test_simple_buy(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x695739b3eab8dc7e6ef7f9b362983cfd4d9b81592b0840bd0ca69b0b2e8e51f9')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704888587000)
    swap_amount, received_amount, gas_fees = '223.031074350165285613', '200.000000000000000001', '0.00727228725913224'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=user_address,
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_LINK,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=user_address,
        notes=f'Swap {swap_amount} LINK in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ENS,
        balance=Balance(amount=FVal(received_amount)),
        location_label=user_address,
        notes=f'Receive {received_amount} ENS as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x33e543cB6Be7b33fF95FAF61eA8106b384E74912']])
def test_multi_swap_no_fee(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x6f7313845874cb26cda5d63adcbf9899edf257f2e196a7ace641bdbb179947e7')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704815411000)
    swap_amount, received_amount, gas_fees = '400', '30.498415074803766847', '0.007613212553923857'
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=user_address,
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=user_address,
        notes=f'Swap {swap_amount} USDT in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_MPL,
        balance=Balance(amount=FVal(received_amount)),
        location_label=user_address,
        notes=f'Receive {received_amount} MPL as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xBc067f00652Ba0B3278a3d373431769F2805Bc27']])
def test_multi_swap_token_fee(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x0c55b3df325d145b82fbe4e135e88eeae9820b035842b2ec5e17ccb1357375c6')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704883367000)
    swap_amount, received_amount, gas_fees, paraswap_fee = '24996', '48398.029944956021622964', '0.010829082710902124', '91.956256895416441083'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=user_address,
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=user_address,
        notes=f'Swap {swap_amount} USDT in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_TKST,
        balance=Balance(amount=FVal(received_amount)),
        location_label=user_address,
        notes=f'Receive {received_amount} TKST as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_TKST,
        balance=Balance(amount=FVal(paraswap_fee)),
        location_label=user_address,
        notes=f'Spend {paraswap_fee} TKST as a paraswap fee',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x4e9B2f2B72F6A5B3735cD18357F0F0EF950D1Ba7']])
def test_mega_swap_no_fee(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x5c36bcfa67d3306a3fe21203b7279e589d26c9925d055b3174ac259b262345f3')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704802211000)
    swap_amount, received_amount, gas_fees = '219410.681102', '4.68800235', '0.019375015240876558'
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=user_address,
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=12,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_USDC,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=user_address,
        notes=f'Set USDC spending approval of {user_address} by {PARASWAP_TOKEN_TRANSFER_PROXY} to {swap_amount}',  # noqa: E501
        counterparty=None,
        address=PARASWAP_TOKEN_TRANSFER_PROXY,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=13,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDC,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=user_address,
        notes=f'Swap {swap_amount} USDC in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=14,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_WBTC,
        balance=Balance(amount=FVal(received_amount)),
        location_label=user_address,
        notes=f'Receive {received_amount} WBTC as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x752921eAead738CFd1aEB8571a58480dB51e42C1']])
def test_mega_swap_token_fee(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x9c529e46976ce23d1caf3dc1c062ee3c9ec9c327014f5447761409788e842294')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704881183000)
    swap_amount, received_amount, gas_fees, paraswap_fee = '42226.901446319896728285', '40567.774843', '0.028635611789064984', '0.858994'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=user_address,
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_PRISMA,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=user_address,
        notes=f'Swap {swap_amount} PRISMA in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDC,
        balance=Balance(amount=FVal(received_amount)),
        location_label=user_address,
        notes=f'Receive {received_amount} USDC as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USDC,
        balance=Balance(amount=FVal(paraswap_fee)),
        location_label=user_address,
        notes=f'Spend {paraswap_fee} USDC as a paraswap fee',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xe952e50D1F82bBfb5054311Ca689807e343a1ab8']])
def test_swap_on_uniswap_v2_fork(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x6fa4a6a9c0d9c5aad831cc1ff149fb7683c0573db93571bc43acb5b4848314ae')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704889739000)
    swap_amount, received_amount, gas_fees = '0.35', '835.81811', '0.00296189763180853'
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=user_address,
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=user_address,
        notes=f'Swap {swap_amount} ETH in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDC,
        balance=Balance(amount=FVal(received_amount)),
        location_label=user_address,
        notes=f'Receive {received_amount} USDC as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x4AE269b8e9116f8E44797D7424E8351286FCDfab']])
def test_swap_on_uniswap_v2_fork_with_permit(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xaab04d564e1f065b350e6aa6fda9d0ff51082e8810520e691866fdade91ba9c4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704889595000)
    swap_amount, received_amount, approval_amount, gas_fees = '150', '150.152117', '115792089237316195423570985008687907853269984665640564039457584007913129.639935', '0.004565275677196416'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=user_address,
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=102,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_USDC,
        balance=Balance(amount=FVal(approval_amount)),
        location_label=user_address,
        notes=f'Set USDC spending approval of {user_address} by {PARASWAP_TOKEN_TRANSFER_PROXY} to {approval_amount}',  # noqa: E501
        counterparty=None,
        address=PARASWAP_TOKEN_TRANSFER_PROXY,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=103,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDC,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=user_address,
        notes=f'Swap {swap_amount} USDC in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=104,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDT,
        balance=Balance(amount=FVal(received_amount)),
        location_label=user_address,
        notes=f'Receive {received_amount} USDT as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xB855c4eBb5b6eB3F2033aecC4E543e27BC39465D']])
def test_direct_uniswap_v3_swap(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2b6e830d4b32c22b3c4c2a26dbdb9a17c3cc2962fc35d5b4cd5d56c58cbec68a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704888899000)
    swap_amount, received_amount, gas_fees = '2010000', '3.265498018938813939', '0.005934293486927232'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=user_address,
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_UDOODLE,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=user_address,
        notes=f'Swap {swap_amount} μDOODLE in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        balance=Balance(amount=FVal(received_amount)),
        location_label=user_address,
        notes=f'Receive {received_amount} ETH as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events
