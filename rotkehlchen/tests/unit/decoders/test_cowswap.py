import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.cowswap.constants import CPT_COWSWAP
from rotkehlchen.chain.evm.decoding.cowswap.decoder import GPV2_SETTLEMENT_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import (
    A_ETH,
    A_GNOSIS_VCOW,
    A_USDC,
    A_USDT,
    A_VCOW,
    A_WBTC,
    A_WETH,
    A_XDAI,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
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
    timestamp = TimestampMS(1676976635000)
    full_amount = FVal('0.15463537')
    raw_amount = '0.15395918'
    fee_amount = '0.00067619'
    assert full_amount == FVal(raw_amount) + FVal(fee_amount)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_WBTC,
            balance=Balance(amount=FVal(raw_amount)),
            location_label=user_address,
            notes=f'Swap {raw_amount} WBTC in cowswap',
            counterparty=CPT_COWSWAP,
            address=GPV2_SETTLEMENT_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            balance=Balance(amount=FVal('3800')),
            location_label=user_address,
            notes='Receive 3800 USDC as the result of a swap in cowswap',
            counterparty=CPT_COWSWAP,
            address=GPV2_SETTLEMENT_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_WBTC,
            balance=Balance(amount=FVal(fee_amount)),
            location_label=user_address,
            notes=f'Spend {fee_amount} WBTC as a cowswap fee',
            counterparty=CPT_COWSWAP,
            address=GPV2_SETTLEMENT_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
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
    timestamp = TimestampMS(1676976635000)
    full_amount = FVal('99.99')
    raw_amount = '89.682951'
    fee_amount = '10.307049'
    assert full_amount == FVal(raw_amount) + FVal(fee_amount)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDT,
            balance=Balance(amount=FVal(raw_amount)),
            location_label=user_address,
            notes=f'Swap {raw_amount} USDT in cowswap',
            counterparty=CPT_COWSWAP,
            address=GPV2_SETTLEMENT_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.053419767450716028')),
            location_label=user_address,
            notes='Receive 0.053419767450716028 ETH as the result of a swap in cowswap',
            counterparty=CPT_COWSWAP,
            address=GPV2_SETTLEMENT_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USDT,
            balance=Balance(amount=FVal(fee_amount)),
            location_label=user_address,
            notes=f'Spend {fee_amount} USDT as a cowswap fee',
            counterparty=CPT_COWSWAP,
            address=GPV2_SETTLEMENT_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
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
    timestamp = TimestampMS(1676987243000)
    full_amount = FVal('24.311042505395616962')
    raw_amount = '24.304521595868826446'
    fee_amount = '0.006520909526790516'
    assert full_amount == FVal(raw_amount) + FVal(fee_amount)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(amount=FVal(raw_amount)),
            location_label=user_address,
            notes=f'Swap {raw_amount} ETH in cowswap',
            counterparty=CPT_COWSWAP,
            address=GPV2_SETTLEMENT_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USDC,
            balance=Balance(amount=FVal('40690.637506')),
            location_label=user_address,
            notes='Receive 40690.637506 USDC as the result of a swap in cowswap',
            counterparty=CPT_COWSWAP,
            address=GPV2_SETTLEMENT_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(fee_amount)),
            location_label=user_address,
            notes=f'Spend {fee_amount} ETH as a cowswap fee',
            counterparty=CPT_COWSWAP,
            address=GPV2_SETTLEMENT_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
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

    timestamp = TimestampMS(1676976635000)
    asset_fund = Asset('eip155:1/erc20:0xe9B076B476D8865cDF79D1Cf7DF420EE397a7f75')
    full_amount1 = FVal('16000')
    raw_amount1 = '15977.954584364'
    fee_amount1 = '22.045415636'
    assert full_amount1 == FVal(raw_amount1) + FVal(fee_amount1)
    full_amount2 = FVal('99.99')
    raw_amount2 = '89.682951'
    fee_amount2 = '10.307049'
    assert full_amount2 == FVal(raw_amount2) + FVal(fee_amount2)

    expected_events = [
        EvmEvent(  # approval
            tx_hash=evmhash,
            sequence_index=9,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=asset_fund,
            balance=Balance(amount=FVal('115792089237316195423570985008687907853269984665640564039457583991913.129639935')),
            location_label=user_address_1,
            notes='Set FUND spending approval of 0x0D2f07876685bEcd81DDa1C897f2D6Cacc733fc1 by 0xC92E8bdf79f0507f65a392b0ab4667716BFE0110 to 115792089237316195423570985008687907853269984665640564039457583991913.129639935',  # noqa: E501
            address='0xC92E8bdf79f0507f65a392b0ab4667716BFE0110',

        ), EvmEvent(  # 1st swap with FUND
            tx_hash=evmhash,
            sequence_index=11,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=asset_fund,
            balance=Balance(amount=FVal(raw_amount1)),
            location_label=user_address_1,
            notes=f'Swap {raw_amount1} FUND in cowswap',
            counterparty=CPT_COWSWAP,
            address=GPV2_SETTLEMENT_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=12,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_WETH,
            balance=Balance(amount=FVal('4.870994011222719015')),
            location_label=user_address_1,
            notes='Receive 4.870994011222719015 WETH as the result of a swap in cowswap',
            counterparty=CPT_COWSWAP,
            address=GPV2_SETTLEMENT_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=13,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.FEE,
            asset=asset_fund,
            balance=Balance(amount=FVal(fee_amount1)),
            location_label=user_address_1,
            notes=f'Spend {fee_amount1} FUND as a cowswap fee',
            counterparty=CPT_COWSWAP,
            address=GPV2_SETTLEMENT_ADDRESS,
        ), EvmEvent(  # 2nd swap with USDT
            tx_hash=evmhash,
            sequence_index=14,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDT,
            balance=Balance(amount=FVal(raw_amount2)),
            location_label=user_address_2,
            notes=f'Swap {raw_amount2} USDT in cowswap',
            counterparty=CPT_COWSWAP,
            address=GPV2_SETTLEMENT_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=15,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.053419767450716028')),
            location_label=user_address_2,
            notes='Receive 0.053419767450716028 ETH as the result of a swap in cowswap',
            counterparty=CPT_COWSWAP,
            address=GPV2_SETTLEMENT_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=16,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USDT,
            balance=Balance(amount=FVal(fee_amount2)),
            location_label=user_address_2,
            notes=f'Spend {fee_amount2} USDT as a cowswap fee',
            counterparty=CPT_COWSWAP,
            address=GPV2_SETTLEMENT_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
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


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_place_xdai_order(database, gnosis_inquirer, gnosis_accounts):
    tx_hex = deserialize_evm_tx_hash('0x0fa7c5936310a7fefa2b62597aea88fd152f73e736eee805d26e9337f461bc4f')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = gnosis_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1691568565000),
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            balance=Balance(amount=FVal('0.0000901568')),
            location_label=user_address,
            notes='Burned 0.0000901568 XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1691568565000),
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.PLACE_ORDER,
            asset=A_XDAI,
            balance=Balance(amount=FVal('2')),
            location_label=user_address,
            notes='Deposit 2 XDAI to swap it for USDC in cowswap',
            counterparty=CPT_COWSWAP,
            address=string_to_evm_address('0x40A50cf069e992AA4536211B23F286eF88752187'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
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


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0xb0e83C2D71A991017e0116d58c5765Abc57384af']])
def test_invalidate_gnosis_order(database, gnosis_inquirer, gnosis_accounts):
    tx_hex = deserialize_evm_tx_hash('0x68927e822317242ac1c0a0c71f2303725fc998164f1bb812f61b3053ef2a9a02')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = gnosis_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1697119590000),
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            balance=Balance(amount=FVal('0.000369223819835234')),
            location_label=user_address,
            notes='Burned 0.000369223819835234 XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1697119590000),
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.CANCEL_ORDER,
            asset=A_XDAI,
            balance=Balance(amount=FVal('10000')),
            location_label=user_address,
            notes='Invalidate an order that intended to swap 10000 XDAI in cowswap',
            counterparty=CPT_COWSWAP,
            address=string_to_evm_address('0x40A50cf069e992AA4536211B23F286eF88752187'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
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


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x402633Ec0283F58415bcbe5b48e7F44338a349eb']])
def test_refund_gnosis_order(database, gnosis_inquirer, gnosis_accounts):
    tx_hex = deserialize_evm_tx_hash('0xb37be7c154ef4fb0fd291c647c21013abb10428181e64ba1c6305b77df929d0e')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = gnosis_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1696381750000),
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REFUND,
            asset=A_XDAI,
            balance=Balance(amount=FVal('0.01')),
            location_label=user_address,
            notes='Refund 0.01 unused XDAI from cowswap',
            counterparty=CPT_COWSWAP,
            address=string_to_evm_address('0x40A50cf069e992AA4536211B23F286eF88752187'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_swap_gnosis_tokens(database, gnosis_inquirer, gnosis_accounts):
    tx_hex = deserialize_evm_tx_hash('0x024e1da9dc2bf7ff88dd22643857979fcd954103860698203257b6db27778482')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = gnosis_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1691567755000)
    full_amount = FVal('59.848803')
    raw_amount = '59.847255'
    fee_amount = '0.001548'
    assert full_amount == FVal(raw_amount) + FVal(fee_amount)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:100/erc20:0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83'),
            balance=Balance(amount=FVal(raw_amount)),
            location_label=user_address,
            notes=f'Swap {raw_amount} USDC in cowswap',
            counterparty=CPT_COWSWAP,
            address=GPV2_SETTLEMENT_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:100/erc20:0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb'),
            balance=Balance(amount=FVal('0.531598728938365724')),
            location_label=user_address,
            notes='Receive 0.531598728938365724 GNO as the result of a swap in cowswap',
            counterparty=CPT_COWSWAP,
            address=GPV2_SETTLEMENT_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('eip155:100/erc20:0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83'),
            balance=Balance(amount=FVal(fee_amount)),
            location_label=user_address,
            notes=f'Spend {fee_amount} USDC as a cowswap fee',
            counterparty=CPT_COWSWAP,
            address=GPV2_SETTLEMENT_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xf393fb8C4BbF7e37f583D0593AD1d1b2443E205c']])
def test_ethereum_claim_airdrop(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x8d33a6f1c37da1e2b77a4595425360361b6db79ec8811ff2eef810ebb9942044')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1644614818000)
    amount = FVal('15922.558465644366037906')
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(0.006544511735317699)),
            location_label=user_address,
            notes='Burned 0.006544511735317699 ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=379,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=A_VCOW,
            balance=Balance(amount),
            location_label=user_address,
            notes=f'Claim {amount} vCOW from cowswap airdrop',
            tx_hash=tx_hash,
            counterparty=CPT_COWSWAP,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_gnosis_claim_airdrop(database, gnosis_inquirer, gnosis_accounts):
    user_address = gnosis_accounts[0]
    tx_hash = deserialize_evm_tx_hash('0x85540c0cb716efa6027ff9415c700ecb36d382aafa18749b9e66c67e66f47b8d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1644617690000)
    amount = FVal('34.73918333042108124')
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            balance=Balance(amount=FVal(0.000121524)),
            location_label=user_address,
            notes='Burned 0.000121524 XDAI for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=23,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=A_GNOSIS_VCOW,
            balance=Balance(amount),
            location_label=user_address,
            notes=f'Claim {amount} vCOW from cowswap airdrop',
            tx_hash=tx_hash,
            counterparty=CPT_COWSWAP,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x773d161310d07CaFC6f767Ca24f43e52163b9BE6']])
def test_ethereum_vested_claim(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xb6b58ea77542bfeec311c2df5707fe002b62c5a5d648aa17892d680f4e0d6e07')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704960791000)
    gas, amount = '0.001562177312628784', '4278.42414719412947787'
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(FVal(gas)),
            location_label=user_address,
            notes=f'Burned {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_VCOW,
            balance=Balance(FVal(amount)),
            location_label=user_address,
            notes=f'Exchange {amount} vested vCOW for COW',
            tx_hash=tx_hash,
            counterparty=CPT_COWSWAP,
            address=string_to_evm_address('0xD057B63f5E69CF1B929b356b579Cba08D7688048'),
        ), EvmEvent(
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:1/erc20:0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB'),
            balance=Balance(FVal(amount)),
            location_label=user_address,
            notes=f'Claim {amount} COW from vesting tokens',
            tx_hash=tx_hash,
            counterparty=CPT_COWSWAP,
            address=string_to_evm_address('0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_gnosis_vested_claim(database, gnosis_inquirer, gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0x57ecb8f87eed5548cb375ea695531d6849843d6217771a5c25c957058a460243')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    user_address = gnosis_accounts[0]
    timestamp = TimestampMS(1707738405000)
    gas, amount = '0.000520287498374868', '99.807039723201809834'
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            balance=Balance(FVal(gas)),
            location_label=user_address,
            notes=f'Burned {gas} XDAI for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_GNOSIS_VCOW,
            balance=Balance(FVal(amount)),
            location_label=user_address,
            notes=f'Exchange {amount} vested vCOW for COW',
            tx_hash=tx_hash,
            counterparty=CPT_COWSWAP,
            address=string_to_evm_address('0xc20C9C13E853fc64d054b73fF21d3636B2d97eaB'),
        ), EvmEvent(
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:100/erc20:0x177127622c4A00F3d409B75571e12cB3c8973d3c'),
            balance=Balance(FVal(amount)),
            location_label=user_address,
            notes=f'Claim {amount} COW from vesting tokens',
            tx_hash=tx_hash,
            counterparty=CPT_COWSWAP,
            address=string_to_evm_address('0x177127622c4A00F3d409B75571e12cB3c8973d3c'),
        ),
    ]
