from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.compound.v3.constants import COMPOUND_REWARDS_ADDRESS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.compound.v3.constants import CPT_COMPOUND_V3
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ARB, A_COMP, A_ETH, A_POLYGON_POS_MATIC, A_USDC, A_WBTC
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.unit.decoders.test_zerox import A_BASE_USDC
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x373aDc79FF63d5076D0685cA35031339d4E0Da82']])
def test_compound_v3_claim_comp(
        database: 'DBHandler',
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts,
) -> None:
    """Test that claiming comp reward for v3 works fine"""
    tx_hash = deserialize_evm_tx_hash('0x89b189f36989aba504c77e686cb52691fdb147873f72ef9c64c31f39bf355fc8')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1700653367000)
    gas_str = '0.002927949668742244'
    amount_str = '2.368215'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_str), usd_value=ZERO),
            location_label=user_address,
            notes=f'Burned {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=199,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_COMP,
            balance=Balance(amount=FVal(amount_str)),
            location_label=user_address,
            notes=f'Collect {amount_str} COMP from compound',
            counterparty=CPT_COMPOUND_V3,
            address=COMPOUND_REWARDS_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xc1f8d0c485eC00B9A3A54c3B9BbeB5D7a2B4265a']])
def test_compound_v3_supply(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xcac67d0ca139b9418673f04dcc18fe7805b1242566489bf2e9c99a2fea4ee01c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1712239823000)
    gas_fees, supply_amount, position_amount = '0.003305489949685846', '15000', '14999.999998'
    expected_events = [
        EvmEvent(
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
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_USDC,
            balance=Balance(amount=FVal(supply_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Deposit {supply_amount} USDC to compound v3',
            counterparty=CPT_COMPOUND_V3,
            address=string_to_evm_address('0xc3d688B66703497DAA19211EEdff47f25384cdc3'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xc3d688B66703497DAA19211EEdff47f25384cdc3'),  # cUSDCv3
            balance=Balance(amount=FVal(position_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Receive {position_amount} cUSDCv3 from compound v3',
            counterparty=CPT_COMPOUND_V3,
            address=ZERO_ADDRESS,
        )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xD7ca0E0238E3fDAB2a33646348207AB945d55df7']])
def test_compound_v3_withdraw(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xd8ba70d3e993cae4b89a68d5b991d0a85dd9888c0e6a07814c9ddd2ff4ba93d2')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1712239703000)
    gas_fees, withdraw_amount = '0.002760840922152728', '8158.266856'
    expected_events = [
        EvmEvent(
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
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0xc3d688B66703497DAA19211EEdff47f25384cdc3'),  # cUSDCv3
            balance=Balance(amount=FVal(withdraw_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Return {withdraw_amount} cUSDCv3 to compound v3',
            counterparty=CPT_COMPOUND_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_USDC,
            balance=Balance(amount=FVal(withdraw_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Withdraw {withdraw_amount} USDC from compound v3',
            counterparty=CPT_COMPOUND_V3,
            address=string_to_evm_address('0xc3d688B66703497DAA19211EEdff47f25384cdc3'),
        )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x274B56e812b7951B737e450a22e849860C8adA11']])
def test_compound_v3_borrow(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x70aca19e6ac5285a586ad9e6a6d38bb4e4a682386901e987c7f7a30ea8c2431c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1712235011000)
    gas_fees, borrow_amount = '0.003503372063979697', '30'
    expected_events = [
        EvmEvent(
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
            sequence_index=472,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_WBTC,
            balance=Balance(amount=FVal(borrow_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Borrow {borrow_amount} WBTC from compound v3',
            counterparty=CPT_COMPOUND_V3,
            address=string_to_evm_address('0xc3d688B66703497DAA19211EEdff47f25384cdc3'),
        )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x048C013be418178cBf35Fc7102d80298506e82E8']])
def test_compound_v3_repay(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2e362252c9c96669eb0801cd431d6b36bdea63968e5781d33ea58efc528ac205')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1712238731000)
    gas_fees, repay_amount = '0.00267689111806624', '15'
    expected_events = [
        EvmEvent(
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
            sequence_index=312,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=A_WBTC,
            balance=Balance(amount=FVal(repay_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Repay {repay_amount} WBTC to compound v3',
            counterparty=CPT_COMPOUND_V3,
            address=string_to_evm_address('0xc3d688B66703497DAA19211EEdff47f25384cdc3'),
        )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xF468655Ed420b3Ed7Afb4F5d4283F847DC9234F3']])
def test_ethereum_weth_repay(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xc4779bc4bb37676e6440459a5eedb14b92d20b1bcd9754b21c4f314b3c0c2b49')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1712183879000)
    gas_fees, repay_amount = '0.002215984001817839', '14.220926764078819328'
    expected_events = [
        EvmEvent(
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
            sequence_index=245,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=Asset('eip155:1/erc20:0xBe9895146f7AF43049ca1c1AE358B0541Ea49704'),  # cbETH
            balance=Balance(amount=FVal(repay_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Repay {repay_amount} cbETH to compound v3',
            counterparty=CPT_COMPOUND_V3,
            address=string_to_evm_address('0xA17581A9E3356d9A858b789D68B4d866e593aE94'),
        )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0xD350663eB2615FF8aDa1Db2A2c810129003142f1']])
def test_polygon_pos_withdraw(database, polygon_pos_inquirer, polygon_pos_accounts):
    tx_hash = deserialize_evm_tx_hash('0xb747e7075a5f4d1b4b60da150da7fb0bce7759e36d2753fed47f0f6ecbda780c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1712676523000)
    gas_fees, withdraw_amount, return_amount = '0.025730978971038568', '417.093804', '417.093805'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_POLYGON_POS_MATIC,
            balance=Balance(amount=FVal(gas_fees)),
            location_label=polygon_pos_accounts[0],
            notes=f'Burned {gas_fees} MATIC for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:137/erc20:0xF25212E676D1F7F89Cd72fFEe66158f541246445'),  # cUSDCv3
            balance=Balance(amount=FVal(return_amount)),
            location_label=polygon_pos_accounts[0],
            notes=f'Return {return_amount} cUSDCv3 to compound v3',
            counterparty=CPT_COMPOUND_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:137/erc20:0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'),  # USDC.e,
            balance=Balance(amount=FVal(withdraw_amount)),
            location_label=polygon_pos_accounts[0],
            notes=f'Withdraw {withdraw_amount} USDC from compound v3',
            counterparty=CPT_COMPOUND_V3,
            address=string_to_evm_address('0xF25212E676D1F7F89Cd72fFEe66158f541246445'),
        )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x6ac5d0D1f2D80f97De90C0b04cc904C257b258Ff']])
def test_arbitrum_one_borrow(database, arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0xf1f0e42be8a65d53c903e36a7fbf796108371a6df2f49b858517903fd42fa6df')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1712738344000)
    gas_fees, borrow_amount = '0.00000136108', '0.367655432709867671'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_fees)),
            location_label=arbitrum_one_accounts[0],
            notes=f'Burned {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=9,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_ARB,
            balance=Balance(amount=FVal(borrow_amount)),
            location_label=arbitrum_one_accounts[0],
            notes=f'Borrow {borrow_amount} ARB from compound v3',
            counterparty=CPT_COMPOUND_V3,
            address=string_to_evm_address('0xA5EDBDD9646f8dFF606d7448e414884C7d905dCA'),
        )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x1397B89726Ada5460C9f995c5EB1a63B6Dc3380B']])
def test_base_supply(database, base_inquirer, base_accounts):
    tx_hash = deserialize_evm_tx_hash('0xb6d2ad96bab5ceac90ddee9598889a288c716ef015394542aa5c42c70fc6390e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1712747817000)
    gas_fees, supply_amount, position_amount = '0.000011015992753122', '0.1', '0.099999'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_fees)),
            location_label=base_accounts[0],
            notes=f'Burned {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_BASE_USDC,
            balance=Balance(amount=FVal(supply_amount)),
            location_label=base_accounts[0],
            notes=f'Deposit {supply_amount} USDC to compound v3',
            counterparty=CPT_COMPOUND_V3,
            address=string_to_evm_address('0xb125E6687d4313864e53df431d5425969c15Eb2F'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:8453/erc20:0xb125E6687d4313864e53df431d5425969c15Eb2F'),  # cUSDCv3
            balance=Balance(amount=FVal(position_amount)),
            location_label=base_accounts[0],
            notes=f'Receive {position_amount} cUSDCv3 from compound v3',
            counterparty=CPT_COMPOUND_V3,
            address=ZERO_ADDRESS,
        )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('scroll_accounts', [['0xe53Ca0bB4E6F22514Aa1c1ABFd9634d52A808546']])
def test_scroll_withdraw(database, scroll_inquirer, scroll_accounts):
    tx_hash = deserialize_evm_tx_hash('0x0ec09157328bba439e276c83a2c3364c390d430b5bc0bddf3169d475b6fbfdee')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=scroll_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1712739257000)
    gas_fees, withdraw_amount = '0.000179933419363529', '5001.003801'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_fees)),
            location_label=scroll_accounts[0],
            notes=f'Burned {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:534352/erc20:0xB2f97c1Bd3bf02f5e74d13f02E3e26F93D77CE44'),  # cUSDCv3  # noqa: E501
            balance=Balance(amount=FVal(withdraw_amount)),
            location_label=scroll_accounts[0],
            notes=f'Return {withdraw_amount} cUSDCv3 to compound v3',
            counterparty=CPT_COMPOUND_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:534352/erc20:0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4'),  # USDC
            balance=Balance(amount=FVal(withdraw_amount)),
            location_label=scroll_accounts[0],
            notes=f'Withdraw {withdraw_amount} USDC from compound v3',
            counterparty=CPT_COMPOUND_V3,
            address=string_to_evm_address('0xB2f97c1Bd3bf02f5e74d13f02E3e26F93D77CE44'),
        )]
    assert events == expected_events
