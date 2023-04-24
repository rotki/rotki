import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.cowswap.constants import CPT_COWSWAP
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_USDC, A_USDT, A_WBTC, A_WETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x31b6020CeF40b72D1e53562229c1F9200d00CC12']])
def test_swap_token_to_token(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0xd4d16ea74bbf806715f5f0e799fd5e8befbf369a9e5461fa9c0ed88d72bd06e4')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=4,
            timestamp=TimestampMS(1676976635000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_WBTC,
            balance=Balance(amount=FVal('0.15463537')),
            location_label=user_address,
            notes='Swap 0.15463537 WBTC in cowswap',
            counterparty=CPT_COWSWAP,
            address=string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=34,
            timestamp=TimestampMS(1676976635000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            balance=Balance(amount=FVal('3800')),
            location_label=user_address,
            notes='Receive 3800 USDC as the result of a swap in cowswap',
            counterparty=CPT_COWSWAP,
            address=string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x34938Bd809BDf57178df6DF523759B4083A29190']])
def test_swap_token_to_eth(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0xd4d16ea74bbf806715f5f0e799fd5e8befbf369a9e5461fa9c0ed88d72bd06e4')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1676976635000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDT,
            balance=Balance(amount=FVal('99.99')),
            location_label=user_address,
            notes='Swap 99.99 USDT in cowswap',
            counterparty=CPT_COWSWAP,
            address=string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=10,
            timestamp=TimestampMS(1676976635000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.053419767450716028')),
            location_label=user_address,
            notes='Receive 0.053419767450716028 ETH as the result of a swap in cowswap',  # noqa: E501
            counterparty=CPT_COWSWAP,
            address=string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xcFeA48Cf6Ba36e0328a6Ead0fdB4C2642D21c59d']])
def test_swap_eth_to_token(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0xe2d6aa636623989061f1d762b19ca6fe6bc0edb5a890cf5a934a8fc6d42dcaca')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1676987243000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(amount=FVal('24.311042505395616962')),
            location_label=user_address,
            notes='Swap 24.311042505395616962 ETH in cowswap',
            counterparty=CPT_COWSWAP,
            address=string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=321,
            timestamp=TimestampMS(1676987243000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USDC,
            balance=Balance(amount=FVal('40690.637506')),
            location_label=user_address,
            notes='Receive 40690.637506 USDC as the result of a swap in cowswap',
            counterparty=CPT_COWSWAP,
            address=string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x0D2f07876685bEcd81DDa1C897f2D6Cacc733fc1',
    '0x34938Bd809BDf57178df6DF523759B4083A29190',
]])
def test_2_decoded_swaps(database, ethereum_inquirer, ethereum_accounts):
    """
    Tests that if a user has 2 tracked addresses from a cowswap settlement transaction
    both swaps are decoded correctly.
    """
    tx_hex = deserialize_evm_tx_hash('0xd4d16ea74bbf806715f5f0e799fd5e8befbf369a9e5461fa9c0ed88d72bd06e4')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address_1, user_address_2 = ethereum_accounts
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1676976635000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDT,
            balance=Balance(amount=FVal('99.99')),
            location_label=user_address_2,
            notes='Swap 99.99 USDT in cowswap',
            counterparty=CPT_COWSWAP,
            address=string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1676976635000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.053419767450716028')),
            location_label=user_address_2,
            notes='Receive 0.053419767450716028 ETH as the result of a swap in cowswap',  # noqa: E501
            counterparty=CPT_COWSWAP,
            address=string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=8,
            timestamp=TimestampMS(1676976635000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0xe9B076B476D8865cDF79D1Cf7DF420EE397a7f75'),
            balance=Balance(amount=FVal('16000')),
            location_label=user_address_1,
            notes='Swap 16000 FUND in cowswap',
            counterparty=CPT_COWSWAP,
            address=string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=9,
            timestamp=TimestampMS(1676976635000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_WETH,
            balance=Balance(amount=FVal('4.870994011222719015')),
            location_label=user_address_1,
            notes='Receive 4.870994011222719015 WETH as the result of a swap in cowswap',  # noqa: E501
            counterparty=CPT_COWSWAP,
            address=string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=37,
            timestamp=TimestampMS(1676976635000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0xe9B076B476D8865cDF79D1Cf7DF420EE397a7f75'),
            balance=Balance(amount=FVal('115792089237316195423570985000000000000000000000000000000000000000000')),  # noqa: E501
            location_label=user_address_1,
            notes='Set FUND spending approval of 0x0D2f07876685bEcd81DDa1C897f2D6Cacc733fc1 by 0xC92E8bdf79f0507f65a392b0ab4667716BFE0110 to 115792089237316195423570985000000000000000000000000000000000000000000',  # noqa: E501
            address='0xC92E8bdf79f0507f65a392b0ab4667716BFE0110',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xcFeA48Cf6Ba36e0328a6Ead0fdB4C2642D21c59d']])
def test_place_eth_order(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x3619cc8d8f60541df0ea7d96d923efa4c783f53491af0d3ed1ed31de9fe15bcf')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1676987159000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.001768460133875456')),
            location_label=user_address,
            notes='Burned 0.001768460133875456 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1676987159000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.PLACE_ORDER,
            asset=A_ETH,
            balance=Balance(amount=FVal('24.311042505395616962')),
            location_label=user_address,
            notes='Deposit 24.311042505395616962 ETH to swap it for USDC in cowswap',
            counterparty=CPT_COWSWAP,
            address=string_to_evm_address('0x40A50cf069e992AA4536211B23F286eF88752187'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xdc4CaDC65123Ebd371887CaD59Cc8c6F8F6fC29c']])
def test_invalidate_eth_order(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x5769b4634ae26ec93aebc80a50e0676b0793af485041b249652bd7ee6703a9f5')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1677040511000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.001171136978414093')),
            location_label=user_address,
            notes='Burned 0.001171136978414093 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1677040511000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.CANCEL_ORDER,
            asset=A_ETH,
            balance=Balance(amount=FVal('50')),
            location_label=user_address,
            notes='Invalidate an order that intended to swap 50 ETH in cowswap',
            counterparty=CPT_COWSWAP,
            address=string_to_evm_address('0x40A50cf069e992AA4536211B23F286eF88752187'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x4DD2a258130673a2d4242FaC1C5E5f82d1A0888d']])
def test_refund_eth_order(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x424f29ad7b865d764d89fe28767a7f34d177cad71cc123a2a8c0209aa0b70fda')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1677055175000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REFUND,
            asset=A_ETH,
            balance=Balance(amount=FVal('11')),
            location_label=user_address,
            notes='Refund 11 unused ETH from cowswap',
            counterparty=CPT_COWSWAP,
            address=string_to_evm_address('0x40A50cf069e992AA4536211B23F286eF88752187'),
        ),
    ]
    assert events == expected_events
