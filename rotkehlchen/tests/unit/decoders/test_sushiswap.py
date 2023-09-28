import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
from rotkehlchen.chain.ethereum.modules.sushiswap.constants import CPT_SUSHISWAP_V2
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_USDT
from rotkehlchen.constants.misc import EXP18
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.fval import FVal
from rotkehlchen.types import (
    SUSHISWAP_PROTOCOL,
    ChainID,
    EvmInternalTransaction,
    EvmTokenKind,
    EvmTransaction,
    Location,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes

ADDY_1 = string_to_evm_address('0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF')
ADDY_2 = string_to_evm_address('0x1F14bE60172b40dAc0aD9cD72F6f0f2C245992e8')
ADDY_3 = string_to_evm_address('0x3D6a724247c4B133C3b279558e90EdD0c5d25751')


@pytest.mark.parametrize('ethereum_accounts', [[ADDY_1]])
def test_sushiswap_single_swap(database, ethereum_inquirer, eth_transactions):
    """Data for swap
    https://etherscan.io/tx/0xbfe3c8a13c325a32736beb34ea170053cdbbd1740a9c3ceca52060906b7f87bd
    """
    tx_hex = '0xbfe3c8a13c325a32736beb34ea170053cdbbd1740a9c3ceca52060906b7f87bd'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1646375440),
        block_number=14351442,
        from_address=ADDY_1,
        to_address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x38ed173900000000000000000000000000000000000000000000000109dccca56ed38b8c000000000000000000000000000000000000000000000000ff1886165de79bd900000000000000000000000000000000000000000000000000000000000000a00000000000000000000000003ba6eb0e4327b96ade6d4f3b578724208a590cef0000000000000000000000000000000000000000000000000000000060ba9a13000000000000000000000000000000000000000000000000000000000000000200000000000000000000000062b9c7356a2dc64a1969e19c23e4f579f9810aa7000000000000000000000000d533a949740bb3306d119cc777fa900ba034cd52'),  # noqa: E501
        nonce=0,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=306,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000109dccca56ed38b8c'),  # noqa: E501
                address=string_to_evm_address('0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000003ba6eb0e4327b96ade6d4f3b578724208a590cef'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000033f6ddaea2a8a54062e021873bcaee006cdf4007'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=308,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000001005f0be0b7f96826'),  # noqa: E501
                address=string_to_evm_address('0xD533a949740bb3306d119CC777fa900bA034cd52'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000033f6ddaea2a8a54062e021873bcaee006cdf4007'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000003ba6eb0e4327b96ade6d4f3b578724208a590cef'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=310,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000109dccca56ed38b8c00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001005f0be0b7f96826'),  # noqa: E501
                address=string_to_evm_address('0x33F6DDAEa2a8a54062E021873bCaEE006CdF4007'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000d9e1ce17f2641f24ae83637ab66a2cca9c378b9f'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000003ba6eb0e4327b96ade6d4f3b578724208a590cef'),  # noqa: E501
                ],
            ),
        ],
    )

    dbevmtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    events, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)

    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.00393701451),
                usd_value=ZERO,
            ),
            location_label=ADDY_1,
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=EvmToken('eip155:1/erc20:0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
            balance=Balance(amount=FVal('19.157411925828275084'), usd_value=ZERO),
            location_label=ADDY_1,
            notes='Swap 19.157411925828275084 cvxCRV in sushiswap-v2 from 0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF',  # noqa: E501
            counterparty=CPT_SUSHISWAP_V2,
            address=string_to_evm_address('0x33F6DDAEa2a8a54062E021873bCaEE006CdF4007'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=EvmToken('eip155:1/erc20:0xD533a949740bb3306d119CC777fa900bA034cd52'),
            balance=Balance(amount=FVal('18.47349725628421943'), usd_value=ZERO),
            location_label=ADDY_1,
            notes='Receive 18.47349725628421943 CRV in sushiswap-v2 from 0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF',  # noqa: E501
            counterparty=CPT_SUSHISWAP_V2,
            address=string_to_evm_address('0x33F6DDAEa2a8a54062E021873bCaEE006CdF4007'),
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[ADDY_2]])
def test_sushiswap_v2_remove_liquidity(database, ethereum_inquirer, eth_transactions):
    """
    This checks that removing liquidity to Sushiswap V2 pool is decoded properly.

    Data is taken from:
    https://etherscan.io/tx/0x4720a52fc768591cb3997da3a2eab76c54b69176f3c3f8d9a817c2d60dd449ac
    """
    tx_hash = '0x4720a52fc768591cb3997da3a2eab76c54b69176f3c3f8d9a817c2d60dd449ac'
    evmhash = deserialize_evm_tx_hash(tx_hash)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1672888271),
        block_number=16337817,
        from_address=ADDY_2,
        to_address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
        value=0,
        gas=600000,
        gas_price=34000000000,
        gas_used=196129,
        input_data=hexstring_to_bytes('0x02751cec000000000000000000000000dac17f958d2ee523a2206206994597c13d831ec70000000000000000000000000000000000000000000000000000162806697b7c000000000000000000000000000000000000000000000000000000004b92334c0000000000000000000000000000000000000000000000000e042f1c0f4b0c180000000000000000000000001f14be60172b40dac0ad9cd72f6f0f2c245992e8000000000000000000000000000000000000000000000000000001857ff21afb'),  # noqa: E501
        nonce=9642,
    )
    internal_tx = EvmInternalTransaction(
        parent_tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        trace_id=27,
        from_address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
        to_address=ADDY_2,
        value=FVal('1.122198589808876532') * EXP18,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=21,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000162806697b7c'),  # noqa: E501
                address=string_to_evm_address('0x06da0fd433C1A5d7a4faa01111c044910A184553'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000001f14be60172b40dac0ad9cd72f6f0f2c245992e8'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000006da0fd433c1a5d7a4faa01111c044910a184553'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=22,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000cef84e1df5'),  # noqa: E501
                address=string_to_evm_address('0x06da0fd433C1A5d7a4faa01111c044910A184553'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000005ad6211cd3fde39a9cecb5df6f380b8263d1e277'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=23,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000162806697b7c'),  # noqa: E501
                address=string_to_evm_address('0x06da0fd433C1A5d7a4faa01111c044910A184553'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000006da0fd433c1a5d7a4faa01111c044910a184553'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=24,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000f92d9abf9009bf4'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000006da0fd433c1a5d7a4faa01111c044910a184553'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000d9e1ce17f2641f24ae83637ab66a2cca9c378b9f'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=25,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000053f7aa5c'),  # noqa: E501
                address=string_to_evm_address('0xdAC17F958D2ee523a2206206994597C13D831ec7'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000006da0fd433c1a5d7a4faa01111c044910a184553'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000d9e1ce17f2641f24ae83637ab66a2cca9c378b9f'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=26,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000001a7309b55651a1b9acd000000000000000000000000000000000000000000000000000008e9b01789fe'),  # noqa: E501
                address=string_to_evm_address('0x06da0fd433C1A5d7a4faa01111c044910A184553'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=27,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000f92d9abf9009bf40000000000000000000000000000000000000000000000000000000053f7aa5c'),  # noqa: E501
                address=string_to_evm_address('0x06da0fd433C1A5d7a4faa01111c044910A184553'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000d9e1ce17f2641f24ae83637ab66a2cca9c378b9f'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000d9e1ce17f2641f24ae83637ab66a2cca9c378b9f'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=28,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000053f7aa5c'),  # noqa: E501
                address=string_to_evm_address('0xdAC17F958D2ee523a2206206994597C13D831ec7'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000d9e1ce17f2641f24ae83637ab66a2cca9c378b9f'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000001f14be60172b40dac0ad9cd72f6f0f2c245992e8'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=29,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000f92d9abf9009bf4'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000d9e1ce17f2641f24ae83637ab66a2cca9c378b9f'),  # noqa: E501
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(database)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        dbevmtx.add_evm_internal_transactions(cursor, [internal_tx], relevant_address=ADDY_2)  # noqa: E501
    events, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)

    assert len(events) == 4
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1672888271000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.006668386')),
            location_label=ADDY_2,
            notes='Burned 0.006668386 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1672888271000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            balance=Balance(amount=FVal('1.122198589808876532')),
            location_label=ADDY_2,
            notes='Remove 1.122198589808876532 ETH from sushiswap-v2 LP 0x06da0fd433C1A5d7a4faa01111c044910A184553',  # noqa: E501
            counterparty=CPT_SUSHISWAP_V2,
            address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
            extra_data={'pool_address': '0x06da0fd433C1A5d7a4faa01111c044910A184553'},
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=23,
            timestamp=TimestampMS(1672888271000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0x06da0fd433C1A5d7a4faa01111c044910A184553'),
            balance=Balance(amount=FVal('0.0000243611620791')),
            location_label=ADDY_2,
            notes='Send 0.0000243611620791 SLP to sushiswap-v2 pool',
            counterparty=CPT_SUSHISWAP_V2,
            address=string_to_evm_address('0x06da0fd433C1A5d7a4faa01111c044910A184553'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=30,
            timestamp=TimestampMS(1672888271000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_USDT,
            balance=Balance(amount=FVal('1408.739932')),
            location_label=ADDY_2,
            notes='Remove 1408.739932 USDT from sushiswap-v2 LP 0x06da0fd433C1A5d7a4faa01111c044910A184553',  # noqa: E501
            counterparty=CPT_SUSHISWAP_V2,
            address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
            extra_data={'pool_address': '0x06da0fd433C1A5d7a4faa01111c044910A184553'},
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[ADDY_3]])
def test_sushiswap_v2_add_liquidity(database, ethereum_inquirer, eth_transactions):
    """
    This checks that adding liquidity to Sushiswap V2 pool is decoded properly.

    Data is taken from:
    https://etherscan.io/tx/0x2ce6f92f4020fdc4ed69a173b10c1dd2811184fac34d56188270950db1152f3a
    """
    tx_hash = '0x2ce6f92f4020fdc4ed69a173b10c1dd2811184fac34d56188270950db1152f3a'
    evmhash = deserialize_evm_tx_hash(tx_hash)
    timestamp = TimestampMS(1672893947000)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1672893947),
        block_number=16338287,
        from_address=ADDY_3,
        to_address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
        value=797012710918264,
        gas=245745,
        gas_price=17231958700,
        gas_used=178679,
        input_data=hexstring_to_bytes('0xf305d719000000000000000000000000dac17f958d2ee523a2206206994597c13d831ec700000000000000000000000000000000000000000000000000000000000f424000000000000000000000000000000000000000000000000000000000000f2eb80000000000000000000000000000000000000000000000000002d1412337da580000000000000000000000003d6a724247c4b133c3b279558e90edd0c5d257510000000000000000000000000000000000000000000000000000000063b65ceb'),  # noqa: E501
        nonce=67,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=216,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000000000f4238'),  # noqa: E501
                address=string_to_evm_address('0xdAC17F958D2ee523a2206206994597C13D831ec7'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000003d6a724247c4b133c3b279558e90edd0c5d25751'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000006da0fd433c1a5d7a4faa01111c044910a184553'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=217,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000002d4e0fb840878'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000d9e1ce17f2641f24ae83637ab66a2cca9c378b9f'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=218,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000002d4e0fb840878'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000d9e1ce17f2641f24ae83637ab66a2cca9c378b9f'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000006da0fd433c1a5d7a4faa01111c044910a184553'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=219,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000022bb176c3'),  # noqa: E501
                address=string_to_evm_address('0x06da0fd433C1A5d7a4faa01111c044910A184553'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000005ad6211cd3fde39a9cecb5df6f380b8263d1e277'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=220,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000406ffeca5'),  # noqa: E501
                address=string_to_evm_address('0x06da0fd433C1A5d7a4faa01111c044910A184553'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000003d6a724247c4b133c3b279558e90edd0c5d25751'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=221,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000001a750097ed3da4ab454000000000000000000000000000000000000000000000000000008e92483e6d3'),  # noqa: E501
                address=string_to_evm_address('0x06da0fd433C1A5d7a4faa01111c044910A184553'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=222,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000002d4e0fb84087800000000000000000000000000000000000000000000000000000000000f4238'),  # noqa: E501
                address=string_to_evm_address('0x06da0fd433C1A5d7a4faa01111c044910A184553'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000d9e1ce17f2641f24ae83637ab66a2cca9c378b9f'),  # noqa: E501
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(database)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
    events, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)

    lp_token_identifier = evm_address_to_identifier(
        address='0x06da0fd433C1A5d7a4faa01111c044910A184553',
        chain_id=ChainID.ETHEREUM,
        token_type=EvmTokenKind.ERC20,
    )
    assert len(events) == 4
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.0030789891485573')),
            location_label=ADDY_3,
            notes='Burned 0.0030789891485573 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.000797012710918264')),
            location_label=ADDY_3,
            notes='Deposit 0.000797012710918264 ETH to sushiswap-v2 LP 0x06da0fd433C1A5d7a4faa01111c044910A184553',  # noqa: E501
            counterparty=CPT_SUSHISWAP_V2,
            address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
            extra_data={'pool_address': '0x06da0fd433C1A5d7a4faa01111c044910A184553'},
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=218,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_USDT,
            balance=Balance(amount=FVal('0.999992')),
            location_label=ADDY_3,
            notes='Deposit 0.999992 USDT to sushiswap-v2 LP 0x06da0fd433C1A5d7a4faa01111c044910A184553',  # noqa: E501
            counterparty=CPT_SUSHISWAP_V2,
            address=string_to_evm_address('0x06da0fd433C1A5d7a4faa01111c044910A184553'),
            extra_data={'pool_address': '0x06da0fd433C1A5d7a4faa01111c044910A184553'},
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=222,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset(lp_token_identifier),
            balance=Balance(amount=FVal('1.7297304741E-8')),
            location_label=ADDY_3,
            notes='Receive 0.000000017297304741 SLP from sushiswap-v2 pool',
            counterparty=CPT_SUSHISWAP_V2,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events
    assert EvmToken(lp_token_identifier).protocol == SUSHISWAP_PROTOCOL
