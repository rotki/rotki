import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.odos.v2.constants import ODOS_V2_ROUTER
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.odos.v2.constants import CPT_ODOS_V2
from rotkehlchen.constants.assets import A_ETH, A_USDC, A_WETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd1AcFE3854229682ff38fc6bbdFa81211020DaB8']])
def test_swap_token_to_token(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x0efcdf00cf582b5befb367e4527bcde302c3bb078aa7683c51b3a14df5ae2e1e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp, swap_amount, received_amount, gas_fees = TimestampMS(1721202275000), '6421.31', '7037.875022', '0.00129060601'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=ethereum_accounts[0],
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:1/erc20:0x1aBaEA1f7C830bD89Acc67eC4af516284b1bC33c'),
        balance=Balance(amount=FVal(swap_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} EUROC in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ODOS_V2_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDC,
        balance=Balance(amount=FVal(received_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} USDC as the result of a swap in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ODOS_V2_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x3097eCF8195aBc13dA5a56a16D686Fc3166EB056']])
def test_swap_token_to_eth(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xf2e7b37c24428631dad93b436019aa1602dbc4315f06a231a87b75b33f2f3491')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp, swap_amount, received_amount, gas_fees = TimestampMS(1721210603000), '0.252163033513435945', '0.252169099350692012', '0.00211742541059688'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=ethereum_accounts[0],
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:1/erc20:0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'),
        balance=Balance(amount=FVal(swap_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} stETH in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ODOS_V2_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        balance=Balance(amount=FVal(received_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} ETH as the result of a swap in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ODOS_V2_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd68f1ee4e3f7c54295F296B9a579664767784a2c']])
def test_swap_eth_to_token(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x3bd3fa946e7da66914bd0c90deccea9ed41fd19e6f7b34e23e7a971eaffa48d8')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp, swap_amount, gas_fees = TimestampMS(1721215703000), '0.48', '0.000956250976660625'
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=ethereum_accounts[0],
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
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} ETH in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ODOS_V2_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_WETH,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Receive {swap_amount} WETH as the result of a swap in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ODOS_V2_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xB3dB8a7fB7f35CD64A46d5F06992DF99F815e67d']])
def test_swap_multi_to_single(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xedc73ef9cec8f60630a509d87038e8826f6ca334443ffc025e03d212ffa9e267')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp, swap_amount_barron, swap_amount_sapo, received_amount, odos_fees, gas_fees = TimestampMS(1721212283000), '21952.133805449', '25347.248642364588152989', '0.008056869560090457', '0.000000805767532763', '0.001959751810319688'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=ethereum_accounts[0],
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=223,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:1/erc20:0x1F70300BCe8c2302780BD0a153ebb75B8CA7efCb'),
        balance=Balance(),
        location_label=ethereum_accounts[0],
        notes=f'Revoke BARRON spending approval of {ethereum_accounts[0]} by {ODOS_V2_ROUTER}',
        address=ODOS_V2_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=224,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:1/erc20:0xb48EF10254C688ca0077f45C84459DC466bC83F6'),
        balance=Balance(),
        location_label=ethereum_accounts[0],
        notes=f'Revoke SAPO spending approval of {ethereum_accounts[0]} by {ODOS_V2_ROUTER}',
        address=ODOS_V2_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=225,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:1/erc20:0x1F70300BCe8c2302780BD0a153ebb75B8CA7efCb'),
        balance=Balance(amount=FVal(swap_amount_barron)),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount_barron} BARRON in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ODOS_V2_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=226,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:1/erc20:0xb48EF10254C688ca0077f45C84459DC466bC83F6'),
        balance=Balance(amount=FVal(swap_amount_sapo)),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount_sapo} SAPO in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ODOS_V2_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=227,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        balance=Balance(amount=FVal(received_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} ETH as the result of a swap in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ODOS_V2_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=228,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(odos_fees)),
        location_label=ethereum_accounts[0],
        notes=f'Spend {odos_fees} ETH as an Odos v2 fee',
        counterparty=CPT_ODOS_V2,
        address=ODOS_V2_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x62975846Ad2401b4dD9d65D7aE5BD40B4239CB23']])
def test_swap_single_to_multi(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xa331b8a62ccf8a62960a6a4edda43f3b835c0a76b5c6365691936077787a5507')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp, swap_amount, received_amount_sfrax, received_amount_rgusd, odos_fees_sfrax, odos_fees_rgusd, gas_fees = TimestampMS(1721103275000), '0.01', '16.393269664059458706', '17.599136295574420014', '0.001639490915497496', '0.001760089638521295', '0.00234938705101066'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=ethereum_accounts[0],
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
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} ETH in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ODOS_V2_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:1/erc20:0xA663B02CF0a4b149d2aD41910CB81e23e1c41c32'),
        balance=Balance(amount=FVal(received_amount_sfrax)),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount_sfrax} sFRAX as the result of a swap in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ODOS_V2_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:1/erc20:0x78da5799CF427Fee11e9996982F4150eCe7a99A7'),
        balance=Balance(amount=FVal(received_amount_rgusd)),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount_rgusd} rgUSD as the result of a swap in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ODOS_V2_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=4,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=Asset('eip155:1/erc20:0xA663B02CF0a4b149d2aD41910CB81e23e1c41c32'),
        balance=Balance(amount=FVal(odos_fees_sfrax)),
        location_label=ethereum_accounts[0],
        notes=f'Spend {odos_fees_sfrax} sFRAX as an Odos v2 fee',
        counterparty=CPT_ODOS_V2,
        address=ODOS_V2_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=5,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=Asset('eip155:1/erc20:0x78da5799CF427Fee11e9996982F4150eCe7a99A7'),
        balance=Balance(amount=FVal(odos_fees_rgusd)),
        location_label=ethereum_accounts[0],
        notes=f'Spend {odos_fees_rgusd} rgUSD as an Odos v2 fee',
        counterparty=CPT_ODOS_V2,
        address=ODOS_V2_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd0392C8cE1b658f1f3D5dFcbacA159F90625E87F']])
def test_swap_multi_to_multi(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2ae9298c00c76fc63df4112a7924a5deb908f095cb9d41d284e890aee31ca114')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp, swap_amount_sweth, swap_amount_usdc, received_amount_eth, received_amount_cbeth, odos_fees_eth, odos_fees_cbeth, gas_fees = TimestampMS(1720651511000), '0.300942750197910709', '5.085873', '0.21177820231350276', '0.101348638838421792', '0.000021179938225173', '0.000010135877471590', '0.00194866414'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=ethereum_accounts[0],
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=247,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:1/erc20:0xf951E335afb289353dc249e82926178EaC7DEd78'),
        balance=Balance(amount=FVal(0)),
        location_label=ethereum_accounts[0],
        notes=f'Revoke swETH spending approval of {ethereum_accounts[0]} by {ODOS_V2_ROUTER}',
        address=ODOS_V2_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=248,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:1/erc20:0xf951E335afb289353dc249e82926178EaC7DEd78'),
        balance=Balance(amount=FVal(swap_amount_sweth)),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount_sweth} swETH in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ODOS_V2_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=249,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDC,
        balance=Balance(amount=FVal(swap_amount_usdc)),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount_usdc} USDC in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ODOS_V2_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=250,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        balance=Balance(amount=FVal(received_amount_eth)),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount_eth} ETH as the result of a swap in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ODOS_V2_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=251,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:1/erc20:0xBe9895146f7AF43049ca1c1AE358B0541Ea49704'),
        balance=Balance(amount=FVal(received_amount_cbeth)),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount_cbeth} cbETH as the result of a swap in Odos v2',
        counterparty=CPT_ODOS_V2,
        address=ODOS_V2_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=252,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=Asset('eip155:1/erc20:0xBe9895146f7AF43049ca1c1AE358B0541Ea49704'),
        balance=Balance(amount=FVal(odos_fees_cbeth)),
        location_label=ethereum_accounts[0],
        notes=f'Spend {odos_fees_cbeth} cbETH as an Odos v2 fee',
        counterparty=CPT_ODOS_V2,
        address=ODOS_V2_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=253,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(odos_fees_eth)),
        location_label=ethereum_accounts[0],
        notes=f'Spend {odos_fees_eth} ETH as an Odos v2 fee',
        counterparty=CPT_ODOS_V2,
        address=ODOS_V2_ROUTER,
    )]
    assert expected_events == events
