import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.ethereum.modules.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_LINK, A_USDC, A_USDT
from rotkehlchen.constants.misc import EXP18, ZERO
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    EvmInternalTransaction,
    EvmTransaction,
    Location,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes


@pytest.mark.parametrize('ethereum_accounts', [['0x57bF3B0f29E37619623994071C9e12091919675c']])  # noqa: E501
def test_curve_deposit(database, ethereum_transaction_decoder):
    """Data for deposit taken from
    https://etherscan.io/tx/0x523b7df8e168315e97a836a3d516d639908814785d7df1ef1745de3e55501982
    tests that a deposit for the aave pool in curve works correctly
    """
    tx_hex = '0x523b7df8e168315e97a836a3d516d639908814785d7df1ef1745de3e55501982'
    location_label = '0x57bF3B0f29E37619623994071C9e12091919675c'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        chain_id=ChainID.ETHEREUM,
        tx_hash=evmhash,
        timestamp=1650276061,
        block_number=14608535,
        from_address=string_to_evm_address('0x57bF3B0f29E37619623994071C9e12091919675c'),
        to_address=string_to_evm_address('0xDeBF20617708857ebe4F679508E7b7863a8A8EeE'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x2b6e993a000000000000000000000000000000000000000000005512b9a6a672640100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000060c5f3590000000000000000000000000000000000000000000005255abbd43baa53603f90000000000000000000000000000000000000000000000000000000000000001'),  # noqa: E501
        nonce=599,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=370,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000005512b9a6a67264010000'),  # noqa: E501
                address=string_to_evm_address('0x6B175474E89094C44Da98b954EedeAC495271d0F'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000057bf3b0f29e37619623994071c9e12091919675c'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000debf20617708857ebe4f679508e7b7863a8a8eee'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=383,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000060c5f3590'),  # noqa: E501
                address=string_to_evm_address('0xdAC17F958D2ee523a2206206994597C13D831ec7'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000057bf3b0f29e37619623994071c9e12091919675c'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000debf20617708857ebe4f679508e7b7863a8a8eee'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=396,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000005328394d50efea7abaf4'),  # noqa: E501
                address=string_to_evm_address('0xFd2a8fA60Abd58Efe3EeE34dd494cD491dC14900'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000057bf3b0f29e37619623994071c9e12091919675c'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=397,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000005512b9a6a672640100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000060c5f3590000000000000000000000000000000000000000000000002038eb27e79fe96ef0000000000000000000000000000000000000000000000000000000002e973710000000000000000000000000000000000000000000000000000000001832b050000000000000000000000000000000000000000002a38dd00eecdefe02a2fcf00000000000000000000000000000000000000000026c6b056a9a8e3b89d5717'),  # noqa: E501
                address=string_to_evm_address('0xDeBF20617708857ebe4F679508E7b7863a8A8EeE'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x423f6495a08fc652425cf4ed0d1f9e37e571d9b9529b1c1c23cce780b2e7df0d'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000057bf3b0f29e37619623994071c9e12091919675c'),  # noqa: E501
                ],
            ),
        ],
    )

    dbevmtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
    events = ethereum_transaction_decoder.decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )
    timestamp = TimestampMS(1650276061000)
    expected_events = [
        EvmEvent(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.00393701451),
                usd_value=ZERO,
            ),
            location_label=location_label,
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=371,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0xFd2a8fA60Abd58Efe3EeE34dd494cD491dC14900'),
            balance=Balance(amount=FVal('392698.416886553664731892'), usd_value=ZERO),
            location_label=location_label,
            notes='Receive 392698.416886553664731892 a3CRV after depositing in curve pool 0xDeBF20617708857ebe4F679508E7b7863a8A8EeE',  # noqa: E501
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
            extra_data={'deposit_events_num': 2},
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=372,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_DAI,
            balance=Balance(amount=FVal('401746.57'), usd_value=ZERO),
            location_label=location_label,
            notes='Deposit 401746.57 DAI in curve pool 0xDeBF20617708857ebe4F679508E7b7863a8A8EeE',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xDeBF20617708857ebe4F679508E7b7863a8A8EeE'),
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=384,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_USDT,
            balance=Balance(amount=FVal('25977.37'), usd_value=ZERO),
            location_label=location_label,
            notes='Deposit 25977.37 USDT in curve pool 0xDeBF20617708857ebe4F679508E7b7863a8A8EeE',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xDeBF20617708857ebe4F679508E7b7863a8A8EeE'),
        )]
    assert len(events) == 4
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0x767B35b9F06F6e28e5ed05eE7C27bDf992eba5d2']])  # noqa: E501
def test_curve_deposit_eth(database, ethereum_transaction_decoder):
    """Data for deposit taken from
    https://etherscan.io/tx/0x51c052c8fb60f092f98ffc3cab6340c7c5348ee3b339582feba1c17cbd97ea56
    This tests uses the steth/eth pool to verify that deposits including transfer of ETH work
    properly
    """
    tx_hex = '0x51c052c8fb60f092f98ffc3cab6340c7c5348ee3b339582feba1c17cbd97ea56'
    location_label = '0x767B35b9F06F6e28e5ed05eE7C27bDf992eba5d2'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=1650276061,
        block_number=14608535,
        from_address=location_label,
        to_address=string_to_evm_address('0xDC24316b9AE028F1497c275EB9192a3Ea0f67022'),
        value=FVal(0.2) * EXP18,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x0b4c7e4d00000000000000000000000000000000000000000000000002c68af0bb14000000000000000000000000000000000000000000000000000002c6526ca273a800000000000000000000000000000000000000000000000000054aaa619fda0c01'),  # noqa: E501
        nonce=5,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=412,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000002c6526ca273a800'),  # noqa: E501
                address=string_to_evm_address('0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000767b35b9f06f6e28e5ed05ee7c27bdf992eba5d2'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000dc24316b9ae028f1497c275eb9192a3ea0f67022'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=413,
                data=hexstring_to_bytes('0xfffffffffffffffffffffffffffffffffffffffffffffffffd39ad935d8c57ff'),  # noqa: E501
                address=string_to_evm_address('0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000767b35b9f06f6e28e5ed05ee7c27bdf992eba5d2'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000dc24316b9ae028f1497c275eb9192a3ea0f67022'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=414,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000005589f42020a37df'),  # noqa: E501
                address=string_to_evm_address('0x06325440D014e39736583c165C2963BA99fAf14E'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000767b35b9f06f6e28e5ed05ee7c27bdf992eba5d2'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=415,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000002c68af0bb14000000000000000000000000000000000000000000000000000002c6526ca273a80000000000000000000000000000000000000000000000000000000016a92ed4ce00000000000000000000000000000000000000000000000000000016a9b386830000000000000000000000000000000000000000000156e4db21d9cf6a6d4f3f000000000000000000000000000000000000000000014a4959a6fb2bf53a7108'),  # noqa: E501
                address=string_to_evm_address('0xDC24316b9AE028F1497c275EB9192a3Ea0f67022'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x26f55a85081d24974e85c6c00045d0f0453991e95873f52bff0d21af4079a768'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000767b35b9f06f6e28e5ed05ee7c27bdf992eba5d2'),  # noqa: E501
                ],
            ),
        ],
    )

    dbevmtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
    events = ethereum_transaction_decoder.decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )
    timestamp = TimestampMS(1650276061000)
    expected_events = [
        EvmEvent(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.00393701451),
                usd_value=ZERO,
            ),
            location_label=location_label,
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x06325440D014e39736583c165C2963BA99fAf14E'),
            balance=Balance(amount=FVal('0.385232873991059423'), usd_value=ZERO),
            location_label=location_label,
            notes='Receive 0.385232873991059423 steCRV after depositing in curve pool 0xDC24316b9AE028F1497c275EB9192a3Ea0f67022',  # noqa: E501
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
            extra_data={'deposit_events_num': 2},
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.2'), usd_value=ZERO),
            location_label=location_label,
            notes='Deposit 0.2 ETH in curve pool',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xDC24316b9AE028F1497c275EB9192a3Ea0f67022'),
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=414,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=EvmToken('eip155:1/erc20:0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'),
            balance=Balance(amount=FVal('0.19993786'), usd_value=ZERO),
            location_label=location_label,
            notes='Deposit 0.19993786 stETH in curve pool 0xDC24316b9AE028F1497c275EB9192a3Ea0f67022',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xDC24316b9AE028F1497c275EB9192a3Ea0f67022'),
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=415,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=EvmToken('eip155:1/erc20:0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'),
            balance=Balance(amount=FVal('1.157920892373161954235709850E+59'), usd_value=ZERO),
            location_label=location_label,
            notes='Set stETH spending approval of 0x767B35b9F06F6e28e5ed05eE7C27bDf992eba5d2 by 0xDC24316b9AE028F1497c275EB9192a3Ea0f67022 to 115792089237316195423570985000000000000000000000000000000000',  # noqa: E501
            address=string_to_evm_address('0xDC24316b9AE028F1497c275EB9192a3Ea0f67022'),
        )]
    assert len(events) == 5
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0xDf9f0AE722A3919fE7f9cC8805773ef142007Ca6']])  # noqa: E501
def test_curve_remove_liquidity(database, ethereum_transaction_decoder):
    """Data for deposit taken from
    https://etherscan.io/tx/0xd63dccdbebeede3a1f50b97c0a8592255203a0559880b80377daa39f915741b0
    This tests uses the link pool to verify that withdrawals are correctly decoded
    """
    tx_hex = '0xd63dccdbebeede3a1f50b97c0a8592255203a0559880b80377daa39f915741b0'
    location_label = '0xDf9f0AE722A3919fE7f9cC8805773ef142007Ca6'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=1650276061,
        block_number=14608535,
        from_address=location_label,
        to_address=string_to_evm_address('0xF178C0b5Bb7e7aBF4e12A4838C7b7c5bA2C623c0'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x1a4d01d20000000000000000000000000000000000000000000000a8815561fefbe56aa300000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000a8d15fc942541fea7f'),  # noqa: E501
        nonce=5,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=506,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000a8815561fefbe56aa3'),  # noqa: E501
                address=string_to_evm_address('0xcee60cFa923170e4f8204AE08B4fA6A3F5656F3a'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000df9f0ae722a3919fe7f9cc8805773ef142007ca6'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=507,
                data=hexstring_to_bytes('0000000000000000000000000000000000000000000000a93078ae269dbeca10'),  # noqa: E501
                address=string_to_evm_address('0x514910771AF9Ca656af840dff83E8264EcF986CA'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000f178c0b5bb7e7abf4e12a4838c7b7c5ba2c623c0'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000df9f0ae722a3919fe7f9cc8805773ef142007ca6'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=508,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000a8815561fefbe56aa30000000000000000000000000000000000000000000000a93078ae269dbeca100000000000000000000000000000000000000000000092c009040e68c381c519'),  # noqa: E501
                address=string_to_evm_address('0xF178C0b5Bb7e7aBF4e12A4838C7b7c5bA2C623c0'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x5ad056f2e28a8cec232015406b843668c1e36cda598127ec3b8c59b8c72773a0'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000df9f0ae722a3919fe7f9cc8805773ef142007ca6'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=415,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000002c68af0bb14000000000000000000000000000000000000000000000000000002c6526ca273a80000000000000000000000000000000000000000000000000000000016a92ed4ce00000000000000000000000000000000000000000000000000000016a9b386830000000000000000000000000000000000000000000156e4db21d9cf6a6d4f3f000000000000000000000000000000000000000000014a4959a6fb2bf53a7108'),  # noqa: E501
                address=string_to_evm_address('0xDC24316b9AE028F1497c275EB9192a3Ea0f67022'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x26f55a85081d24974e85c6c00045d0f0453991e95873f52bff0d21af4079a768'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000767b35b9f06f6e28e5ed05ee7c27bdf992eba5d2'),  # noqa: E501
                ],
            ),
        ],
    )

    dbevmtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
    events = ethereum_transaction_decoder.decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )
    timestamp = TimestampMS(1650276061000)
    expected_events = [
        EvmEvent(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.00393701451),
                usd_value=ZERO,
            ),
            location_label=location_label,
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=507,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0xcee60cFa923170e4f8204AE08B4fA6A3F5656F3a'),
            balance=Balance(amount=FVal('3108.372467134893484707'), usd_value=ZERO),
            location_label=location_label,
            notes='Return 3108.372467134893484707 linkCRV',
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
            extra_data={'withdrawal_events_num': 1},
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=508,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_LINK,
            balance=Balance(amount=FVal('3120.992481448818559504'), usd_value=ZERO),
            location_label=location_label,
            notes='Remove 3120.992481448818559504 LINK from the curve pool 0xF178C0b5Bb7e7aBF4e12A4838C7b7c5bA2C623c0',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xF178C0b5Bb7e7aBF4e12A4838C7b7c5bA2C623c0'),
        )]
    assert expected_events == events


@pytest.mark.parametrize('ethereum_accounts', [['0xa8005630caE7b7d2AFADD38FD3B3040d13cbE2BC']])  # noqa: E501
def test_curve_remove_liquidity_with_internal(database, ethereum_transaction_decoder):
    """Data for deposit taken from
    https://etherscan.io/tx/0x30bb99f3e34fb1fbcf009320af7e290caf18b04b207319e15aa8ffbf645f4ad9
    This tests uses the steth pool to verify that withdrawals are correctly decoded when an
    internal transaction is made for eth transfers
    """
    tx_hex = '0x30bb99f3e34fb1fbcf009320af7e290caf18b04b207319e15aa8ffbf645f4ad9'
    location_label = '0xa8005630caE7b7d2AFADD38FD3B3040d13cbE2BC'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=1650276061,
        block_number=14647221,
        from_address=location_label,
        to_address=string_to_evm_address('0xF178C0b5Bb7e7aBF4e12A4838C7b7c5bA2C623c0'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x1a4d01d20000000000000000000000000000000000000000000000a8815561fefbe56aa300000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000a8d15fc942541fea7f'),  # noqa: E501
        nonce=5,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=191,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000dc335d474901e08'),  # noqa: E501
                address=string_to_evm_address('0x06325440D014e39736583c165C2963BA99fAf14E'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000a8005630cae7b7d2afadd38fd3b3040d13cbe2bc'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=192,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000dc335d474901e080000000000000000000000000000000000000000000000000e48d018621788fa'),  # noqa: E501
                address=string_to_evm_address('0xDC24316b9AE028F1497c275EB9192a3Ea0f67022'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x9e96dd3b997a2a257eec4df9bb6eaf626e206df5f543bd963682d143300be310'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000a8005630cae7b7d2afadd38fd3b3040d13cbe2bc'),  # noqa: E501
                ],
            ),
        ],
    )
    internal_tx = EvmInternalTransaction(
        parent_tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        trace_id=27,
        timestamp=Timestamp(1591043988),
        block_number=14647221,
        from_address=string_to_evm_address('0xDC24316b9AE028F1497c275EB9192a3Ea0f67022'),
        to_address=string_to_evm_address('0xa8005630caE7b7d2AFADD38FD3B3040d13cbE2BC'),
        value=FVal('1.02930131799766041') * EXP18,
    )
    dbevmtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        dbevmtx.add_evm_internal_transactions(cursor, [internal_tx], relevant_address=location_label)  # noqa: E501
    events = ethereum_transaction_decoder.decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )
    timestamp = TimestampMS(1650276061000)
    expected_events = [
        EvmEvent(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.00393701451),
                usd_value=ZERO,
            ),
            location_label=location_label,
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x06325440D014e39736583c165C2963BA99fAf14E'),
            balance=Balance(amount=FVal('0.991695529556581896'), usd_value=ZERO),
            location_label=location_label,
            notes='Return 0.991695529556581896 steCRV',
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
            extra_data={'withdrawal_events_num': 1},
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=193,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            balance=Balance(amount=FVal('1.02930131799766041'), usd_value=ZERO),
            location_label=location_label,
            notes='Remove 1.02930131799766041 ETH from the curve pool',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xDC24316b9AE028F1497c275EB9192a3Ea0f67022'),
        )]
    assert expected_events == events


@pytest.mark.parametrize('ethereum_accounts', [['0x2fac74A3a04B031F240923621a578724C40678af']])  # noqa: E501
def test_curve_remove_imbalanced(database, ethereum_transaction_decoder):
    """Data for deposit taken from
    https://etherscan.io/tx/0xd8832abcf4773abe24d8cda5581fb53bfb3850c535c1956d1d120a72a4ebcbd8
    This tests uses the steth pool to verify that withdrawals are correctly decoded when an
    internal transaction is made for eth transfers
    """
    tx_hex = '0xd8832abcf4773abe24d8cda5581fb53bfb3850c535c1956d1d120a72a4ebcbd8'
    location_label = '0x2fac74A3a04B031F240923621a578724C40678af'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=1650276061,
        block_number=14647221,
        from_address=location_label,
        to_address=string_to_evm_address('0xbBC81d23Ea2c3ec7e56D39296F0cbB648873a5d3'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x517a55a300000000000000000000000000000000000000000000001fa9ee7266a543831f00000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000003f487c50000000000000000000000000000000000000000000000000000000000000001'),  # noqa: E501
        nonce=5,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=2183,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000001fa9ee7266a543831f'),  # noqa: E501
                address=string_to_evm_address('0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000002fac74a3a04b031f240923621a578724c40678af'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000bbc81d23ea2c3ec7e56d39296f0cbb648873a5d3'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=2184,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                address=string_to_evm_address('0x16de59092dAE5CcF4A1E6439D611fd0653f0Bd01'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000045f783cce6b7ff23b2ab2d70e416cdb7d6055f51'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000bbc81d23ea2c3ec7e56d39296f0cbb648873a5d3'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=2185,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000001fdb750a'),  # noqa: E501
                address=string_to_evm_address('0xd6aD7a6750A7593E092a9B218d66C0A814a3436e'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000045f783cce6b7ff23b2ab2d70e416cdb7d6055f51'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000bbc81d23ea2c3ec7e56d39296f0cbb648873a5d3'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=2186,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                address=string_to_evm_address('0x83f798e925BcD4017Eb265844FDDAbb448f1707D'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000045f783cce6b7ff23b2ab2d70e416cdb7d6055f51'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000bbc81d23ea2c3ec7e56d39296f0cbb648873a5d3'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=2187,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                address=string_to_evm_address('0x73a052500105205d34Daf004eAb301916DA8190f'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000045f783cce6b7ff23b2ab2d70e416cdb7d6055f51'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000bbc81d23ea2c3ec7e56d39296f0cbb648873a5d3'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=2188,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                address=string_to_evm_address('0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000bbc81d23ea2c3ec7e56d39296f0cbb648873a5d3'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=2189,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001fdb750a000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000045cf4bec2e53f0000000000000000000000000000000000000000000000000000000000000e07e000000000000000000000000000000000000000000000000000000000000570d0000000000000000000000000000000000000000000000000051077d9dc293100000000000000000000000000000000000000000000c740195f187122987a9ef0000000000000000000000000000000000000000000aeddccb3976328f7d90bd'),  # noqa: E501
                address=string_to_evm_address('0x45F783CCE6B7FF23B2ab2D70e416cdb7D6055f51'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xb964b72f73f5ef5bf0fdc559b2fab9a7b12a39e47817a547f1f0aee47febd602'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000bbc81d23ea2c3ec7e56d39296f0cbb648873a5d3'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000bbc81d23ea2c3ec7e56d39296f0cbb648873a5d3'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=2189,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000027a72df9'),  # noqa: E501
                address=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000bbc81d23ea2c3ec7e56d39296f0cbb648873a5d3'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000002fac74a3a04b031f240923621a578724c40678af'),  # noqa: E501
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
    events = ethereum_transaction_decoder.decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )
    timestamp = TimestampMS(1650276061000)
    expected_events = [
        EvmEvent(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.00393701451),
                usd_value=ZERO,
            ),
            location_label=location_label,
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=2184,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8'),
            balance=Balance(amount=FVal('584.093916507047953183'), usd_value=ZERO),
            location_label=location_label,
            notes='Return 584.093916507047953183 yDAI+yUSDC+yUSDT+yTUSD',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xbBC81d23Ea2c3ec7e56D39296F0cbB648873a5d3'),
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=2190,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_USDC,
            balance=Balance(amount=FVal('665.267705'), usd_value=ZERO),
            location_label=location_label,
            notes='Receive 665.267705 USDC from the curve pool 0xbBC81d23Ea2c3ec7e56D39296F0cbB648873a5d3',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xbBC81d23Ea2c3ec7e56D39296F0cbB648873a5d3'),
        )]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x6Bb553FFC5716782051f51b564Bb149D9946f0d2']])
def test_deposit_multiple_tokens(ethereum_transaction_decoder, ethereum_accounts):
    """Check the case for a pool where multiple deposit events appear in the transaction"""
    tx_hex = deserialize_evm_tx_hash('0xe954a396a02ebbea45a1d206c9918f717c55509c8138fccc63155d0262ef4dc4 ')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        database=ethereum_transaction_decoder.database,
        tx_hash=tx_hex,
    )
    expected_events = [
        EvmEvent(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1675186487000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.011180845456491718')),
            location_label=user_address,
            notes='Burned 0.011180845456491718 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=76,
            timestamp=TimestampMS(1675186487000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xC25a3A3b969415c80451098fa907EC722572917F'),
            balance=Balance(amount=FVal('9.423568821947938716')),
            location_label=user_address,
            notes='Receive 9.423568821947938716 crvPlain3andSUSD after depositing in curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD',  # noqa: E501
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
            extra_data={'deposit_events_num': 1},
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=80,
            timestamp=TimestampMS(1675186487000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_DAI,
            balance=Balance(amount=FVal('10')),
            location_label=user_address,
            notes='Deposit 10 DAI in curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xA5407eAE9Ba41422680e2e00537571bcC53efBfD'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xd289986c25Ae3f4644949e25bC369e9d8e0caeaD']])
def test_gauge_deposit(ethereum_transaction_decoder, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x5ae70d68241d85feac65c90e4546154e232dba9fecad9036bcec10082acc9d46')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        database=ethereum_transaction_decoder.database,
        tx_hash=tx_hex,
    )
    expected_events = [
        EvmEvent(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1679313731000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('0.007333038632457846')),
            location_label=user_address,
            notes='Burned 0.007333038632457846 ETH for gas',
            counterparty='gas',
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=200,
            timestamp=TimestampMS(1679313731000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:1/erc20:0xC25a3A3b969415c80451098fa907EC722572917F'),
            balance=Balance(amount=FVal('7985.261401730774426743')),
            location_label=user_address,
            notes='Deposit 7985.261401730774426743 crvPlain3andSUSD into 0xA90996896660DEcC6E997655E065b23788857849 curve gauge',  # noqa: E501
            counterparty='curve',
            address=string_to_evm_address('0xA90996896660DEcC6E997655E065b23788857849'),
            product=EvmProduct.CURVE_GAUGE,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xd80DF837766C8Edb6f11Bf7fD35703f87F2a31fB']])
def test_gauge_withdraw(ethereum_transaction_decoder, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x055fc6cafcdae6b367d934e9385816f89153314c5abc5d3659a65778c90342d2')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        database=ethereum_transaction_decoder.database,
        tx_hash=tx_hex,
    )
    expected_events = [
        EvmEvent(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1679346575000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('0.01157725763881742')),
            location_label=user_address,
            notes='Burned 0.01157725763881742 ETH for gas',
            counterparty='gas',
            address=None,
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=43,
            timestamp=TimestampMS(1679346575000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:1/erc20:0xC25a3A3b969415c80451098fa907EC722572917F'),
            balance=Balance(amount=FVal('37939.72737243936267785')),
            location_label=user_address,
            notes='Withdraw 37939.72737243936267785 crvPlain3andSUSD from 0xA90996896660DEcC6E997655E065b23788857849 curve gauge',  # noqa: E501
            counterparty='curve',
            address=string_to_evm_address('0xA90996896660DEcC6E997655E065b23788857849'),
            product=EvmProduct.CURVE_GAUGE,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x0E9Fed33f6a202146a615De0FA1985adFb461467']])
def test_gauge_claim_rewards(ethereum_transaction_decoder, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0xe01bc48ddb3df6eb721c122c5ddaea705b771bfb8db407e3a96ae9bab6584453')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        database=ethereum_transaction_decoder.database,
        tx_hash=tx_hex,
    )
    expected_events = [
        EvmEvent(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1679342423000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('0.004486722780852585')),
            location_label=user_address,
            notes='Burned 0.004486722780852585 ETH for gas',
            counterparty='gas',
            address=None,
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=112,
            timestamp=TimestampMS(1679342423000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:1/erc20:0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F'),
            balance=Balance(amount=FVal('0.451753537525671486')),
            location_label=user_address,
            notes='Receive 0.451753537525671486 SNX rewards from 0xA90996896660DEcC6E997655E065b23788857849 curve gauge',  # noqa: E501
            counterparty='curve',
            address=string_to_evm_address('0xA90996896660DEcC6E997655E065b23788857849'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xA8d7Fb04877C3FBf175DE76FA3D2fa66c770537F']])
def test_curve_trade_token_to_token(ethereum_transaction_decoder, ethereum_accounts):
    """Test that trading token to token in curve is decoded correctly"""
    tx_hex = deserialize_evm_tx_hash('0xaa176ce742d62b663656572f8cc53d63d6c00cd2c3adde32293e4028a5e0693c ')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        database=ethereum_transaction_decoder.database,
        tx_hash=tx_hex,
    )
    expected_events = [
        EvmEvent(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1679546783000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('0.002265287178848788')),
            location_label=user_address,
            notes='Burned 0.002265287178848788 ETH for gas',
            counterparty='gas',
            address=None,
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=172,
            timestamp=TimestampMS(1679546783000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            balance=Balance(amount=FVal('500000')),
            location_label=user_address,
            notes='Swap 500000 USDC in curve',
            counterparty='curve',
            address=string_to_evm_address('0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7'),
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=173,
            timestamp=TimestampMS(1679546783000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7'),
            balance=Balance(amount=FVal('498538.169982')),
            location_label=user_address,
            notes='Receive 498538.169982 USDT as the result of a swap in curve',
            counterparty='curve',
            address=string_to_evm_address('0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x8a1B73A88E1854Dd3EeBEe4354Bd4DbA23861E3A']])
def test_curve_trade_eth_to_token(ethereum_transaction_decoder, ethereum_accounts):
    """Test that trading eth to token in curve is decoded correctly"""
    tx_hex = deserialize_evm_tx_hash('0x34d6674d8d46b8a6c546b04b4c748b82d42a688f562fe80a8d02e9180a684d09 ')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        database=ethereum_transaction_decoder.database,
        tx_hash=tx_hex,
    )
    expected_events = [
        EvmEvent(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1679225231000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('0.001727872677935233')),
            location_label=user_address,
            notes='Burned 0.001727872677935233 ETH for gas',
            counterparty='gas',
            address=None,
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1679225231000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('0.00008')),
            location_label=user_address,
            notes='Swap 0.00008 ETH in curve',
            counterparty='curve',
            address=string_to_evm_address('0xA96A65c051bF88B4095Ee1f2451C2A9d43F53Ae2'),
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=57,
            timestamp=TimestampMS(1679225231000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0xE95A203B1a91a908F9B9CE46459d101078c2c3cb'),
            balance=Balance(amount=FVal('0.000073629326233652')),
            location_label=user_address,
            notes='Receive 0.000073629326233652 ankrETH as the result of a swap in curve',  # noqa: E501
            counterparty='curve',
            address=string_to_evm_address('0xA96A65c051bF88B4095Ee1f2451C2A9d43F53Ae2'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x38abab9766e0b27d2912718a884292b8E7eb2803']])
def test_curve_trade_exchange_underlying(ethereum_transaction_decoder, ethereum_accounts):
    """Test that if exchange_underlying is happening the trade is decoded correctly"""
    tx_hex = deserialize_evm_tx_hash('0xed73e8717c9b2571a9cd7c0563e013c569e757920a050b1120ff1e6f5f3d3b8f ')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        database=ethereum_transaction_decoder.database,
        tx_hash=tx_hex,
    )
    expected_events = [
        EvmEvent(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1679482763000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('0.003678824742134973')),
            location_label=user_address,
            notes='Burned 0.003678824742134973 ETH for gas',
            counterparty='gas',
            address=None,
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=106,
            timestamp=TimestampMS(1679482763000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F'),
            balance=Balance(amount=FVal('9411.299859703624772744')),
            location_label=user_address,
            notes='Swap 9411.299859703624772744 DAI in curve',
            counterparty='curve',
            address=string_to_evm_address('0x8038C01A0390a8c547446a0b2c18fc9aEFEcc10c'),
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=110,
            timestamp=TimestampMS(1679482763000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0x5BC25f649fc4e26069dDF4cF4010F9f706c23831'),
            balance=Balance(amount=FVal('9495.240278199771455578')),
            location_label=user_address,
            notes='Receive 9495.240278199771455578 DUSD as the result of a swap in curve',  # noqa: E501
            counterparty='curve',
            address=string_to_evm_address('0x8038C01A0390a8c547446a0b2c18fc9aEFEcc10c'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x3Da232a0c0A5C59918D7B5fF77bf1c8Fc93aeE1B']])
def test_curve_swap_router(ethereum_transaction_decoder, ethereum_accounts):
    """Test that transactions made via curve swap router are decoded correctly"""
    tx_hex = deserialize_evm_tx_hash('0xd561728d989c4d8a25ca6708051cdb265dbc455927bb8c355083b790101487e9 ')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        database=ethereum_transaction_decoder.database,
        tx_hash=tx_hex,
    )
    expected_events = [
        EvmEvent(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1679550275000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('0.003261945529483024')),
            location_label=user_address,
            notes='Burned 0.003261945529483024 ETH for gas',
            counterparty='gas',
            address=None,
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1679550275000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('40')),
            location_label=user_address,
            notes='Swap 40 ETH in curve',
            counterparty='curve',
            address=string_to_evm_address('0x99a58482BD75cbab83b27EC03CA68fF489b5788f'),
        ), EvmEvent(
            event_identifier=evmhash,
            sequence_index=37,
            timestamp=TimestampMS(1679550275000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0xD533a949740bb3306d119CC777fa900bA034cd52'),
            balance=Balance(amount=FVal('73317.327157158562433931')),
            location_label=user_address,
            notes='Receive 73317.327157158562433931 CRV as the result of a swap in curve',  # noqa: E501
            counterparty='curve',
            address=string_to_evm_address('0x99a58482BD75cbab83b27EC03CA68fF489b5788f'),
        ),
    ]
    assert events == expected_events
