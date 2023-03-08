import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
from rotkehlchen.chain.ethereum.modules.uniswap.constants import CPT_UNISWAP_V2
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USDC
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

ADDY_1 = string_to_evm_address('0x3CAdf2cA458376a6a5feA2EF3612346037D5A787')
ADDY_2 = string_to_evm_address('0xCC917Ab28544c80E2f0e8efFbd22551A3cB096bE')
ADDY_3 = string_to_evm_address('0x65fc65C639467423Bf19801a59FCfd62f0F29777')


@pytest.mark.parametrize('ethereum_accounts', [[ADDY_1]])
def test_uniswap_v2_swap(database, ethereum_inquirer, eth_transactions):
    """Data for swap
    https://etherscan.io/tx/0x67cf6c4ce5078f9750a14afd2f5070c327caf8c5180bdee2be59644ac59974e1/
    """
    tx_hex = '0x67cf6c4ce5078f9750a14afd2f5070c327caf8c5180bdee2be59644ac59974e1'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1646375440),
        block_number=14351442,
        from_address=ADDY_1,
        to_address='0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
        value=150000000000000000,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x7ff36ab50000000000000000000000000000000000000000000000165e98da19714be59e00000000000000000000000000000000000000000000000000000000000000800000000000000000000000003cadf2ca458376a6a5fea2ef3612346037d5a787000000000000000000000000000000000000000000000000000000006114d38c0000000000000000000000000000000000000000000000000000000000000004000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb480000000000000000000000003432b6a60d23ca0dfca7761b7ab56459d9c964d0000000000000000000000000853d955acef822db058eb8505911ed77f175b99e'),  # noqa: E501
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
                log_index=508,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000214e8348c4f0000'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000b4e16d0168e52d35cacd2c6185b44281ec28c9dc'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=509,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000001be99523'),  # noqa: E501
                address=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000b4e16d0168e52d35cacd2c6185b44281ec28c9dc'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000009bac32d4f3322bc7588bb119283bad7073145355'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=511,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000214e8348c4f0000000000000000000000000000000000000000000000000000000000001be995230000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                address=string_to_evm_address('0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000009bac32d4f3322bc7588bb119283bad7073145355'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=514,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000007aa72c2d7bbdda13f'),  # noqa: E501
                address=string_to_evm_address('0xf4aD61dB72f114Be877E87d62DC5e7bd52DF4d9B'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000009bac32d4f3322bc7588bb119283bad7073145355'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000e1573b9d29e2183b1af0e743dc2754979a40d237'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=516,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001be99523000000000000000000000000000000000000000000000007aa72c2d7bbdda13f0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                address=string_to_evm_address('0x9BAC32D4f3322bC7588BB119283bAd7073145355'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000e1573b9d29e2183b1af0e743dc2754979a40d237'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=517,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000001918f7e61d476779dd'),  # noqa: E501
                address=string_to_evm_address('0x853d955aCEf822Db058eb8505911ED77F175b99e'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000e1573b9d29e2183b1af0e743dc2754979a40d237'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000003cadf2ca458376a6a5fea2ef3612346037d5a787'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=519,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000007aa72c2d7bbdda13f0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001918f7e61d476779dd'),  # noqa: E501
                address=string_to_evm_address('0xE1573B9D29e2183B1AF0e743Dc2754979A40D237'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000003cadf2ca458376a6a5fea2ef3612346037d5a787'),  # noqa: E501
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
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.15'), usd_value=ZERO),
            location_label=ADDY_1,
            notes='Swap 0.15 ETH in uniswap-v2 from 0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',
            counterparty=CPT_UNISWAP_V2,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=519,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=EvmToken('eip155:1/erc20:0x853d955aCEf822Db058eb8505911ED77F175b99e'),
            balance=Balance(amount=FVal('462.967761432322996701'), usd_value=ZERO),
            location_label=ADDY_1,
            notes='Receive 462.967761432322996701 FRAX in uniswap-v2 from 0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',  # noqa: E501
            counterparty=CPT_UNISWAP_V2,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[ADDY_1]])
def test_uniswap_v2_swap_eth_returned(database, ethereum_inquirer, eth_transactions):
    """Test a transaction where eth is swapped and some of it is returned due to change in price"""
    tx_hex = '0x20ecc226c438a8803a6195d8031ae7dd97a27351e6b7429621b36194121b9b76'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1646375440),
        block_number=14351442,
        from_address=ADDY_1,
        to_address='0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
        value=FVal('1.59134916748576351') * EXP18,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xfb3bdb410000000000000000000000000000000000000000204fce5e3e2502611000000000000000000000000000000000000000000000000000000000000000000000800000000000000000000000003cadf2ca458376a6a5fea2ef3612346037d5a78700000000000000000000000000000000000000000000000000000000616ed7a40000000000000000000000000000000000000000000000000000000000000002000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2000000000000000000000000761d38e5ddf6ccf6cf7c55759d5210750b5d60f3'),  # noqa: E501
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
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000015f8d0c01dad329c'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007b73644935b8e68019ac6356c40661e1bc315860'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=307,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000204fce5e3e25026110000000'),  # noqa: E501
                address=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007b73644935b8e68019ac6356c40661e1bc315860'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000003cadf2ca458376a6a5fea2ef3612346037d5a787'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=309,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000015f8d0c01dad329c0000000000000000000000000000000000000000204fce5e3e250261100000000000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                address=string_to_evm_address('0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000003cadf2ca458376a6a5fea2ef3612346037d5a787'),  # noqa: E501
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
        from_address='0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
        to_address=ADDY_1,
        value=FVal('0.008104374914845978') * EXP18,
    )

    dbevmtx = DBEvmTx(database)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        dbevmtx.add_evm_internal_transactions(cursor, [internal_tx], relevant_address=ADDY_1)  # noqa: E501
    events = decoder.decode_transaction(transaction=transaction, tx_receipt=receipt)

    assert len(events) == 4
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
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
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.008104374914845978),
                usd_value=ZERO,
            ),
            location_label=ADDY_1,
            notes='Refund of 0.008104374914845978 ETH in uniswap-v2 due to price change',  # noqa: E501
            counterparty=CPT_UNISWAP_V2,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(amount=FVal('1.59134916748576351'), usd_value=ZERO),
            location_label=ADDY_1,
            notes='Swap 1.59134916748576351 ETH in uniswap-v2 from 0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',  # noqa: E501
            counterparty=CPT_UNISWAP_V2,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=310,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=EvmToken('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            balance=Balance(amount=FVal('10000000000000000000000'), usd_value=ZERO),
            location_label=ADDY_1,
            notes='Receive 10000000000000000000000 USDC in uniswap-v2 from 0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',  # noqa: E501
            counterparty=CPT_UNISWAP_V2,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xa931b486F661540c6D709aE6DfC8BcEF347ea437']])
def test_uniswap_v2_swap_with_approval(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0xcbe558177f62ccdb77f59b6be11e60b0a3fed1d224d5ce28d2bb6dff59447d3b')  # noqa: E501
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
            timestamp=TimestampMS(1667857559000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('0.003227029072809172')),
            location_label=user_address,
            notes='Burned 0.003227029072809172 ETH for gas',
            counterparty='gas',
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=297,
            timestamp=TimestampMS(1667857559000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0x33349B282065b0284d756F0577FB39c158F935e6'),
            balance=Balance(amount=FVal('115792089237316195423570985000000000000000000000000000000000')),  # noqa: E501
            location_label=user_address,
            notes='Set MPL spending approval of 0xa931b486F661540c6D709aE6DfC8BcEF347ea437 by 0x617Dee16B86534a5d792A4d7A62FB491B544111E to 115792089237316195423570985000000000000000000000000000000000',  # noqa: E501
            counterparty='0x617Dee16B86534a5d792A4d7A62FB491B544111E',
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=300,
            timestamp=TimestampMS(1667857559000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0x33349B282065b0284d756F0577FB39c158F935e6'),
            balance=Balance(amount=FVal('20.653429896')),
            location_label=user_address,
            notes='Swap 20.653429896 MPL in uniswap-v2',
            counterparty='uniswap-v2',
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=301,
            timestamp=TimestampMS(1667857559000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            balance=Balance(amount=FVal('273.798721')),
            location_label=user_address,
            notes=f'Receive 273.798721 USDC as a result of a {CPT_UNISWAP_V2} swap',
            counterparty='uniswap-v2',
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [[ADDY_2]])
def test_uniswap_v2_add_liquidity(database, ethereum_inquirer, eth_transactions):
    """
    This checks that adding liquidity to Uniswap V2 pool is decoded properly.

    Data is taken from:
    https://etherscan.io/tx/0x1bab8a89a6a3f8cb127cfaf7cd58809201a4e230d0a05f9e067674749605959e
    """
    tx_hash = '0x1bab8a89a6a3f8cb127cfaf7cd58809201a4e230d0a05f9e067674749605959e'
    evmhash = deserialize_evm_tx_hash(tx_hash)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1672316471),
        block_number=16293065,
        from_address=ADDY_2,
        to_address='0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
        value=0,
        gas=197127,
        gas_price=18501979762,
        gas_used=158459,
        input_data=hexstring_to_bytes('0xe8e33700000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb480000000000000000000000006b175474e89094c44da98b954eedeac495271d0f00000000000000000000000000000000000000000000000000000000017d78400000000000000000000000000000000000000000000000015adf749283d89f7500000000000000000000000000000000000000000000000000000000017b8ff800000000000000000000000000000000000000000000000159237544fb81c79f000000000000000000000000cc917ab28544c80e2f0e8effbd22551a3cb096be0000000000000000000000000000000000000000000000000000000063ae0bab'),  # noqa: E501
        nonce=259,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=117,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000000017d7840'),  # noqa: E501
                address=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000cc917ab28544c80e2f0e8effbd22551a3cb096be'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000ae461ca67b15dc8dc81ce7615e0320da1a9ab8d5'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=118,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000015adf749283d89f75'),  # noqa: E501
                address=string_to_evm_address('0x6B175474E89094C44Da98b954EedeAC495271d0F'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000cc917ab28544c80e2f0e8effbd22551a3cb096be'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000ae461ca67b15dc8dc81ce7615e0320da1a9ab8d5'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=119,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000142e06b0b866'),  # noqa: E501
                address=string_to_evm_address('0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000cc917ab28544c80e2f0e8effbd22551a3cb096be'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=120,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000d9f840b4a272a74b3a46c00000000000000000000000000000000000000000000000000000efb5baf8782'),  # noqa: E501
                address=string_to_evm_address('0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=121,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000015adf749283d89f7500000000000000000000000000000000000000000000000000000000017d7840'),  # noqa: E501
                address=string_to_evm_address('0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),  # noqa: E501
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
    events = decoder.decode_transaction(transaction=transaction, tx_receipt=receipt)

    assert len(events) == 4
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1672316471000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.002931805211106758')),
            location_label=ADDY_2,
            notes='Burned 0.002931805211106758 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=118,
            timestamp=TimestampMS(1672316471000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_USDC,
            balance=Balance(amount=FVal('25')),
            location_label=ADDY_2,
            notes='Deposit 25 USDC to uniswap-v2 LP 0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5',  # noqa: E501
            counterparty=CPT_UNISWAP_V2,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=119,
            timestamp=TimestampMS(1672316471000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_DAI,
            balance=Balance(amount=FVal('24.994824629555601269')),
            location_label=ADDY_2,
            notes='Deposit 24.994824629555601269 DAI to uniswap-v2 LP 0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5',  # noqa: E501
            counterparty=CPT_UNISWAP_V2,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=120,
            timestamp=TimestampMS(1672316471000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5'),
            balance=Balance(amount=FVal('0.000022187913295974')),
            location_label=ADDY_2,
            notes='Receive 0.000022187913295974 UNI-V2 from uniswap-v2 pool',
            counterparty=CPT_UNISWAP_V2,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[ADDY_3]])
def test_uniswap_v2_remove_liquidity(database, ethereum_inquirer, eth_transactions):
    """
    This checks that removing liquidity from a Uniswap V2 pool is decoded properly.

    Data is taken from:
    https://etherscan.io/tx/0x0936a16e1d3655e832c60bed52040fd5ac0d99d03865d11225b3183dba318f43
    """
    tx_hash = '0x0936a16e1d3655e832c60bed52040fd5ac0d99d03865d11225b3183dba318f43'
    evmhash = deserialize_evm_tx_hash(tx_hash)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1672784687),
        block_number=16329226,
        from_address=ADDY_3,
        to_address='0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
        value=0,
        gas=354181,
        gas_price=20000000000,
        gas_used=234471,
        input_data=hexstring_to_bytes('0xded9382a000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb4800000000000000000000000000000000000000000000000000000016648cc933000000000000000000000000000000000000000000000000000000000066875e0000000000000000000000000000000000000000000000000013b5a924011b7a00000000000000000000000065fc65c639467423bf19801a59fcfd62f0f297770000000000000000000000000000000000000000000000000000000063b4b4ef0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001c1dc56216cf8a1c8d2a0047d192c419c6cd789abf4fbb57f33d7226aa9a6b0aa61ae9f6b20565405cefc191c797f78b3d2d10ca2483cf74043b561bfd7c4d54e1'),  # noqa: E501
        nonce=2,
    )
    internal_tx = EvmInternalTransaction(
        parent_tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        trace_id=27,
        timestamp=Timestamp(1672784687),
        block_number=16329226,
        from_address='0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
        to_address=ADDY_3,
        value=FVal('0.005839327781368506') * EXP18,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=31,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000016648cc933'),  # noqa: E501
                address=string_to_evm_address('0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000065fc65c639467423bf19801a59fcfd62f0f29777'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=32,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000016648cc933'),  # noqa: E501
                address=string_to_evm_address('0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000065fc65c639467423bf19801a59fcfd62f0f29777'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000b4e16d0168e52d35cacd2c6185b44281ec28c9dc'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=33,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000016648cc933'),  # noqa: E501
                address=string_to_evm_address('0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000b4e16d0168e52d35cacd2c6185b44281ec28c9dc'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=34,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000000006beed5'),  # noqa: E501
                address=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000b4e16d0168e52d35cacd2c6185b44281ec28c9dc'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=35,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000014bed67222b2ba'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000b4e16d0168e52d35cacd2c6185b44281ec28c9dc'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=36,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000026068b3a890000000000000000000000000000000000000000000000074f0bf96ef2478fa7ad'),  # noqa: E501
                address=string_to_evm_address('0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=37,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000000006beed50000000000000000000000000000000000000000000000000014bed67222b2ba'),  # noqa: E501
                address=string_to_evm_address('0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=38,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000000006beed5'),  # noqa: E501
                address=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000065fc65c639467423bf19801a59fcfd62f0f29777'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=39,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000014bed67222b2ba'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),  # noqa: E501
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
        dbevmtx.add_evm_internal_transactions(cursor, [internal_tx], relevant_address=ADDY_3)  # noqa: E501
    events = decoder.decode_transaction(transaction=transaction, tx_receipt=receipt)

    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1672784687000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.00468942')),
            location_label=ADDY_3,
            notes='Burned 0.00468942 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1672784687000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.005839327781368506')),
            location_label=ADDY_3,
            notes='Remove 0.005839327781368506 ETH from uniswap-v2 LP 0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc',  # noqa: E501
            counterparty=CPT_UNISWAP_V2,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=33,
            timestamp=TimestampMS(1672784687000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset='eip155:1/erc20:0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc',
            balance=Balance(amount=FVal('9.6176228659E-8')),
            location_label=ADDY_3,
            notes='Set UNI-V2 spending approval of 0x65fc65C639467423Bf19801a59FCfd62f0F29777 by 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D to 0.000000096176228659',  # noqa: E501
            counterparty='0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=34,
            timestamp=TimestampMS(1672784687000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'),
            balance=Balance(amount=FVal('9.6176228659E-8')),
            location_label=ADDY_3,
            notes='Send 0.000000096176228659 UNI-V2 to uniswap-v2 pool',
            counterparty=CPT_UNISWAP_V2,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=40,
            timestamp=TimestampMS(1672784687000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_USDC,
            balance=Balance(amount=FVal('7.073493')),
            location_label=ADDY_3,
            notes='Remove 7.073493 USDC from uniswap-v2 LP 0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc',  # noqa: E501
            counterparty=CPT_UNISWAP_V2,
        ),
    ]
    assert events == expected_events
