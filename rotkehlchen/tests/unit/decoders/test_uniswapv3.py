import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
from rotkehlchen.chain.ethereum.modules.uniswap.constants import CPT_UNISWAP_V3
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USDC
from rotkehlchen.constants.misc import EXP18, ZERO
from rotkehlchen.constants.resolver import ethaddress_to_identifier
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

ADDY = string_to_evm_address('0xb63e0C506dDBa7b0dd106d1937d6D13BE2C62aE2')
ADDY_2 = string_to_evm_address('0xeB312F4921aEbbE99faCaCFE92f22b942Cbd7599')
ADDY_3 = string_to_evm_address('0xdD84Ce1aDcb3A4908Db61A1dFA3353C3974c5a2B')
ADDY_4 = string_to_evm_address('0x354304234329A8d2425965C647e701A72d3438e5')
ADDY_5 = string_to_evm_address('0xa931b486F661540c6D709aE6DfC8BcEF347ea437')


@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_uniswap_v3_swap(database, ethereum_inquirer, eth_transactions):
    """
    Data for swap
    https://etherscan.io/tx/0x1c50c336329a7ee41f722ce5d848ebd066b72bf44a1eaafcaa92e8c0282049d2
    """
    tx_hex = '0x1c50c336329a7ee41f722ce5d848ebd066b72bf44a1eaafcaa92e8c0282049d2'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1646375440),
        block_number=14351442,
        from_address=ADDY,
        to_address='0xE592427A0AEce92De3Edee1F18E0157C05861564',
        value=632989659350357136,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xac9650d800000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000001800000000000000000000000000000000000000000000000000000000000000104db3e2198000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc20000000000000000000000005a98fcbea516cf06857215779fd812ca3bef1b320000000000000000000000000000000000000000000000000000000000002710000000000000000000000000b63e0c506ddba7b0dd106d1937d6d13be2c62ae2000000000000000000000000000000000000000000000000000000006183617400000000000000000000000000000000000000000000003635c9adc5dea0000000000000000000000000000000000000000000000000000008d4133ec308af39000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000412210e8a00000000000000000000000000000000000000000000000000000000'),  # noqa: E501
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
                log_index=485,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000003635c9adc5dea00000'),  # noqa: E501
                address=string_to_evm_address('0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000f4ad61db72f114be877e87d62dc5e7bd52df4d9b'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000b63e0c506ddba7b0dd106d1937d6d13be2c62ae2'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=486,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000008c8d4bdd012d490'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000e592427a0aece92de3edee1f18e0157c05861564'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=487,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000008c8d4bdd012d490'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000e592427a0aece92de3edee1f18e0157c05861564'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000f4ad61db72f114be877e87d62dc5e7bd52df4d9b'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=488,
                data=hexstring_to_bytes('0xffffffffffffffffffffffffffffffffffffffffffffffc9ca36523a2160000000000000000000000000000000000000000000000000000008c8d4bdd012d4900000000000000000000000000000000000000000066b7e70be499b45db3d11c000000000000000000000000000000000000000000000017d945bc30daf7e2f36fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffee008'),  # noqa: E501
                address=string_to_evm_address('0xf4aD61dB72f114Be877E87d62DC5e7bd52DF4d9B'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000e592427a0aece92de3edee1f18e0157c05861564'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000b63e0c506ddba7b0dd106d1937d6d13be2c62ae2'),  # noqa: E501
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
    events = decoder.decode_transaction(transaction=transaction, tx_receipt=receipt)

    assert len(events) == 3
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1646375440000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.00393701451),
                usd_value=ZERO,
            ),
            location_label=ADDY,
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1646375440000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.632989659350357136'), usd_value=ZERO),
            location_label=ADDY,
            notes='Swap 0.632989659350357136 ETH via uniswap-v3 auto router',
            counterparty=CPT_UNISWAP_V3,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1646375440000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'),
            balance=Balance(amount=FVal('1000')),
            location_label=ADDY,
            notes=f'Receive 1000 LDO as the result of a swap via {CPT_UNISWAP_V3} auto router',
            counterparty=CPT_UNISWAP_V3,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[ADDY_2]])
def test_uniswap_v3_swap_received_token2(database, ethereum_inquirer, eth_transactions):
    """This test checks that the logic is correct when the asset leaving the pool is the token2 of
    the pool. Data for swap
    https://etherscan.io/tx/0x116b3a9c0b2a4857605e336438c8e4c91897a9ef2af23178f9dbceba85264bd9
    """
    tx_hex = '0x116b3a9c0b2a4857605e336438c8e4c91897a9ef2af23178f9dbceba85264bd9'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1646375440),
        block_number=14351442,
        from_address=ADDY_2,
        to_address='0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45',
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x5ae401dc00000000000000000000000000000000000000000000000000000000631874d50000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000000300000000000000000000000000000000000000000000000000000000000000600000000000000000000000000000000000000000000000000000000000000160000000000000000000000000000000000000000000000000000000000000028000000000000000000000000000000000000000000000000000000000000000c4f3995c67000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb480000000000000000000000000000000000000000000000000000001176592e000000000000000000000000000000000000000000000000000000000063187985000000000000000000000000000000000000000000000000000000000000001bb850a14eb4c0a7d78d7a3642fe3f3290836732a8919f3f2547e6e106213d81cc1e77ab122e55948575792e4c6d1acdb7a601c49669fda898a1df74d225ba5b580000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000e404e45aaf000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc200000000000000000000000000000000000000000000000000000000000001f400000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000001176592e00000000000000000000000000000000000000000000000002ab8909ff4256bf68000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004449404b7c000000000000000000000000000000000000000000000002ab8909ff4256bf68000000000000000000000000eb312f4921aebbe99facacfe92f22b942cbd759900000000000000000000000000000000000000000000000000000000'),  # noqa: E501
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
                log_index=232,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000002af4522041b8670dc'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000088e6a0c2ddd26feeb64f039a2c41296fcb3f5640'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000068b3465833fb72a70ecdf485e0e4c7bd8665fc45'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=233,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000001176592e00'),  # noqa: E501
                address=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000eb312f4921aebbe99facacfe92f22b942cbd7599'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000088e6a0c2ddd26feeb64f039a2c41296fcb3f5640'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=234,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000001176592e00fffffffffffffffffffffffffffffffffffffffffffffffd50baddfbe4798f2400000000000000000000000000000000000064659f7f94d4566f174408bd10230000000000000000000000000000000000000000000000011464a6feb449adec0000000000000000000000000000000000000000000000000000000000031958'),  # noqa: E501
                address=string_to_evm_address('0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000068b3465833fb72a70ecdf485e0e4c7bd8665fc45'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000068b3465833fb72a70ecdf485e0e4c7bd8665fc45'),  # noqa: E501
                ],
            ),
        ],
    )

    internal_tx = EvmInternalTransaction(
        parent_tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        trace_id=27,
        timestamp=Timestamp(1646375440),
        block_number=14351442,
        from_address='0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45',
        to_address=ADDY_2,
        value=FVal('49.523026278486536412') * EXP18,
    )

    dbevmtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        dbevmtx.add_evm_internal_transactions(cursor, [internal_tx], relevant_address=ADDY_2)  # noqa: E501
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    events = decoder.decode_transaction(transaction=transaction, tx_receipt=receipt)

    assert len(events) == 3
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1646375440000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('0.00393701451')),
            location_label=ADDY_2,
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1646375440000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDC,
            balance=Balance(amount=FVal('75000')),
            location_label=ADDY_2,
            notes=f'Swap 75000 USDC via {CPT_UNISWAP_V3} auto router',
            counterparty=CPT_UNISWAP_V3,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=2,
            timestamp=Timestamp(1646375440000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('49.523026278486536412')),
            location_label=ADDY_2,
            notes=f'Receive 49.523026278486536412 ETH as the result of a swap via {CPT_UNISWAP_V3} auto router',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[ADDY_3]])
def test_uniswap_v3_swap_by_aggregator(database, ethereum_inquirer, eth_transactions):
    """
    This checks that swap(s) initiated by an aggregator is decoded properly.
    Data is taken from:
    https://etherscan.io/tx/0x14e73a3bbced025ae22245eae0045972c1664fc01038b2ba6b1153590f536948
    """
    tx_hex = '0x14e73a3bbced025ae22245eae0045972c1664fc01038b2ba6b1153590f536948'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1669210175),
        block_number=16032999,
        from_address='0xc9ec550BEA1C64D779124b23A26292cc223327b6',
        to_address=ADDY_3,
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x13d79a0b000000000000000000000000000000000000000000000000000000000000008000000000000000000000000000000000000000000000000000000000000000e0000000000000000000000000000000000000000000000000000000000000014000000000000000000000000000000000000000000000000000000000000003600000000000000000000000000000000000000000000000000000000000000002000000000000000000000000d9fcd98c322942075a5c3860693e9f4f03aae07b000000000000000000000000eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000012171be30000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001000000000000000000000000dd84ce1adcb3a4908db61a1dfa3353c3974c5a2b00000000000000000000000000000000000000000000000b96bbc3ff3cd324e10000000000000000000000000000000000000000000000000a32c8497eefc38400000000000000000000000000000000000000000000000000000000637e2708fda28b94d496c30e7bf8d159f8e2c4396926574362e79d263e7b37570fb5936100000000000000000000000000000000000000000000000005e9f5d449342740000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000b96bbc3ff3cd324e100000000000000000000000000000000000000000000000000000000000001600000000000000000000000000000000000000000000000000000000000000041ae2a304d26cbf1620faad930a50a4528cb678f106bd9fdad327f90cd0f4681012815da2bf7ff37e7e02c012c894f8c38cbc57fd11788b971ffc64f348b8efa931c0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000600000000000000000000000000000000000000000000000000000000000000080000000000000000000000000000000000000000000000000000000000000032000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000001c00000000000000000000000000d53497746e70c8cc2e5e8d2ac5f0a33f93c93530000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000006000000000000000000000000000000000000000000000000000000000000000e46af479b2000000000000000000000000000000000000000000000000000000000000008000000000000000000000000000000000000000000000000b96bbc3ff3cd324e10000000000000000000000000000000000000000000000000a3ea020000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002bd9fcd98c322942075a5c3860693e9f4f03aae07b002710c02aaa39b223fe8d0a0e5c4f27ead9083c756cc200000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc20000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000006000000000000000000000000000000000000000000000000000000000000000242e1a7d4d0000000000000000000000000000000000000000000000000a3feffdf3a10c12000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
        nonce=29513,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=249,
                data=hexstring_to_bytes('0x000000000000000000000000d9fcd98c322942075a5c3860693e9f4f03aae07b000000000000000000000000eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee00000000000000000000000000000000000000000000000b9ca5b9d386074c210000000000000000000000000000000000000000000000000a3feffdf3a10c1200000000000000000000000000000000000000000000000005e9f5d44934274000000000000000000000000000000000000000000000000000000000000000c00000000000000000000000000000000000000000000000000000000000000038f2e988cb71d09a733a32e47090ec8270d3605d0605167c15f61833c46307946edd84ce1adcb3a4908db61a1dfa3353c3974c5a2b637e27080000000000000000'),  # noqa: E501
                address=string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xa07a543ab8a018198e99ca0184c93fe9050a79400a0a723441f84de1d972cc17'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000dd84ce1adcb3a4908db61a1dfa3353c3974c5a2b'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=250,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000b9ca5b9d386074c21'),  # noqa: E501
                address=string_to_evm_address('0xd9Fcd98c322942075A5C3860693e9f4f03AAE07b'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000dd84ce1adcb3a4908db61a1dfa3353c3974c5a2b'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=251,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000fb72e42ac09146ba30000000000000000000000000000000000000000000000041a8888d8830d1f82'),  # noqa: E501
                address=string_to_evm_address('0xd9Fcd98c322942075A5C3860693e9f4f03AAE07b'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xdec2bacdd2f05b59de34da9b523dff8be42e5e38e818c82fdb0bae774387a724'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000e6da683076b7ed6ce7ec972f21eb8f91e9137a17'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=252,
                data=hexstring_to_bytes('0xffffffffffffffffffffffffffffffffffffffffffffffe427dd9990fb99e04c'),  # noqa: E501
                address=string_to_evm_address('0xd9Fcd98c322942075A5C3860693e9f4f03AAE07b'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000dd84ce1adcb3a4908db61a1dfa3353c3974c5a2b'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c92e8bdf79f0507f65a392b0ab4667716bfe0110'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=253,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000a3feffd7f24c066'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000b003df4b243f938132e8cadbeb237abc5a889fb4'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=254,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000b96bbc3ff3cd324e1'),  # noqa: E501
                address=string_to_evm_address('0xd9Fcd98c322942075A5C3860693e9f4f03AAE07b'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000b003df4b243f938132e8cadbeb237abc5a889fb4'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=255,
                data=hexstring_to_bytes('0xffffffffffffffffffffffffffffffffffffffffffffff5fcfb0aa366255e470'),  # noqa: E501
                address=string_to_evm_address('0xd9Fcd98c322942075A5C3860693e9f4f03AAE07b'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000d53497746e70c8cc2e5e8d2ac5f0a33f93c9353'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=256,
                data=hexstring_to_bytes('fffffffffffffffffffffffffffffffffffffffffffffffff5c0100280db3f9a00000000000000000000000000000000000000000000000b96bbc3ff3cd324e10000000000000000000000000000000000000010fc53ece379d82dde087ced260000000000000000000000000000000000000000000000634af2979832dffc7e000000000000000000000000000000000000000000000000000000000000dd4a'),  # noqa: E501
                address=string_to_evm_address('0xB003DF4B243f938132e8CAdBEB237AbC5A889FB4'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000d53497746e70c8cc2e5e8d2ac5f0a33f93c9353'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=257,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000000000000006af479b200000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                address=string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xed99827efb37016f2275f98c4bcf71c7551c75d59e9b450f79fa32e60be672c2'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000d53497746e70c8cc2e5e8d2ac5f0a33f93c9353'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=258,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000a3feffdf3a10c12'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=259,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000000000000002e1a7d4d00000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                address=string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xed99827efb37016f2275f98c4bcf71c7551c75d59e9b450f79fa32e60be672c2'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=260,
                data=hexstring_to_bytes('0x'),
                address=string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x40338ce1a7c49204f0099533b1e9a7ee0a3d261f84974ab7af36105b8c4e9db4'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c9ec550bea1c64d779124b23a26292cc223327b6'),  # noqa: E501
                ],
            ),
        ],
    )
    internal_tx = EvmInternalTransaction(
        parent_tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        trace_id=27,
        timestamp=Timestamp(1669210175),
        block_number=16032999,
        from_address='0x9008D19f58AAbD9eD0D60971565AA8510560ab41',
        to_address=ADDY_3,
        value=FVal('0.738572737905232914') * EXP18,
    )
    dbevmtx = DBEvmTx(database)
    with database.user_write() as write_cursor:
        dbevmtx.add_evm_transactions(write_cursor, [transaction], relevant_address=None)
        dbevmtx.add_evm_internal_transactions(write_cursor, [internal_tx], relevant_address=ADDY_3)  # noqa: E501
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    events = decoder.decode_transaction(transaction=transaction, tx_receipt=receipt)
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1669210175000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.738572737905232914')),
            location_label=ADDY_3,
            notes='Receive 0.738572737905232914 ETH from 0x9008D19f58AAbD9eD0D60971565AA8510560ab41',  # noqa: E501
            counterparty='0x9008D19f58AAbD9eD0D60971565AA8510560ab41',
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=251,
            timestamp=TimestampMS(1669210175000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=EvmToken(ethaddress_to_identifier('0xd9Fcd98c322942075A5C3860693e9f4f03AAE07b')),
            balance=Balance(amount=FVal('214.201817170016947233')),
            location_label=ADDY_3,
            notes='Send 214.201817170016947233 EUL from 0xdD84Ce1aDcb3A4908Db61A1dFA3353C3974c5a2B to 0x9008D19f58AAbD9eD0D60971565AA8510560ab41',  # noqa: E501
            counterparty='0x9008D19f58AAbD9eD0D60971565AA8510560ab41',
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=253,
            timestamp=TimestampMS(1669210175000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=EvmToken(ethaddress_to_identifier('0xd9Fcd98c322942075A5C3860693e9f4f03AAE07b')),
            balance=Balance(amount=FVal('1.157920892373161954235709850E+59')),
            location_label=ADDY_3,
            notes='Approve 115792089237316195423570985000000000000000000000000000000000 EUL of 0xdD84Ce1aDcb3A4908Db61A1dFA3353C3974c5a2B for spending by 0xC92E8bdf79f0507f65a392b0ab4667716BFE0110',  # noqa: E501
            counterparty='0xC92E8bdf79f0507f65a392b0ab4667716BFE0110',
        ),
    ]
    assert len(events) == 3
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xd6f2F8a2D6BD2f06234a95e61b55f41676CbE50d']])
def test_swap_eth_to_tokens(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0xaf8755f0ab8a0cfa8901fe2a9250a8727cca54825210061aab90f34b7a3ed9ba')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    assert events == [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1641528717000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('0.082968903798164815')),
            location_label=user_address,
            notes='Burned 0.082968903798164815 ETH for gas',
            counterparty='gas',
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1641528717000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('262')),
            location_label=user_address,
            notes=f'Swap 262 ETH via {CPT_UNISWAP_V3} auto router',
            counterparty=CPT_UNISWAP_V3,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1641528717000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            balance=Balance(amount=FVal('841047.621362')),
            location_label=user_address,
            notes=f'Receive 841047.621362 USDC as the result of a swap via {CPT_UNISWAP_V3} auto router',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
        ),
    ]


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xd6f2F8a2D6BD2f06234a95e61b55f41676CbE50d']])
def test_swap_tokens_to_eth(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x1b6c3fe84ed4f8f273a54c3e3f6ba80f843522c6a19220a05089104fc54b09ba')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    assert events == [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1655541881000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('0.03490929635453643')),
            location_label=user_address,
            notes='Burned 0.03490929635453643 ETH for gas',
            counterparty='gas',
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1655541881000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            balance=Balance(amount=FVal('150000')),
            location_label=user_address,
            notes=f'Swap 150000 USDC via {CPT_UNISWAP_V3} auto router',
            counterparty=CPT_UNISWAP_V3,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1655541881000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('150.306972002256248665')),
            location_label=user_address,
            notes=f'Receive 150.306972002256248665 ETH as the result of a swap via {CPT_UNISWAP_V3} auto router',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
        ),
    ]


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xCDeBA740656640fCA1A7b573e925f8C3b92f76b6']])
def test_swap_tokens_to_tokens_single_receipt(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x3ae92fa63a9cf672906036beb18ece09592a8a471bd7f15e4385ca5011615e51')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    assert events == [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1643060358000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.074007294410979132')),
            location_label=user_address,
            notes='Burned 0.074007294410979132 ETH for gas',
            counterparty='gas',
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1643060358000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0xa47c8bf37f92aBed4A126BDA807A7b7498661acD'),
            balance=Balance(amount=FVal('3000000')),
            location_label=user_address,
            notes=f'Swap 3000000 UST via {CPT_UNISWAP_V3} auto router',
            counterparty=CPT_UNISWAP_V3,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1643060358000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            balance=Balance(amount=FVal('2994089.109716')),
            location_label=user_address,
            notes=f'Receive 2994089.109716 USDC as the result of a swap via {CPT_UNISWAP_V3} auto router',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
        ),
    ]


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x73264d8bE9EDDfCD25E4d54BF1b69828c9631A1C']])
def test_swap_tokens_to_tokens_multiple_receipts(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0xa4e0dbf77bf7a9721e1ba4ecf44ed6ea8dcb1c16e9e784b6fefa30749f64e7c0')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    assert events == [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1658331886000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.049823244141159502')),
            location_label=user_address,
            notes='Burned 0.049823244141159502 ETH for gas',
            counterparty='gas',
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1658331886000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'),
            balance=Balance(amount=FVal('224.18247796')),
            location_label=user_address,
            notes=f'Swap 224.18247796 WBTC via {CPT_UNISWAP_V3} auto router',
            counterparty=CPT_UNISWAP_V3,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1658331886000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F'),
            balance=Balance(amount=FVal('5326023.631679255788142165')),
            location_label=user_address,
            notes=f'Receive 5326023.631679255788142165 DAI as the result of a swap via {CPT_UNISWAP_V3} auto router',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [[ADDY_4]])
def test_uniswap_v3_remove_liquidity(database, ethereum_inquirer, eth_transactions):
    """
    Check that removing liquidity from Uniswap V3 LP is decoded properly.

    Data is taken from:
    https://etherscan.io/tx/0x76c312fe1c8604de5175c37dcbbb99cc8699336f3e4840e9e29e3383970f6c6d
    """
    tx_hash = '0x76c312fe1c8604de5175c37dcbbb99cc8699336f3e4840e9e29e3383970f6c6d'
    evmhash = deserialize_evm_tx_hash(tx_hash)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1672413263),
        block_number=16298410,
        from_address=ADDY_4,
        to_address='0xC36442b4a4522E871399CD717aBDD847Ab11FE88',
        value=0,
        gas=375016,
        gas_price=18022413529,
        gas_used=250012,
        input_data=hexstring_to_bytes('0xac9650d80000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000160000000000000000000000000000000000000000000000000000000000000022000000000000000000000000000000000000000000000000000000000000002a000000000000000000000000000000000000000000000000000000000000000a40c49ccbe000000000000000000000000000000000000000000000000000000000005efb3000000000000000000000000000000000000000000000000042895835c5ebcf9000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002a28ce083bcb0ad2510000000000000000000000000000000000000000000000000000000063af04e7000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000084fc6f7865000000000000000000000000000000000000000000000000000000000005efb3000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000ffffffffffffffffffffffffffffffff00000000000000000000000000000000ffffffffffffffffffffffffffffffff00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004449404b7c00000000000000000000000000000000000000000000002a4980e9fdaababa64000000000000000000000000354304234329a8d2425965c647e701a72d3438e5000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000064df2ab5bb000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb480000000000000000000000000000000000000000000000000000000096c6393c000000000000000000000000354304234329a8d2425965c647e701a72d3438e500000000000000000000000000000000000000000000000000000000'),  # noqa: E501
        nonce=51,
    )
    internal_tx = EvmInternalTransaction(
        parent_tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        trace_id=27,
        timestamp=Timestamp(1672413263),
        block_number=16298410,
        from_address='0xC36442b4a4522E871399CD717aBDD847Ab11FE88',
        to_address=ADDY_4,
        value=1000374356073654694973,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=46,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000042895835c5ebcf90000000000000000000000000000000000000000000000000000002d9adfdf060000000000000000000000000000000000000000000000361a48c6e194a2cc2a'),  # noqa: E501
                address=string_to_evm_address('0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c36442b4a4522e871399cd717abdd847ab11fe88'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000000003195c'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000032460'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=47,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000042895835c5ebcf90000000000000000000000000000000000000000000000000000002d9adfdf060000000000000000000000000000000000000000000000361a48c6e194a2cc2a'),  # noqa: E501
                address=string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x26f6a048ee9138f2c0ce266f322cb99228e8d619ae2bff30c67f8dcf9d2377b4'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000000005efb3'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=48,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000002e31a61842'),  # noqa: E501
                address=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000008ad599c3a0ff1de082011efddc58f1908eb6e6d8'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c36442b4a4522e871399cd717abdd847ab11fe88'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=49,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000363afba8a37452b43d'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000008ad599c3a0ff1de082011efddc58f1908eb6e6d8'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c36442b4a4522e871399cd717abdd847ab11fe88'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=50,
                data=hexstring_to_bytes('0x000000000000000000000000c36442b4a4522e871399cd717abdd847ab11fe880000000000000000000000000000000000000000000000000000002e31a618420000000000000000000000000000000000000000000000363afba8a37452b43d'),  # noqa: E501
                address=string_to_evm_address('0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c36442b4a4522e871399cd717abdd847ab11fe88'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000000003195c'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000032460'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=51,
                data=hexstring_to_bytes('0x000000000000000000000000c36442b4a4522e871399cd717abdd847ab11fe880000000000000000000000000000000000000000000000000000002e31a618420000000000000000000000000000000000000000000000363afba8a37452b43d'),  # noqa: E501
                address=string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x40d0efd1a53d60ecbf40971b9daf7dc90178c3aadc7aab1765632738fa8b8f01'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000000005efb3'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=52,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000363afba8a37452b43d'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c36442b4a4522e871399cd717abdd847ab11fe88'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=53,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000002e31a61842'),  # noqa: E501
                address=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c36442b4a4522e871399cd717abdd847ab11fe88'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000354304234329a8d2425965c647e701a72d3438e5'),  # noqa: E501
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        dbevmtx.add_evm_internal_transactions(cursor, [internal_tx], relevant_address=ADDY_4)  # noqa: E501
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    events = decoder.decode_transaction(transaction=transaction, tx_receipt=receipt)

    assert len(events) == 3
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1672413263000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.004505819651212348')),
            location_label=ADDY_4,
            notes='Burned 0.004505819651212348 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1672413263000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            balance=Balance(amount=FVal('1000.374356073654694973')),
            location_label=ADDY_4,
            notes='Remove 1000.374356073654694973 ETH from uniswap-v3 LP 389043',
            counterparty=CPT_UNISWAP_V3,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=56,
            timestamp=TimestampMS(1672413263000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_USDC,
            balance=Balance(amount=FVal('198401.464386')),
            location_label=ADDY_4,
            notes='Remove 198401.464386 USDC from uniswap-v3 LP 389043',
            counterparty=CPT_UNISWAP_V3,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[ADDY_5]])
def test_uniswap_v3_add_liquidity(database, ethereum_inquirer, eth_transactions):
    """
    Check that adding liquidity to a Uniswap V3 LP is decoded properly.

    Data is taken from:
    https://etherscan.io/tx/0x6bf3588f669a784adf5def3c0db149b0cdbcca775e472bb35f00acedee263c4c
    """
    tx_hash = '0x6bf3588f669a784adf5def3c0db149b0cdbcca775e472bb35f00acedee263c4c'
    evmhash = deserialize_evm_tx_hash(tx_hash)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1672409279),
        block_number=16298078,
        from_address=ADDY_5,
        to_address='0xC36442b4a4522E871399CD717aBDD847Ab11FE88',
        value=0,
        gas=1172373,
        gas_price=14477765135,
        gas_used=390791,
        input_data=hexstring_to_bytes('0x883164560000000000000000000000006b175474e89094c44da98b954eedeac495271d0f000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb480000000000000000000000000000000000000000000000000000000000000064fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffbc891fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffbc8a50000000000000000000000000000000000000000000002624c2297d3f3dfa86c00000000000000000000000000000000000000000000000000000003328323c600000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000a931b486f661540c6d709ae6dfc8bcef347ea4370000000000000000000000000000000000000000000000000000000063aef737'),  # noqa: E501
        nonce=173,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=307,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000002624c2297d3f3de90b6'),  # noqa: E501
                address=string_to_evm_address('0x6B175474E89094C44Da98b954EedeAC495271d0F'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000a931b486f661540c6d709ae6dfc8bcef347ea437'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000005777d92f208679db4b9778590fa3cab3ac9e2168'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=308,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000003328323c6'),  # noqa: E501
                address=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000a931b486f661540c6d709ae6dfc8bcef347ea437'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000005777d92f208679db4b9778590fa3cab3ac9e2168'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=309,
                data=hexstring_to_bytes('000000000000000000000000c36442b4a4522e871399cd717abdd847ab11fe880000000000000000000000000000000000000000000000015aea6e37897e087c0000000000000000000000000000000000000000000002624c2297d3f3de90b600000000000000000000000000000000000000000000000000000003328323c6'),  # noqa: E501
                address=string_to_evm_address('0x5777d92f208679DB4b9778590Fa3CAB3aC9e2168'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c36442b4a4522e871399cd717abdd847ab11fe88'),  # noqa: E501
                    hexstring_to_bytes('0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffffffbc891'),  # noqa: E501
                    hexstring_to_bytes('0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffffffbc891'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=310,
                data=hexstring_to_bytes('0x'),
                address=string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000a931b486f661540c6d709ae6dfc8bcef347ea437'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000061fcd'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=311,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000015aea6e37897e087c0000000000000000000000000000000000000000000002624c2297d3f3de90b600000000000000000000000000000000000000000000000000000003328323c6'),  # noqa: E501
                address=string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x3067048beee31b25b2f1681f88dac838c8bba36af25bfb2b7cf7473a5847e35f'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000061fcd'),  # noqa: E501
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
    events = decoder.decode_transaction(transaction=transaction, tx_receipt=receipt)

    assert len(events) == 4
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1672409279000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.005657780314871785')),
            location_label=ADDY_5,
            notes='Burned 0.005657780314871785 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=308,
            timestamp=TimestampMS(1672409279000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_DAI,
            balance=Balance(amount=FVal('11257.999999195502514358')),
            location_label=ADDY_5,
            notes='Deposit 11257.999999195502514358 DAI to uniswap-v3 LP 401357',
            counterparty=CPT_UNISWAP_V3,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=309,
            timestamp=TimestampMS(1672409279000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_USDC,
            balance=Balance(amount=FVal('13732.357062')),
            location_label=ADDY_5,
            notes='Deposit 13732.357062 USDC to uniswap-v3 LP 401357',
            counterparty=CPT_UNISWAP_V3,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=311,
            timestamp=TimestampMS(1672409279000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NFT,
            asset=Asset('eip155:1/erc721:0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
            balance=Balance(amount=FVal(1)),
            location_label=ADDY_5,
            notes='Create uniswap-v3 LP with id 401357',
            counterparty=CPT_UNISWAP_V3,
            extra_data={'token_id': 401357, 'token_name': 'Uniswap V3 Positions NFT-V1'},
        ),
    ]
    assert events == expected_events
