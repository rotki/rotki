from typing import TYPE_CHECKING, cast

import pytest

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.base.modules.curve.constants import CURVE_SWAP_ROUTER_NG
from rotkehlchen.chain.binance_sc.modules.curve.constants import (
    CURVE_SWAP_ROUTER_NG as CURVE_SWAP_ROUTER_NG_BSC,
)
from rotkehlchen.chain.ethereum.modules.curve.constants import (
    FEE_DISTRIBUTOR,
    GAUGE_BRIBE_V2,
    VOTING_ESCROW,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE, DEPOSIT_AND_STAKE_ZAP
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import (
    A_BSC_BNB,
    A_CRV,
    A_CRV_3CRV,
    A_DAI,
    A_ETH,
    A_LINK,
    A_POLYGON_POS_MATIC,
    A_USDC,
    A_USDT,
    A_XDAI,
)
from rotkehlchen.constants.misc import EXP18
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.fixtures.messages import MockedWsMessage
from rotkehlchen.tests.unit.decoders.test_zerox import A_POLYGON_POS_USDT
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    CURVE_POOL_PROTOCOL,
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
from rotkehlchen.utils.misc import timestamp_to_date

if TYPE_CHECKING:
    from rotkehlchen.chain.binance_sc.node_inquirer import BinanceSCInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('ethereum_accounts', [['0x57bF3B0f29E37619623994071C9e12091919675c']])
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
        input_data=hexstring_to_bytes('0x2b6e993a000000000000000000000000000000000000000000005512b9a6a672640100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000060c5f3590000000000000000000000000000000000000000000005255abbd43baa53603f90000000000000000000000000000000000000000000000000000000000000001'),
        nonce=599,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=370,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000005512b9a6a67264010000'),
                address=string_to_evm_address('0x6B175474E89094C44Da98b954EedeAC495271d0F'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x00000000000000000000000057bf3b0f29e37619623994071c9e12091919675c'),
                    hexstring_to_bytes('0x000000000000000000000000debf20617708857ebe4f679508e7b7863a8a8eee'),
                ],
            ), EvmTxReceiptLog(
                log_index=383,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000060c5f3590'),
                address=string_to_evm_address('0xdAC17F958D2ee523a2206206994597C13D831ec7'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x00000000000000000000000057bf3b0f29e37619623994071c9e12091919675c'),
                    hexstring_to_bytes('0x000000000000000000000000debf20617708857ebe4f679508e7b7863a8a8eee'),
                ],
            ), EvmTxReceiptLog(
                log_index=396,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000005328394d50efea7abaf4'),
                address=string_to_evm_address('0xFd2a8fA60Abd58Efe3EeE34dd494cD491dC14900'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000057bf3b0f29e37619623994071c9e12091919675c'),
                ],
            ), EvmTxReceiptLog(
                log_index=397,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000005512b9a6a672640100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000060c5f3590000000000000000000000000000000000000000000000002038eb27e79fe96ef0000000000000000000000000000000000000000000000000000000002e973710000000000000000000000000000000000000000000000000000000001832b050000000000000000000000000000000000000000002a38dd00eecdefe02a2fcf00000000000000000000000000000000000000000026c6b056a9a8e3b89d5717'),
                address=string_to_evm_address('0xDeBF20617708857ebe4F679508E7b7863a8A8EeE'),
                topics=[
                    hexstring_to_bytes('0x423f6495a08fc652425cf4ed0d1f9e37e571d9b9529b1c1c23cce780b2e7df0d'),
                    hexstring_to_bytes('0x00000000000000000000000057bf3b0f29e37619623994071c9e12091919675c'),
                ],
            ),
        ],
    )

    dbevmtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        ethereum_transaction_decoder.reload_data(cursor)
    events, _, _ = ethereum_transaction_decoder._decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )
    timestamp = TimestampMS(1650276061000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(0.00393701451),
            location_label=location_label,
            notes='Burn 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_DAI,
            amount=FVal('401746.57'),
            location_label=location_label,
            notes='Deposit 401746.57 DAI in curve pool 0xDeBF20617708857ebe4F679508E7b7863a8A8EeE',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xDeBF20617708857ebe4F679508E7b7863a8A8EeE'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_USDT,
            amount=FVal('25977.37'),
            location_label=location_label,
            notes='Deposit 25977.37 USDT in curve pool 0xDeBF20617708857ebe4F679508E7b7863a8A8EeE',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xDeBF20617708857ebe4F679508E7b7863a8A8EeE'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0xFd2a8fA60Abd58Efe3EeE34dd494cD491dC14900'),
            amount=FVal('392698.416886553664731892'),
            location_label=location_label,
            notes='Receive 392698.416886553664731892 a3CRV after depositing in curve pool 0xDeBF20617708857ebe4F679508E7b7863a8A8EeE',  # noqa: E501
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
        )]
    assert len(events) == 4
    assert events == expected_events


@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('ethereum_accounts', [['0x767B35b9F06F6e28e5ed05eE7C27bDf992eba5d2']])
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
        input_data=hexstring_to_bytes('0x0b4c7e4d00000000000000000000000000000000000000000000000002c68af0bb14000000000000000000000000000000000000000000000000000002c6526ca273a800000000000000000000000000000000000000000000000000054aaa619fda0c01'),
        nonce=5,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=412,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000002c6526ca273a800'),
                address=string_to_evm_address('0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000767b35b9f06f6e28e5ed05ee7c27bdf992eba5d2'),
                    hexstring_to_bytes('0x000000000000000000000000dc24316b9ae028f1497c275eb9192a3ea0f67022'),
                ],
            ), EvmTxReceiptLog(
                log_index=413,
                data=hexstring_to_bytes('0xfffffffffffffffffffffffffffffffffffffffffffffffffd39ad935d8c57ff'),
                address=string_to_evm_address('0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'),
                topics=[
                    hexstring_to_bytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'),
                    hexstring_to_bytes('0x000000000000000000000000767b35b9f06f6e28e5ed05ee7c27bdf992eba5d2'),
                    hexstring_to_bytes('0x000000000000000000000000dc24316b9ae028f1497c275eb9192a3ea0f67022'),
                ],
            ), EvmTxReceiptLog(
                log_index=414,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000005589f42020a37df'),
                address=string_to_evm_address('0x06325440D014e39736583c165C2963BA99fAf14E'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000767b35b9f06f6e28e5ed05ee7c27bdf992eba5d2'),
                ],
            ), EvmTxReceiptLog(
                log_index=415,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000002c68af0bb14000000000000000000000000000000000000000000000000000002c6526ca273a80000000000000000000000000000000000000000000000000000000016a92ed4ce00000000000000000000000000000000000000000000000000000016a9b386830000000000000000000000000000000000000000000156e4db21d9cf6a6d4f3f000000000000000000000000000000000000000000014a4959a6fb2bf53a7108'),
                address=string_to_evm_address('0xDC24316b9AE028F1497c275EB9192a3Ea0f67022'),
                topics=[
                    hexstring_to_bytes('0x26f55a85081d24974e85c6c00045d0f0453991e95873f52bff0d21af4079a768'),
                    hexstring_to_bytes('0x000000000000000000000000767b35b9f06f6e28e5ed05ee7c27bdf992eba5d2'),
                ],
            ),
        ],
    )

    dbevmtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        ethereum_transaction_decoder.reload_data(cursor)
    events, _, _ = ethereum_transaction_decoder._decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )
    timestamp = TimestampMS(1650276061000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(0.00393701451),
            location_label=location_label,
            notes='Burn 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=415,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=EvmToken('eip155:1/erc20:0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'),
            amount=FVal('115792089237316195423570985008687907853269984665640564039457.384070053129639935'),
            location_label=location_label,
            notes='Set stETH spending approval of 0x767B35b9F06F6e28e5ed05eE7C27bDf992eba5d2 by 0xDC24316b9AE028F1497c275EB9192a3Ea0f67022 to 115792089237316195423570985008687907853269984665640564039457.384070053129639935',  # noqa: E501
            address=string_to_evm_address('0xDC24316b9AE028F1497c275EB9192a3Ea0f67022'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=416,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal('0.2'),
            location_label=location_label,
            notes='Deposit 0.2 ETH in curve pool',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xDC24316b9AE028F1497c275EB9192a3Ea0f67022'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=417,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'),
            amount=FVal('0.19993786'),
            location_label=location_label,
            notes='Deposit 0.19993786 stETH in curve pool 0xDC24316b9AE028F1497c275EB9192a3Ea0f67022',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xDC24316b9AE028F1497c275EB9192a3Ea0f67022'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=418,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x06325440D014e39736583c165C2963BA99fAf14E'),
            amount=FVal('0.385232873991059423'),
            location_label=location_label,
            notes='Receive 0.385232873991059423 steCRV after depositing in curve pool 0xDC24316b9AE028F1497c275EB9192a3Ea0f67022',  # noqa: E501
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
        )]
    assert len(events) == 5
    assert events == expected_events


@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
@pytest.mark.parametrize('ethereum_accounts', [['0xDf9f0AE722A3919fE7f9cC8805773ef142007Ca6']])
def test_curve_remove_liquidity(
        database,
        ethereum_transaction_decoder,
) -> None:
    """Data for deposit taken from
    https://etherscan.io/tx/0xd63dccdbebeede3a1f50b97c0a8592255203a0559880b80377daa39f915741b0
    This tests uses the link pool to verify that withdrawals are correctly decoded
    """
    tx_hex = '0xd63dccdbebeede3a1f50b97c0a8592255203a0559880b80377daa39f915741b0'
    location_label = string_to_evm_address('0xDf9f0AE722A3919fE7f9cC8805773ef142007Ca6')
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1650276061),
        block_number=14608535,
        from_address=location_label,
        to_address=string_to_evm_address('0xF178C0b5Bb7e7aBF4e12A4838C7b7c5bA2C623c0'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x1a4d01d20000000000000000000000000000000000000000000000a8815561fefbe56aa300000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000a8d15fc942541fea7f'),
        nonce=5,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=506,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000a8815561fefbe56aa3'),
                address=string_to_evm_address('0xcee60cFa923170e4f8204AE08B4fA6A3F5656F3a'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000df9f0ae722a3919fe7f9cc8805773ef142007ca6'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=507,
                data=hexstring_to_bytes('0000000000000000000000000000000000000000000000a93078ae269dbeca10'),
                address=string_to_evm_address('0x514910771AF9Ca656af840dff83E8264EcF986CA'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000f178c0b5bb7e7abf4e12a4838c7b7c5ba2c623c0'),
                    hexstring_to_bytes('0x000000000000000000000000df9f0ae722a3919fe7f9cc8805773ef142007ca6'),
                ],
            ), EvmTxReceiptLog(
                log_index=508,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000a8815561fefbe56aa30000000000000000000000000000000000000000000000a93078ae269dbeca100000000000000000000000000000000000000000000092c009040e68c381c519'),
                address=string_to_evm_address('0xF178C0b5Bb7e7aBF4e12A4838C7b7c5bA2C623c0'),
                topics=[
                    hexstring_to_bytes('0x5ad056f2e28a8cec232015406b843668c1e36cda598127ec3b8c59b8c72773a0'),
                    hexstring_to_bytes('0x000000000000000000000000df9f0ae722a3919fe7f9cc8805773ef142007ca6'),
                ],
            ), EvmTxReceiptLog(
                log_index=415,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000002c68af0bb14000000000000000000000000000000000000000000000000000002c6526ca273a80000000000000000000000000000000000000000000000000000000016a92ed4ce00000000000000000000000000000000000000000000000000000016a9b386830000000000000000000000000000000000000000000156e4db21d9cf6a6d4f3f000000000000000000000000000000000000000000014a4959a6fb2bf53a7108'),
                address=string_to_evm_address('0xDC24316b9AE028F1497c275EB9192a3Ea0f67022'),
                topics=[
                    hexstring_to_bytes('0x26f55a85081d24974e85c6c00045d0f0453991e95873f52bff0d21af4079a768'),
                    hexstring_to_bytes('0x000000000000000000000000767b35b9f06f6e28e5ed05ee7c27bdf992eba5d2'),
                ],
            ),
        ],
    )

    dbevmtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        ethereum_transaction_decoder.reload_data(cursor)
    events, _, _ = ethereum_transaction_decoder._decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )
    mocked_notifier = database.msg_aggregator.rotki_notifier
    assert len(mocked_notifier.messages) == 0, 'There is no gauge action, so there should be no message to refresh balances'  # noqa: E501
    timestamp = TimestampMS(1650276061000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(0.00393701451),
            location_label=location_label,
            notes='Burn 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0xcee60cFa923170e4f8204AE08B4fA6A3F5656F3a'),
            amount=FVal('3108.372467134893484707'),
            location_label=location_label,
            notes='Return 3108.372467134893484707 linkCRV',
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_LINK,
            amount=FVal('3120.992481448818559504'),
            location_label=location_label,
            notes='Remove 3120.992481448818559504 LINK from 0xF178C0b5Bb7e7aBF4e12A4838C7b7c5bA2C623c0 curve pool',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xF178C0b5Bb7e7aBF4e12A4838C7b7c5bA2C623c0'),
        )]
    assert expected_events == events


@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('ethereum_accounts', [['0xa8005630caE7b7d2AFADD38FD3B3040d13cbE2BC']])
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
        input_data=hexstring_to_bytes('0x1a4d01d20000000000000000000000000000000000000000000000a8815561fefbe56aa300000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000a8d15fc942541fea7f'),
        nonce=5,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=191,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000dc335d474901e08'),
                address=string_to_evm_address('0x06325440D014e39736583c165C2963BA99fAf14E'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000a8005630cae7b7d2afadd38fd3b3040d13cbe2bc'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=192,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000dc335d474901e080000000000000000000000000000000000000000000000000e48d018621788fa'),
                address=string_to_evm_address('0xDC24316b9AE028F1497c275EB9192a3Ea0f67022'),
                topics=[
                    hexstring_to_bytes('0x9e96dd3b997a2a257eec4df9bb6eaf626e206df5f543bd963682d143300be310'),
                    hexstring_to_bytes('0x000000000000000000000000a8005630cae7b7d2afadd38fd3b3040d13cbe2bc'),
                ],
            ),
        ],
    )
    internal_tx = EvmInternalTransaction(
        parent_tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        trace_id=27,
        from_address=string_to_evm_address('0xDC24316b9AE028F1497c275EB9192a3Ea0f67022'),
        to_address=string_to_evm_address('0xa8005630caE7b7d2AFADD38FD3B3040d13cbE2BC'),
        value=FVal('1.02930131799766041') * EXP18,
    )
    dbevmtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        dbevmtx.add_evm_internal_transactions(cursor, [internal_tx], relevant_address=location_label)  # noqa: E501
        ethereum_transaction_decoder.reload_data(cursor)
    events, _, _ = ethereum_transaction_decoder._decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )
    timestamp = TimestampMS(1650276061000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(0.00393701451),
            location_label=location_label,
            notes='Burn 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x06325440D014e39736583c165C2963BA99fAf14E'),
            amount=FVal('0.991695529556581896'),
            location_label=location_label,
            notes='Return 0.991695529556581896 steCRV',
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_ETH,
            amount=FVal('1.02930131799766041'),
            location_label=location_label,
            notes='Remove 1.02930131799766041 ETH from the curve pool',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xDC24316b9AE028F1497c275EB9192a3Ea0f67022'),
        )]
    assert expected_events == events


@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('ethereum_accounts', [['0x2fac74A3a04B031F240923621a578724C40678af']])
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
        input_data=hexstring_to_bytes('0x517a55a300000000000000000000000000000000000000000000001fa9ee7266a543831f00000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000003f487c50000000000000000000000000000000000000000000000000000000000000001'),
        nonce=5,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=2183,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000001fa9ee7266a543831f'),
                address=string_to_evm_address('0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000002fac74a3a04b031f240923621a578724c40678af'),
                    hexstring_to_bytes('0x000000000000000000000000bbc81d23ea2c3ec7e56d39296f0cbb648873a5d3'),
                ],
            ), EvmTxReceiptLog(
                log_index=2184,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                address=string_to_evm_address('0x16de59092dAE5CcF4A1E6439D611fd0653f0Bd01'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x00000000000000000000000045f783cce6b7ff23b2ab2d70e416cdb7d6055f51'),
                    hexstring_to_bytes('0x000000000000000000000000bbc81d23ea2c3ec7e56d39296f0cbb648873a5d3'),
                ],
            ), EvmTxReceiptLog(
                log_index=2185,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000001fdb750a'),
                address=string_to_evm_address('0xd6aD7a6750A7593E092a9B218d66C0A814a3436e'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x00000000000000000000000045f783cce6b7ff23b2ab2d70e416cdb7d6055f51'),
                    hexstring_to_bytes('0x000000000000000000000000bbc81d23ea2c3ec7e56d39296f0cbb648873a5d3'),
                ],
            ), EvmTxReceiptLog(
                log_index=2186,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                address=string_to_evm_address('0x83f798e925BcD4017Eb265844FDDAbb448f1707D'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x00000000000000000000000045f783cce6b7ff23b2ab2d70e416cdb7d6055f51'),
                    hexstring_to_bytes('0x000000000000000000000000bbc81d23ea2c3ec7e56d39296f0cbb648873a5d3'),
                ],
            ), EvmTxReceiptLog(
                log_index=2187,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                address=string_to_evm_address('0x73a052500105205d34Daf004eAb301916DA8190f'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x00000000000000000000000045f783cce6b7ff23b2ab2d70e416cdb7d6055f51'),
                    hexstring_to_bytes('0x000000000000000000000000bbc81d23ea2c3ec7e56d39296f0cbb648873a5d3'),
                ],
            ), EvmTxReceiptLog(
                log_index=2188,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                address=string_to_evm_address('0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000bbc81d23ea2c3ec7e56d39296f0cbb648873a5d3'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=2189,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001fdb750a000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000045cf4bec2e53f0000000000000000000000000000000000000000000000000000000000000e07e000000000000000000000000000000000000000000000000000000000000570d0000000000000000000000000000000000000000000000000051077d9dc293100000000000000000000000000000000000000000000c740195f187122987a9ef0000000000000000000000000000000000000000000aeddccb3976328f7d90bd'),
                address=string_to_evm_address('0x45F783CCE6B7FF23B2ab2D70e416cdb7D6055f51'),
                topics=[
                    hexstring_to_bytes('0xb964b72f73f5ef5bf0fdc559b2fab9a7b12a39e47817a547f1f0aee47febd602'),
                    hexstring_to_bytes('0x000000000000000000000000bbc81d23ea2c3ec7e56d39296f0cbb648873a5d3'),
                    hexstring_to_bytes('0x000000000000000000000000bbc81d23ea2c3ec7e56d39296f0cbb648873a5d3'),
                ],
            ), EvmTxReceiptLog(
                log_index=2189,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000027a72df9'),
                address=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000bbc81d23ea2c3ec7e56d39296f0cbb648873a5d3'),
                    hexstring_to_bytes('0x0000000000000000000000002fac74a3a04b031f240923621a578724c40678af'),
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        ethereum_transaction_decoder.reload_data(cursor)
    events, _, _ = ethereum_transaction_decoder._decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )
    timestamp = TimestampMS(1650276061000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(0.00393701451),
            location_label=location_label,
            notes='Burn 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8'),
            amount=FVal('584.093916507047953183'),
            location_label=location_label,
            notes='Return 584.093916507047953183 yDAI+yUSDC+yUSDT+yTUSD',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xbBC81d23Ea2c3ec7e56D39296F0cbB648873a5d3'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_USDC,
            amount=FVal('665.267705'),
            location_label=location_label,
            notes='Remove 665.267705 USDC from 0x45F783CCE6B7FF23B2ab2D70e416cdb7D6055f51 curve pool',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xbBC81d23Ea2c3ec7e56D39296F0cbB648873a5d3'),
        )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('ethereum_accounts', [['0x6Bb553FFC5716782051f51b564Bb149D9946f0d2']])
def test_deposit_multiple_tokens(ethereum_transaction_decoder, ethereum_accounts, load_global_caches):  # noqa: E501
    """Check the case for a pool where multiple deposit events appear in the transaction"""
    tx_hex = deserialize_evm_tx_hash('0xe954a396a02ebbea45a1d206c9918f717c55509c8138fccc63155d0262ef4dc4 ')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=tx_hex,
        load_global_caches=load_global_caches,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1675186487000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.011180845456491718'),
            location_label=user_address,
            notes='Burn 0.011180845456491718 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1675186487000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_DAI,
            amount=FVal('10'),
            location_label=user_address,
            notes='Deposit 10 DAI in curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xA5407eAE9Ba41422680e2e00537571bcC53efBfD'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1675186487000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xC25a3A3b969415c80451098fa907EC722572917F'),
            amount=FVal('9.423568821947938716'),
            location_label=user_address,
            notes='Receive 9.423568821947938716 crvPlain3andSUSD after depositing in curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD',  # noqa: E501
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x66215D23B8A247C80c2D1B7beF4BefC2AB384bCE']])
def test_gauge_vote(ethereum_accounts, ethereum_transaction_decoder) -> None:
    tx_hex = deserialize_evm_tx_hash('0xf67308b01613b3f75a71f2a3cea198acc063c987f17be4aaf5505a1ad70751ef')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1685562071000)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=cast('EthereumInquirer', ethereum_transaction_decoder.evm_inquirer),
        tx_hash=tx_hex,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            amount=FVal('0.01847747115186684'),
            location_label=user_address,
            notes='Burn 0.01847747115186684 ETH for gas',
            counterparty='gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=191,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=Asset('ETH'),
            amount=ZERO,
            location_label=user_address,
            notes='Reset vote for 0x740BA8aa0052E07b925908B380248cb03f3DE5cB curve gauge',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x740BA8aa0052E07b925908B380248cb03f3DE5cB'),
            product=EvmProduct.GAUGE,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
@pytest.mark.parametrize('ethereum_accounts', [['0xd289986c25Ae3f4644949e25bC369e9d8e0caeaD']])
def test_gauge_deposit(
        ethereum_accounts,
        database,
        ethereum_transaction_decoder,
        load_global_caches,
) -> None:
    tx_hex = deserialize_evm_tx_hash('0x5ae70d68241d85feac65c90e4546154e232dba9fecad9036bcec10082acc9d46')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=cast('EthereumInquirer', ethereum_transaction_decoder.evm_inquirer),
        tx_hash=tx_hex,
        load_global_caches=load_global_caches,
    )
    mocked_notifier = database.msg_aggregator.rotki_notifier
    message = mocked_notifier.pop_message()
    assert message == MockedWsMessage(
        message_type=WSMessageType.REFRESH_BALANCES,
        data={
            'type': 'blockchain_balances',
            'blockchain': 'eth',
        },
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1679313731000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            amount=FVal('0.007333038632457846'),
            location_label=user_address,
            notes='Burn 0.007333038632457846 ETH for gas',
            counterparty='gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=200,
            timestamp=TimestampMS(1679313731000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:1/erc20:0xC25a3A3b969415c80451098fa907EC722572917F'),
            amount=FVal('7985.261401730774426743'),
            location_label=user_address,
            notes='Deposit 7985.261401730774426743 crvPlain3andSUSD into 0xA90996896660DEcC6E997655E065b23788857849 curve gauge',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xA90996896660DEcC6E997655E065b23788857849'),
            product=EvmProduct.GAUGE,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('ethereum_accounts', [['0xd80DF837766C8Edb6f11Bf7fD35703f87F2a31fB']])
def test_gauge_withdraw(ethereum_transaction_decoder, ethereum_accounts, load_global_caches):
    tx_hex = deserialize_evm_tx_hash('0x055fc6cafcdae6b367d934e9385816f89153314c5abc5d3659a65778c90342d2')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=tx_hex,
        load_global_caches=load_global_caches,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1679346575000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            amount=FVal('0.01157725763881742'),
            location_label=user_address,
            notes='Burn 0.01157725763881742 ETH for gas',
            counterparty='gas',
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=43,
            timestamp=TimestampMS(1679346575000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:1/erc20:0xC25a3A3b969415c80451098fa907EC722572917F'),
            amount=FVal('37939.72737243936267785'),
            location_label=user_address,
            notes='Withdraw 37939.72737243936267785 crvPlain3andSUSD from 0xA90996896660DEcC6E997655E065b23788857849 curve gauge',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xA90996896660DEcC6E997655E065b23788857849'),
            product=EvmProduct.GAUGE,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('ethereum_accounts', [['0x0E9Fed33f6a202146a615De0FA1985adFb461467']])
def test_gauge_claim_rewards(ethereum_transaction_decoder, ethereum_accounts, load_global_caches):
    tx_hex = deserialize_evm_tx_hash('0xe01bc48ddb3df6eb721c122c5ddaea705b771bfb8db407e3a96ae9bab6584453')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=tx_hex,
        load_global_caches=load_global_caches,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1679342423000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            amount=FVal('0.004486722780852585'),
            location_label=user_address,
            notes='Burn 0.004486722780852585 ETH for gas',
            counterparty='gas',
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=112,
            timestamp=TimestampMS(1679342423000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:1/erc20:0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F'),
            amount=FVal('0.451753537525671486'),
            location_label=user_address,
            notes='Receive 0.451753537525671486 SNX rewards from 0xA90996896660DEcC6E997655E065b23788857849 curve gauge',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xA90996896660DEcC6E997655E065b23788857849'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('ethereum_accounts', [['0xA8d7Fb04877C3FBf175DE76FA3D2fa66c770537F']])
def test_curve_trade_token_to_token(ethereum_transaction_decoder, ethereum_accounts, load_global_caches):  # noqa: E501
    """Test that trading token to token in curve is decoded correctly"""
    tx_hex = deserialize_evm_tx_hash('0xaa176ce742d62b663656572f8cc53d63d6c00cd2c3adde32293e4028a5e0693c ')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=tx_hex,
        load_global_caches=load_global_caches,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1679546783000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            amount=FVal('0.002265287178848788'),
            location_label=user_address,
            notes='Burn 0.002265287178848788 ETH for gas',
            counterparty='gas',
            address=None,
        ), EvmSwapEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1679546783000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            amount=FVal('500000'),
            location_label=user_address,
            notes='Swap 500000 USDC in curve',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7'),
        ), EvmSwapEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1679546783000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7'),
            amount=FVal('498538.169982'),
            location_label=user_address,
            notes='Receive 498538.169982 USDT as the result of a swap in curve',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('ethereum_accounts', [['0x8a1B73A88E1854Dd3EeBEe4354Bd4DbA23861E3A']])
def test_curve_trade_eth_to_token(ethereum_transaction_decoder, ethereum_accounts, load_global_caches):  # noqa: E501
    """Test that trading eth to token in curve is decoded correctly"""
    tx_hex = deserialize_evm_tx_hash('0x34d6674d8d46b8a6c546b04b4c748b82d42a688f562fe80a8d02e9180a684d09')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=tx_hex,
        load_global_caches=load_global_caches,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1679225231000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            amount=FVal('0.001727872677935233'),
            location_label=user_address,
            notes='Burn 0.001727872677935233 ETH for gas',
            counterparty='gas',
            address=None,
        ), EvmSwapEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1679225231000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('ETH'),
            amount=FVal('0.00008'),
            location_label=user_address,
            notes='Swap 0.00008 ETH in curve',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xA96A65c051bF88B4095Ee1f2451C2A9d43F53Ae2'),
        ), EvmSwapEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1679225231000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0xE95A203B1a91a908F9B9CE46459d101078c2c3cb'),
            amount=FVal('0.000073629326233652'),
            location_label=user_address,
            notes='Receive 0.000073629326233652 ankrETH as the result of a swap in curve',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xA96A65c051bF88B4095Ee1f2451C2A9d43F53Ae2'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('ethereum_accounts', [['0x38abab9766e0b27d2912718a884292b8E7eb2803']])
def test_curve_trade_exchange_underlying(ethereum_transaction_decoder, ethereum_accounts, load_global_caches):  # noqa: E501
    """Test that if exchange_underlying is happening the trade is decoded correctly"""
    tx_hex = deserialize_evm_tx_hash('0xed73e8717c9b2571a9cd7c0563e013c569e757920a050b1120ff1e6f5f3d3b8f ')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=tx_hex,
        load_global_caches=load_global_caches,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1679482763000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            amount=FVal('0.003678824742134973'),
            location_label=user_address,
            notes='Burn 0.003678824742134973 ETH for gas',
            counterparty='gas',
            address=None,
        ), EvmSwapEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1679482763000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F'),
            amount=FVal('9411.299859703624772744'),
            location_label=user_address,
            notes='Swap 9411.299859703624772744 DAI in curve',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x8038C01A0390a8c547446a0b2c18fc9aEFEcc10c'),
        ), EvmSwapEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1679482763000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0x5BC25f649fc4e26069dDF4cF4010F9f706c23831'),
            amount=FVal('9495.240278199771455578'),
            location_label=user_address,
            notes='Receive 9495.240278199771455578 DUSD as the result of a swap in curve',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x8038C01A0390a8c547446a0b2c18fc9aEFEcc10c'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x3Da232a0c0A5C59918D7B5fF77bf1c8Fc93aeE1B']])
def test_curve_swap_router(ethereum_transaction_decoder, ethereum_accounts):
    """Test that transactions made via curve swap router are decoded correctly"""
    tx_hex = deserialize_evm_tx_hash('0xd561728d989c4d8a25ca6708051cdb265dbc455927bb8c355083b790101487e9 ')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=tx_hex,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1679550275000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            amount=FVal('0.003261945529483024'),
            location_label=user_address,
            notes='Burn 0.003261945529483024 ETH for gas',
            counterparty='gas',
            address=None,
        ), EvmSwapEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1679550275000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('ETH'),
            amount=FVal('40'),
            location_label=user_address,
            notes='Swap 40 ETH in curve',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x99a58482BD75cbab83b27EC03CA68fF489b5788f'),
        ), EvmSwapEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1679550275000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0xD533a949740bb3306d119CC777fa900bA034cd52'),
            amount=FVal('73317.327157158562433931'),
            location_label=user_address,
            notes='Receive 73317.327157158562433931 CRV as the result of a swap in curve',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x99a58482BD75cbab83b27EC03CA68fF489b5788f'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('ethereum_accounts', [['0xdE206bC0Fde2eF5C8BB6A1d552a64F82A2407Be4']])
def test_curve_usdn_add_liquidity(ethereum_transaction_decoder, ethereum_accounts, load_global_caches):  # noqa: E501
    """Check that adding liquidity to a curve pool using the USDN contract is properly decoded."""
    tx_hex = deserialize_evm_tx_hash('0x6c28df56ae4a7f784577273f72402a9b6640024327ee952fdde72c9cfdf08da5')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=tx_hex,
        load_global_caches=load_global_caches,
    )
    timestamp = TimestampMS(Timestamp(1674470159000))
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.005672980418415474'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burn 0.005672980418415474 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_USDC,
            amount=FVal('761.396655'),
            location_label=user_address,
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x094d12e5b541784701FD8d65F11fc0598FBC6332'),
            notes='Deposit 761.396655 USDC in curve pool 0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7',  # noqa: E501
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0x4f3E8F405CF5aFC05D68142F3783bDfE13811522'),
            amount=FVal('2676.003172633078929284'),
            location_label=user_address,
            counterparty=CPT_CURVE,
            notes='Receive 2676.003172633078929284 usdn3CRV after depositing in a curve pool',
            address=string_to_evm_address('0x094d12e5b541784701FD8d65F11fc0598FBC6332'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('ethereum_accounts', [['0x6d84264A7bD2Cffa4A117BA2350403b3A9866949']])
def test_curve_usdn_remove_liquidity(ethereum_transaction_decoder, ethereum_accounts, load_global_caches):  # noqa: E501
    """Check that removing liquidity from a curve pool using the USDN contract is properly decoded."""  # noqa: E501
    tx_hex = deserialize_evm_tx_hash('0x4d77fba437b9dee6679dbb0f238b123f01b7b1bdd41bf46e35b00ce016cf8ab2')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=tx_hex,
        load_global_caches=load_global_caches,
    )
    timestamp = TimestampMS(Timestamp(1676708639000))
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.009847222'),
            location_label=user_address,
            notes='Burn 0.009847222 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0x4f3E8F405CF5aFC05D68142F3783bDfE13811522'),
            amount=FVal('22876.332126821513165437'),
            location_label=user_address,
            notes='Return 22876.332126821513165437 usdn3CRV',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x094d12e5b541784701FD8d65F11fc0598FBC6332'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:1/erc20:0x674C6Ad92Fd080e4004b2312b45f796a192D27a0'),
            amount=FVal('25186.906071469663867559'),
            location_label=user_address,
            notes='Remove 25186.906071469663867559 USDN from 0x0f9cb53Ebe405d49A0bbdBD291A65Ff571bC83e1 curve pool',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x094d12e5b541784701FD8d65F11fc0598FBC6332'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=235,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_DAI,
            amount=FVal('93.260120972251887648'),
            location_label=user_address,
            notes='Remove 93.260120972251887648 DAI from 0x0f9cb53Ebe405d49A0bbdBD291A65Ff571bC83e1 curve pool',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x094d12e5b541784701FD8d65F11fc0598FBC6332'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=236,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_USDC,
            amount=FVal('96.486847'),
            location_label=user_address,
            notes='Remove 96.486847 USDC from 0x0f9cb53Ebe405d49A0bbdBD291A65Ff571bC83e1 curve pool',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x094d12e5b541784701FD8d65F11fc0598FBC6332'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=237,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_USDT,
            amount=FVal('70.225535'),
            location_label=user_address,
            notes='Remove 70.225535 USDT from 0x0f9cb53Ebe405d49A0bbdBD291A65Ff571bC83e1 curve pool',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x094d12e5b541784701FD8d65F11fc0598FBC6332'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('ethereum_accounts', [['0xcbE942516AE7687d80a5fF94F8f9A203Be800713']])
def test_3pool_add_liquidity(ethereum_transaction_decoder, ethereum_accounts, load_global_caches):
    """Check that adding liquidity to a curve pool using the 3Pool zap contract is properly decoded."""  # noqa: E501
    tx_hex = deserialize_evm_tx_hash('0xf7c6764b832069785eeee22a078f4cb3c92149c25eb0bdc6bba36ebd1598c255')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=tx_hex,
        load_global_caches=load_global_caches,
    )
    timestamp = TimestampMS(1680503171000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.006158572854866488'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burn 0.006158572854866488 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_USDT,
            amount=FVal('200000'),
            location_label=user_address,
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xA79828DF1850E8a3A3064576f380D90aECDD3359'),
            notes='Deposit 200000 USDT in curve pool 0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xc270b3B858c335B6BA5D5b10e2Da8a09976005ad'),
            amount=FVal('195463.032550265720355345'),
            location_label=user_address,
            counterparty=CPT_CURVE,
            notes='Receive 195463.032550265720355345 pax-usdp3CRV-f after depositing in a curve pool',  # noqa: E501
            address=string_to_evm_address('0x0000000000000000000000000000000000000000'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('ethereum_accounts', [['0xC7BFb2ED20D14407C78cc1FC4a4Abe39f1964964']])
def test_3pool_remove_liquidity(ethereum_transaction_decoder, ethereum_accounts, load_global_caches):  # noqa: E501
    """Check that removing liquidity from a curve pool using the 3Pool zap contract is properly decoded."""  # noqa: E501
    tx_hex = deserialize_evm_tx_hash('0xbf4a445d0452e2f1e046c3ab3d10018c801e2acae89051c98332e9264f36d7f7')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=tx_hex,
        load_global_caches=load_global_caches,
    )
    timestamp = TimestampMS(1680390095000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.007508781310937599'),
            location_label=user_address,
            notes='Burn 0.007508781310937599 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0xe9123CBC5d1EA65301D417193c40A72Ac8D53501'),
            amount=FVal('95093.489007941270920107'),
            location_label=user_address,
            notes='Return 95093.489007941270920107 3CRVlvUSD3CRV-f',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xA79828DF1850E8a3A3064576f380D90aECDD3359'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:1/erc20:0x94A18d9FE00bab617fAD8B49b11e9F1f64Db6b36'),
            amount=FVal('56718.010997734097866656'),
            location_label=user_address,
            notes='Remove 56718.010997734097866656 lvUSD from 0xe9123CBC5d1EA65301D417193c40A72Ac8D53501 curve pool',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xA79828DF1850E8a3A3064576f380D90aECDD3359'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=50,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_DAI,
            amount=FVal('14119.166521016875857287'),
            location_label=user_address,
            notes='Remove 14119.166521016875857287 DAI from 0xe9123CBC5d1EA65301D417193c40A72Ac8D53501 curve pool',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xA79828DF1850E8a3A3064576f380D90aECDD3359'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=51,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_USDC,
            amount=FVal('16072.772093'),
            location_label=user_address,
            notes='Remove 16072.772093 USDC from 0xe9123CBC5d1EA65301D417193c40A72Ac8D53501 curve pool',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xA79828DF1850E8a3A3064576f380D90aECDD3359'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=52,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_USDT,
            amount=FVal('8326.299501'),
            location_label=user_address,
            notes='Remove 8326.299501 USDT from 0xe9123CBC5d1EA65301D417193c40A72Ac8D53501 curve pool',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xA79828DF1850E8a3A3064576f380D90aECDD3359'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('ethereum_accounts', [['0x60b0f1919cf4ee46d1A8D63428276512814de570']])
def test_remove_from_aave_pool(ethereum_transaction_decoder, ethereum_accounts, load_global_caches):  # noqa: E501
    """
    Test that if liquidity is removed from a pool with a(aave) tokens,
    the events are decoded correctly.
    """
    tx_hex = deserialize_evm_tx_hash('0xb0a45bc41a83b2bdf2e06b9913a2e4c8b0d7f3080030807a0a06f301287424e9')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=tx_hex,
        load_global_caches=load_global_caches,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1682041175000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            amount=FVal('0.01441418456991474'),
            location_label=user_address,
            notes='Burn 0.01441418456991474 ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1682041175000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0xFd2a8fA60Abd58Efe3EeE34dd494cD491dC14900'),
            amount=FVal('2619.297635390037009904'),
            location_label=user_address,
            notes='Return 2619.297635390037009904 a3CRV',
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1682041175000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F'),
            amount=FVal('2904.458947543711333839'),
            location_label=user_address,
            notes='Remove 2904.458947543711333839 DAI from 0xDeBF20617708857ebe4F679508E7b7863a8A8EeE curve pool',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x028171bCA77440897B824Ca71D1c56caC55b68A3'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('ethereum_accounts', [['0x0550bED1C94AFBd468aa739852632D7e9b4c2F86']])
def test_deposit_via_zap_in_metapool(ethereum_transaction_decoder, ethereum_accounts, load_global_caches):  # noqa: E501
    """
    Test that deposits via a zap to a metapool (when there are 2 AddLiquidity events emitted)
    are decoded correctly.
    """
    tx_hex = deserialize_evm_tx_hash('0x3e39ef142826b80da629023bdbdbee77fcc7402d5845f92507c60c404f4441b8')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=tx_hex,
        load_global_caches=load_global_caches,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1683177731000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            amount=FVal('0.01900328031277868'),
            location_label=user_address,
            notes='Burn 0.01900328031277868 ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1683177731000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F'),
            amount=FVal('0.000116887772996936'),
            location_label=user_address,
            notes='Deposit 0.000116887772996936 DAI in curve pool 0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xA79828DF1850E8a3A3064576f380D90aECDD3359'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1683177731000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            amount=FVal('960'),
            location_label=user_address,
            notes='Deposit 960 USDC in curve pool 0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xA79828DF1850E8a3A3064576f380D90aECDD3359'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=3,
            timestamp=TimestampMS(1683177731000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xe9123CBC5d1EA65301D417193c40A72Ac8D53501'),
            amount=FVal('958.206985908299016385'),
            location_label=user_address,
            notes='Receive 958.206985908299016385 3CRVlvUSD3CRV-f after depositing in a curve pool',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x0000000000000000000000000000000000000000'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('ethereum_accounts', [['0xd381e358d6b4E176559D3D76109985ED83259aEC']])
def test_no_zap_event(ethereum_transaction_decoder, ethereum_accounts, load_global_caches):
    """
    Checks that if a curve zap is used, but there is no zap-specific event emitted (only event from
    the used pool is emitted), transaction is still decoded correctly.
    """
    tx_hex = deserialize_evm_tx_hash('0xc8617f0adcd6273c522359a244bb6908f8ea9232879884d572fd64d5b33e5e83 ')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=evmhash,
        load_global_caches=load_global_caches,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1683629339000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.010742095846323672'),
            location_label=user_address,
            notes='Burn 0.010742095846323672 ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=112,
            timestamp=TimestampMS(1683629339000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0x5a6A4D54456819380173272A5E8E9B9904BdF41B'),
            amount=FVal('44107.783344489319243346'),
            location_label=user_address,
            notes='Return 44107.783344489319243346 MIM-3LP3CRV-f',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xA79828DF1850E8a3A3064576f380D90aECDD3359'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=114,
            timestamp=TimestampMS(1683629339000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:1/erc20:0x99D8a9C45b2ecA8864373A26D1459e3Dff1e17F3'),
            amount=FVal('44587.625561888235283247'),
            location_label=user_address,
            notes='Remove 44587.625561888235283247 MIM from 0x5a6A4D54456819380173272A5E8E9B9904BdF41B curve pool',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x5a6A4D54456819380173272A5E8E9B9904BdF41B'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x1d5E65a087eBc3d03a294412E46CE5D6882969f4']])
def test_gauge_bribe_v2(ethereum_transaction_decoder, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x5ac0cf3073b0c6c722b17d08d56cc1d9064717405d7e23b1f92e5a8c88e647e1')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=tx_hex,
    )
    user_address, timestamp, gas, amount = ethereum_accounts[0], TimestampMS(1680736307000), '0.007331605001682333', '14.752122471808652238'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=288,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_CRV,
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Claim {amount} CRV as veCRV voting bribe',
            counterparty=CPT_CURVE,
            address=GAUGE_BRIBE_V2,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x1c362DFE864a4c4b3311eC97bf0b8320CB0a4952']])
def test_curve_deposit_polygon(polygon_pos_inquirer, polygon_pos_accounts, load_global_caches):
    tx_hash = deserialize_evm_tx_hash('0x6cb9d7ceb55a1063c17b58cb643e699525ca6037e711c34283cf0f3d6e81716e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    timestamp, pool_address, deposit_amount, approve_amount, received_amount, gas_fees = TimestampMS(1718015936000), string_to_evm_address('0x445FE580eF8d70FF569aB36e80c647af338db351'), '2.12', '0.88', '1.87538744644899407', '0.0127938000149261'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_POLYGON_POS_MATIC,
            amount=FVal(gas_fees),
            location_label=polygon_pos_accounts[0],
            notes=f'Burn {gas_fees} POL for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2482,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_POLYGON_POS_USDT,
            amount=FVal(approve_amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Set USDT spending approval of {polygon_pos_accounts[0]} by {pool_address} to {approve_amount}',  # noqa: E501
            address=pool_address,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2483,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_POLYGON_POS_USDT,
            amount=FVal(deposit_amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Deposit {deposit_amount} USDT in curve pool {pool_address}',
            counterparty=CPT_CURVE,
            address=string_to_evm_address(pool_address),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2484,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:137/erc20:0xE7a24EF0C5e95Ffb0f6684b813A78F2a3AD7D171'),
            amount=FVal(received_amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Receive {received_amount} am3CRV after depositing in curve pool {pool_address}',  # noqa: E501
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('optimism_accounts', [['0x1CD90D091C5c13Bb7e7612a90485C6F38B826Fdd']])
def test_gauge_deposit_optimism(database, optimism_inquirer, optimism_accounts, load_global_caches):  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x271f5ee9fddc8e2a2df4187f70b6192acb42661a7d35e934fa68d8778b196c71')  # noqa: E501
    timestamp, gauge_address, deposit_amount, gas_fees = TimestampMS(1718022201000), string_to_evm_address('0xB280fab4817C54796F9E6147aa1ad0198CFEfb41'), '218.705051991330164886', '0.000020026564634882'  # noqa: E501
    get_or_create_evm_token(  # gauge token should already exist in db by reloading cache tokens
        userdb=database,
        evm_address=gauge_address,
        chain_id=optimism_inquirer.chain_id,
        token_kind=EvmTokenKind.ERC20,
        evm_inquirer=optimism_inquirer,
        protocol=CURVE_POOL_PROTOCOL,
    )
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:10/erc20:0xd8dD9a8b2AcA88E68c46aF9008259d0EC04b7751'),
            amount=FVal(deposit_amount),
            location_label=optimism_accounts[0],
            notes=f'Deposit {deposit_amount} 3CRV-OP into {gauge_address} curve gauge',
            counterparty=CPT_CURVE,
            address=string_to_evm_address(gauge_address),
            product=EvmProduct.GAUGE,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset(f'eip155:10/erc20:{gauge_address}'),
            amount=FVal(deposit_amount),
            location_label=optimism_accounts[0],
            notes=f'Receive {deposit_amount} 3CRV-OP-gauge after depositing in {gauge_address} curve gauge',  # noqa: E501
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('gnosis_accounts', [['0xD4f9FE0039Da59e6DDb21bbb6E84e0C9e83D73eD']])
def test_gauge_withdraw_gnosis(database, gnosis_inquirer, gnosis_accounts, load_global_caches):
    tx_hash = deserialize_evm_tx_hash('0x29d1b4a219dfb19562a3915191e6bcc64652ff072daf56216e40267408860474')  # noqa: E501
    timestamp, gauge_address, withdraw_amount, gas_fees = TimestampMS(1717896445000), string_to_evm_address('0x05cd911eE9B60C28FCEE4ea03Cc5670637D955B1'), '19576.247352101772081083', '0.000196106001764954'  # noqa: E501
    get_or_create_evm_token(  # gauge token should already exist in db by reloading cache tokens
        userdb=database,
        evm_address=gauge_address,
        chain_id=gnosis_inquirer.chain_id,
        token_kind=EvmTokenKind.ERC20,
        evm_inquirer=gnosis_inquirer,
        protocol=CURVE_POOL_PROTOCOL,
    )
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_fees),
            location_label=gnosis_accounts[0],
            notes=f'Burn {gas_fees} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset(f'eip155:100/erc20:{gauge_address}'),
            amount=FVal(withdraw_amount),
            location_label=gnosis_accounts[0],
            notes=f'Return {withdraw_amount} crvUSDsDAI-gauge after withdrawing from {gauge_address} curve gauge',  # noqa: E501
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:100/erc20:0x0c8FA74c7b2De5a92B39217DC98D2D609439a2e5'),
            amount=FVal(withdraw_amount),
            location_label=gnosis_accounts[0],
            notes=f'Withdraw {withdraw_amount} crvUSDsDAI from {gauge_address} curve gauge',
            counterparty=CPT_CURVE,
            address=string_to_evm_address(gauge_address),
            product=EvmProduct.GAUGE,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('base_accounts', [['0x4113a3CB9004E193E9906131B632e280F5f9B61e']])
def test_curve_swap_router_base(base_inquirer, base_accounts):
    """Test that transactions made via the new curve swap router are decoded correctly"""
    tx_hash = deserialize_evm_tx_hash('0x6fee2438337aefe297a69d4361ff4d743865ef7fce6637e9e3e544af0c19184f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    timestamp, swap_amount, receive_amount, gas_fees = TimestampMS(1718096041000), '0.01702', '59.996794', '0.000001665983350053'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal(swap_amount),
            location_label=base_accounts[0],
            notes=f'Swap {swap_amount} ETH in curve',
            counterparty=CPT_CURVE,
            address=string_to_evm_address(CURVE_SWAP_ROUTER_NG),
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),
            amount=FVal(receive_amount),
            location_label=base_accounts[0],
            notes=f'Receive {receive_amount} USDC as the result of a swap in curve',
            counterparty=CPT_CURVE,
            address=string_to_evm_address(CURVE_SWAP_ROUTER_NG),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x8800AcEDF5571F35675CF8Aa1E3C16C7A8da0088']])
def test_deposit_via_zap_arbitrum(arbitrum_one_inquirer, arbitrum_one_accounts, load_global_caches):  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x5a72b9be1302cc4b9e1d79e61134b0b7f225b3a4aa723c27c557a672c29791ce')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    timestamp, pool_address, approve_amount, deposit_amount, receive_amount, gas_fees = TimestampMS(1718104329000), string_to_evm_address('0x73aF1150F265419Ef8a5DB41908B700C32D49135'), '115792089237316195423570985008687907853269984665640564039457584007877854.731259', '10000', '10003.6614101799549838', '0.0000058597'  # noqa: E501
    arbitrum_usdt = Asset('eip155:42161/erc20:0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9')
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=8,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=arbitrum_usdt,
            amount=FVal(approve_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Set USDT spending approval of {arbitrum_one_accounts[0]} by {DEPOSIT_AND_STAKE_ZAP} to {approve_amount}',  # noqa: E501
            address=DEPOSIT_AND_STAKE_ZAP,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=9,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=arbitrum_usdt,
            amount=FVal(deposit_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Deposit {deposit_amount} USDT in curve pool {pool_address}',
            counterparty=CPT_CURVE,
            address=string_to_evm_address(DEPOSIT_AND_STAKE_ZAP),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=10,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:42161/erc20:0x030786336Bc7833D4325404A25FE451e4fde9807'),
            amount=FVal(receive_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Receive {receive_amount} crvUSDT-gauge after depositing in a curve pool',
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x5e216ceCB65E1E1B86fE8C46c730af287c4492Dc']])
def test_fee_distributor(ethereum_transaction_decoder, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0xae8a3781fc8f8b032f4e14db7745f9e4297f61e58a3deebc93d55ef4ed99d728')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=tx_hex,
    )
    user_address, timestamp, gas, amount = ethereum_accounts[0], TimestampMS(1697289611000), '0.002010414684866136', '112.875618618497828084'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=123,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_CRV_3CRV,
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Claim {amount} 3CRV as part of curve fees distribution',
            counterparty=CPT_CURVE,
            address=FEE_DISTRIBUTOR,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x510B0068C0756bBEFCBaffB6567e467d661291FE']])
def test_vote_escrow_deposit(ethereum_transaction_decoder, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x2675807cf1950b8a8fbd64e1a0fe0ec3b894ba88fbb8e544ddf279aff12c6d55')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=tx_hex,
    )
    user_address, timestamp, gas, amount, locktime = ethereum_accounts[0], TimestampMS(1671946199000), '0.002774219663106188', '128.808146476393839874', Timestamp(1778112000)  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=150,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_CRV,
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Lock {amount} CRV in vote escrow until {timestamp_to_date(locktime, formatstr="%d/%m/%Y %H:%M:%S")}',  # noqa: E501
            counterparty=CPT_CURVE,
            address=VOTING_ESCROW,
            extra_data={'locktime': 1778112000},
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x3142A7Cb03dB13419884b275f61f8542C8850174']])
def test_vote_escrow_withdraw(ethereum_transaction_decoder, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x5bae0df2aeedc70f82488e8b19030c39d782cd5f58ca66155a5347320c4349a5')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=tx_hex,
    )
    user_address, timestamp, gas, amount = ethereum_accounts[0], TimestampMS(1671887987000), '0.002702199385335098', '1.872144205854855426'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=220,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_CRV,
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Withdraw {amount} CRV from vote escrow',
            counterparty=CPT_CURVE,
            address=VOTING_ESCROW,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('gnosis_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_gauge_deposit_and_stake(gnosis_inquirer, gnosis_accounts, load_global_caches):
    tx_hash = deserialize_evm_tx_hash('0x52141e28c55744cdfddaa1ab5614642f61459d7624a51981e21ec06176c8f65c')  # noqa: E501
    timestamp, gauge_address, deposited_amount, gas_fees, received_amount = TimestampMS(1717744880000), string_to_evm_address('0xd91770E868c7471a9585d1819143063A40c54D00'), '834.517942394847767492', '0.0023483922', '431.905365995549947348'  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_fees),
            location_label=gnosis_accounts[0],
            notes=f'Burn {gas_fees} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:100/erc20:0xcB444e90D8198415266c6a2724b7900fb12FC56E'),
            amount=FVal(deposited_amount),
            location_label=gnosis_accounts[0],
            notes=f'Deposit {deposited_amount} EURe into {gauge_address} curve gauge',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x37c5ab57AF7100Bdc9B668d766e193CCbF6614FD'),
            product=EvmProduct.GAUGE,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset(f'eip155:100/erc20:{gauge_address}'),
            amount=FVal(received_amount),
            location_label=gnosis_accounts[0],
            notes=f'Receive {received_amount} crvEUReUSD-gauge after depositing in {gauge_address} curve gauge',  # noqa: E501
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('gnosis_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_gauge_deposit_and_stake_multiple(gnosis_inquirer, gnosis_accounts, load_global_caches):
    tx_hash = deserialize_evm_tx_hash('0xcbeaaee59405d5f7fd456dc510f1b841cc1329cd9624255ce64c894ac6643bd7')  # noqa: E501
    timestamp, gauge_address, gas_fees, received_amount = TimestampMS(1719684750000), string_to_evm_address('0xd91770E868c7471a9585d1819143063A40c54D00'), '0.0023626991', '0.567442277824060065'  # noqa: E501
    deposited_eur, deposited_usdc = '0.551864219634212696', '0.593161'
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_fees),
            location_label=gnosis_accounts[0],
            notes=f'Burn {gas_fees} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:100/erc20:0xcB444e90D8198415266c6a2724b7900fb12FC56E'),
            amount=FVal(deposited_eur),
            location_label=gnosis_accounts[0],
            notes=f'Deposit {deposited_eur} EURe into {gauge_address} curve gauge',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x37c5ab57AF7100Bdc9B668d766e193CCbF6614FD'),
            product=EvmProduct.GAUGE,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:100/erc20:0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83'),
            amount=FVal(deposited_usdc),
            location_label=gnosis_accounts[0],
            notes=f'Deposit {deposited_usdc} USDC into {gauge_address} curve gauge',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x37c5ab57AF7100Bdc9B668d766e193CCbF6614FD'),
            product=EvmProduct.GAUGE,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset(f'eip155:100/erc20:{gauge_address}'),
            amount=FVal(received_amount),
            location_label=gnosis_accounts[0],
            notes=f'Receive {received_amount} crvEUReUSD-gauge after depositing in {gauge_address} curve gauge',  # noqa: E501
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('gnosis_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_liquidity_withdrawal(gnosis_inquirer, gnosis_accounts, load_global_caches):
    """Test that a withdrawal in the case of pools that have underlying pools
    is correctly decoded"""
    tx_hash = deserialize_evm_tx_hash('0x7645bfeb43a1ccacd3f8eb29c496823bd73586498ff7b79be5a3a48145f1c4b4')  # noqa: E501
    timestamp, pool_address, gas_fees, removed_amount, returned_amount = TimestampMS(1719046465000), string_to_evm_address('0x0CA1C1eC4EBf3CC67a9f545fF90a3795b318cA4a'), '0.000813878', '1656.600276747801451581', '850'  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_fees),
            location_label=gnosis_accounts[0],
            notes=f'Burn {gas_fees} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset(f'eip155:100/erc20:{pool_address}'),
            amount=FVal(returned_amount),
            location_label=gnosis_accounts[0],
            notes=f'Return {returned_amount} crvEUReUSD',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xE3FFF29d4DC930EBb787FeCd49Ee5963DADf60b6'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:100/erc20:0xcB444e90D8198415266c6a2724b7900fb12FC56E'),
            amount=FVal(removed_amount),
            location_label=gnosis_accounts[0],
            notes=f'Remove {removed_amount} EURe from 0x056C6C5e684CeC248635eD86033378Cc444459B0 curve pool',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xE3FFF29d4DC930EBb787FeCd49Ee5963DADf60b6'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('gnosis_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_monerium_eure_v2(gnosis_inquirer, gnosis_accounts, load_global_caches):
    """Regression test for https://github.com/rotki/rotki/issues/8452
    This test pulls a transaction after the deployment of the monerium v2 contracts
    and checks that we ignore correctly the log events emitted by the v1 contract.
    """
    tx_hash = deserialize_evm_tx_hash('0x1a2f03a1d89bb9ac019e6445c6d30ab32d85ca8e45ecbdf33d026700de5f7103')  # noqa: E501
    timestamp, pool_address, gas_fees, removed_amount, returned_amount = TimestampMS(1724679110000), string_to_evm_address('0x0CA1C1eC4EBf3CC67a9f545fF90a3795b318cA4a'), '0.0004379778', '0.019043275513941527', '0.01'  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_fees),
            location_label=gnosis_accounts[0],
            notes=f'Burn {gas_fees} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset(f'eip155:100/erc20:{pool_address}'),
            amount=FVal(returned_amount),
            location_label=gnosis_accounts[0],
            notes=f'Return {returned_amount} crvEUReUSD',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xE3FFF29d4DC930EBb787FeCd49Ee5963DADf60b6'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=11,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:100/erc20:0x420CA0f9B9b604cE0fd9C18EF134C705e5Fa3430'),
            amount=FVal(removed_amount),
            location_label=gnosis_accounts[0],
            notes=f'Remove {removed_amount} EURe from 0x056C6C5e684CeC248635eD86033378Cc444459B0 curve pool',  # noqa: E501
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xE3FFF29d4DC930EBb787FeCd49Ee5963DADf60b6'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('gnosis_accounts', [['0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF']])
def test_deposit_order(gnosis_inquirer, gnosis_accounts, load_global_caches):
    """Ensure that multiple deposits when depositing and staking keep the correct order.
    This is a regression test for an issue where the approval was in between the other deposits.
    """
    tx_hash = deserialize_evm_tx_hash('0x2b2999cee4447d27e27abe7ad926c12a875e296ddc4ad7af77ff52b13e74d39f')  # noqa: E501
    timestamp, deposited_eure, deposited_usdc, gas_fees, received_amount, user, contract = TimestampMS(1735459260000), '2.234019807771402726', '1.580616', '0.0011870912', '1.902024272971248158', gnosis_accounts[0], string_to_evm_address('0x37c5ab57AF7100Bdc9B668d766e193CCbF6614FD')  # noqa: E501
    gauge_address = string_to_evm_address('0xd91770E868c7471a9585d1819143063A40c54D00')
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )

    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_fees),
            location_label=gnosis_accounts[0],
            notes=f'Burn {gas_fees} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=9,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=EvmToken('eip155:100/erc20:0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83'),
            amount=FVal('8.419384'),
            location_label=gnosis_accounts[0],
            notes=(
                f'Set USDC spending approval of {user} by '
                f'{contract} to 8.419384'
            ),
            address=contract,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=11,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:100/erc20:0x420CA0f9B9b604cE0fd9C18EF134C705e5Fa3430'),
            amount=FVal(deposited_eure),
            location_label=gnosis_accounts[0],
            notes=f'Deposit {deposited_eure} EURe into {gauge_address} curve gauge',
            counterparty=CPT_CURVE,
            address=contract,
            product=EvmProduct.GAUGE,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=12,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:100/erc20:0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83'),
            amount=FVal(deposited_usdc),
            location_label=gnosis_accounts[0],
            notes=f'Deposit {deposited_usdc} USDC into {gauge_address} curve gauge',
            counterparty=CPT_CURVE,
            address=contract,
            product=EvmProduct.GAUGE,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=13,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset(f'eip155:100/erc20:{gauge_address}'),
            amount=FVal(received_amount),
            location_label=gnosis_accounts[0],
            notes=f'Receive {received_amount} crvEUReUSD-gauge after depositing in {gauge_address} curve gauge',  # noqa: E501
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('binance_sc_accounts', [['0x1b414E1977EAA94FA57c3e669683769aD19E88D5']])
def test_curve_swap_router_binance_sc(
        binance_sc_inquirer: 'BinanceSCInquirer',
        binance_sc_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x79bda33cfae80c8d7b26def223f409e54cfddc33ec7e009523fb5bc708e85042')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=binance_sc_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, gas_amount, swap_amount, receive_amount = binance_sc_accounts[0], TimestampMS(1735287841000), '0.000226961', '50.400357174206099256', '50.337143372227800304'  # noqa: E501
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
        sequence_index=77,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=a_bsc_usd,
        amount=ZERO,
        location_label=user_address,
        notes=f'Revoke BSC-USD spending approval of {user_address} by {CURVE_SWAP_ROUTER_NG_BSC}',
        address=CURVE_SWAP_ROUTER_NG_BSC,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=78,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.SPEND,
        asset=a_bsc_usd,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} BSC-USD in curve',
        counterparty=CPT_CURVE,
        address=CURVE_SWAP_ROUTER_NG_BSC,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=79,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:56/erc20:0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d'),
        amount=FVal(receive_amount),
        location_label=user_address,
        notes=f'Receive {receive_amount} USDC as the result of a swap in curve',
        counterparty=CPT_CURVE,
        address=CURVE_SWAP_ROUTER_NG_BSC,
    )]
