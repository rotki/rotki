import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS, CPT_GNOSIS_CHAIN
from rotkehlchen.chain.ethereum.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.chain.ethereum.modules.airdrops.constants import CPT_ONEINCH
from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt, EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.fval import FVal
from rotkehlchen.types import EthereumTransaction, Location, deserialize_evm_tx_hash
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.hexbytes import hexstring_to_bytes


@pytest.mark.parametrize('ethereum_accounts', [['0xc931De6d845846E332a52D045072E3feF540Bd5d']])  # noqa: E501
def test_1inch_claim(database, ethereum_manager, eth_transactions):
    """Data for claim taken from
    https://etherscan.io/tx/0x0582a0db79de3fa21d3b92a8658e0b1034c51ea54a8e06ea84fbb91d41b8fe17
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0x0582a0db79de3fa21d3b92a8658e0b1034c51ea54a8e06ea84fbb91d41b8fe17'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EthereumTransaction(
        tx_hash=evmhash,
        timestamp=1646375440,
        block_number=14351442,
        from_address='0xc931De6d845846E332a52D045072E3feF540Bd5d',
        to_address='0xE295aD71242373C37C5FdA7B57F26f9eA1088AFe',
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x2e7ba6ef000000000000000000000000000000000000000000000000000000000000c0e5000000000000000000000000c931de6d845846e332a52d045072e3fef540bd5d00000000000000000000000000000000000000000000002109156970b0a5f32f00000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000010dbe83b35ea054d18e5fdd804d60b6a528f4b66a227079ecb82febf8eb40919495d102f8922e57278b2b6bb3369ae34c37c378dbd4819126c5e5d371ed4777c4580a9985219f50d16cefc798c2aeb6a4d7fa786f4f38ab27b420e6f3f8e25bd0f45709afe1f9fdec3cbea17d1ec63c6f62ce396524b04c9460bb05ef548239ae050b5330a4228c26b8b25ff021c6cc89ed4f0411ecce80256d090d860f9e6ff5e604076af74bd91959259ff59f8d54455a0edcad41ef1fe230504826f025769c250d89c63241d1dfec9dc4dc75f0a0ec47bcc10594ca7db74335507a5f6e4344b52b129d8e0aaeffe22b7595fa9f11c8e2381feafaf25042407913b9ec34cdf879a05d18a68b7a2506a29ba42fb004c7f32390f986f943a2557e304dc777f73869a046dc08506268e16603452a33ea179b4932eeae59338dd3fee75685cc490f1acba6c0ed0c90792bb6f9f696ad1417efe0032bb0e86b6927234ce419628e24c0d577b40b8956166e4d21cba88b58b32dec0a00b2864e8ed4ac5d7be6683f5f297aaf35d6ca208a954554f4ab14a1ca973daf13e7c1dad49db82611f4dadf2a3c32355753f5e11ba88adc0d27f10ad32ad4904bfd782c15693c6795b047124fccd0f927a7dda89206be7ad613644d02a622c3f30f5de40d052b4c3e10ef02a18107e7a23a7abca2aacc0bf854e247569f822013a86927b10f772b7b13fbc8732'),  # noqa: E501
        nonce=19,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=297,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000002109156970b0a5f32f'),  # noqa: E501
                address=string_to_evm_address('0x111111111117dC0aa78b770fA6A738034120C302'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000e295ad71242373c37c5fda7b57f26f9ea1088afe'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c931de6d845846e332a52d045072e3fef540bd5d'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=298,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000000000c0e5000000000000000000000000c931de6d845846e332a52d045072e3fef540bd5d00000000000000000000000000000000000000000000002109156970b0a5f32f'),  # noqa: E501
                address=string_to_evm_address('0xE295aD71242373C37C5FdA7B57F26f9eA1088AFe'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x4ec90e965519d92681267467f775ada5bd214aa92c0dc93d90a5e880ce9ed026'),  # noqa: E501
                ],
            ),
        ],
    )

    dbethtx = DBEthTx(database)
    with database.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
        decoder = EVMTransactionDecoder(
            database=database,
            ethereum_manager=ethereum_manager,
            eth_transactions=eth_transactions,
            msg_aggregator=msg_aggregator,
        )
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)
    assert len(events) == 2
    expected_events = [
        HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x0582a0db79de3fa21d3b92a8658e0b1034c51ea54a8e06ea84fbb91d41b8fe17',
            ),
            sequence_index=0,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.00393701451),
                usd_value=ZERO,
            ),
            location_label='0xc931De6d845846E332a52D045072E3feF540Bd5d',
            notes='Burned 0.00393701451 ETH in gas from 0xc931De6d845846E332a52D045072E3feF540Bd5d',  # noqa: E501
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x0582a0db79de3fa21d3b92a8658e0b1034c51ea54a8e06ea84fbb91d41b8fe17',
            ),
            sequence_index=298,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=EvmToken('eip155:1/erc20:0x111111111117dC0aa78b770fA6A738034120C302'),
            balance=Balance(amount=FVal('609.397099685988397871'), usd_value=ZERO),
            location_label='0xc931De6d845846E332a52D045072E3feF540Bd5d',
            notes='Claim 609.397099685988397871 1INCH from the 1INCH airdrop',
            counterparty=CPT_ONEINCH,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0x5EDCf547eCE0EA1765D6C02e9E5bae53b52E09D4']])  # noqa: E501
def test_gnosis_chain_bridge(database, ethereum_manager, eth_transactions):
    """Data for bridge taken from
    https://etherscan.io/tx/0x52f853d559d83b5303faf044e00e9109bd5c6a05b6633f9df34939f8e7c6de02
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0x52f853d559d83b5303faf044e00e9109bd5c6a05b6633f9df34939f8e7c6de02'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EthereumTransaction(
        tx_hash=evmhash,
        timestamp=1646375440,
        block_number=14351442,
        from_address='0x5EDCf547eCE0EA1765D6C02e9E5bae53b52E09D4',
        to_address='0x88ad09518695c6c3712AC10a214bE5109a655671',
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x09c5eabe000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000002e43f7658fd000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000001a0000000000000000000000000000000000000000000000000000000000000013500050000a7823d6f1e31569f51861e345b30c6bebf70ebe70000000000009cf6f6a78083ca3e2a662d6dd1703c939c8ace2e268d88ad09518695c6c3712ac10a214be5109a655671000927c00101006401867f7a4d000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc20000000000000000000000003f615ba21bc6cc5d4a6d798c5950cc5c42937fbd00000000000000000000000000000000000000000000000007392088b40d14000000000000000000000000000000000000000000000000000000000000000080000000000000000000000000000000000000000000000000000000000000004000000000000000000000000006c187e1b71ffbee4429003bb846c1b3eb1610000000000000000000000000000000000000000000000000000048c52ee05b140000000000000000000000000000000000000000000000000000000000000000000000000000000000000105041b1c1c1c73a08c7605fa9c69f068338cb7cd1c8dd21189cbe56f4cc66cff8dc7f0b0c8cc8c64433ea24643b893c9062beae6a05656b1df5643a242533d63925144c3e5c7dfd0509fb3c4232cfdb4c500e942a95b23439b3e18bab4a40057e1bdfae2d9967025b3f8fdca13354b25250c0d7fa9e4b472dc97df1f0cd0f595dc266d09e711628b3a63c1a6e4c83a11d3655891e31901eacf73b927e10bfbe6b0d5ed808cc228d606779a19a7dfb7393956b4fada14eaef8f6de6ee3824e67d6df18cc2d55f00cf869cc920135a94fb4abc213dc43e97812879d9efab046e4fffb931dcb55e5aa2b86f6a848408fea42cd221df99f1720b2ce22830498d78d04e1d083ba12800000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
        nonce=12,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=473,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000250d51ce33'),  # noqa: E501
                address=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000088ad09518695c6c3712ac10a214be5109a655671'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000005edcf547ece0ea1765d6c02e9e5bae53b52e09d4'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=474,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000250d51ce33'),  # noqa: E501
                address=string_to_evm_address('0x88ad09518695c6c3712AC10a214bE5109a655671'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x9afd47907e25028cdaca89d193518c302bbb128617d5a992c5abd45815526593'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000005edcf547ece0ea1765d6c02e9e5bae53b52e09d4'),  # noqa: E501
                    hexstring_to_bytes('0x00050000a7823d6f1e31569f51861e345b30c6bebf70ebe70000000000009cf9'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=6,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000001'),  # noqa: E501
                address=string_to_evm_address('0x4c36d2919e407f0cc2ee3c993ccf8ac26d9ce64e'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x27333edb8bdcd40a0ae944fb121b5e2d62ea782683946654a0f5e607a908d578'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000f6a78083ca3e2a662d6dd1703c939c8ace2e268d'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000088ad09518695c6c3712ac10a214be5109a655671'),  # noqa: E501
                    hexstring_to_bytes('0x00050000a7823d6f1e31569f51861e345b30c6bebf70ebe70000000000009cf9'),  # noqa: E501
                ],
            ),
        ],
    )

    dbethtx = DBEthTx(database)
    with database.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
        decoder = EVMTransactionDecoder(
            database=database,
            ethereum_manager=ethereum_manager,
            eth_transactions=eth_transactions,
            msg_aggregator=msg_aggregator,
        )
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)
    assert len(events) == 2
    expected_events = [
        HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x52f853d559d83b5303faf044e00e9109bd5c6a05b6633f9df34939f8e7c6de02',
            ),
            sequence_index=0,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.00393701451),
                usd_value=ZERO,
            ),
            location_label='0x5EDCf547eCE0EA1765D6C02e9E5bae53b52E09D4',
            notes='Burned 0.00393701451 ETH in gas from 0x5EDCf547eCE0EA1765D6C02e9E5bae53b52E09D4',  # noqa: E501
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x52f853d559d83b5303faf044e00e9109bd5c6a05b6633f9df34939f8e7c6de02',
            ),
            sequence_index=474,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=EvmToken('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            balance=Balance(amount=FVal('159137.254963'), usd_value=ZERO),
            location_label='0x5EDCf547eCE0EA1765D6C02e9E5bae53b52E09D4',
            notes='Bridge 159137.254963 USDC from gnosis chain',
            counterparty=CPT_GNOSIS_CHAIN,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0xdF5CEF8Dc0CEA8DC200F09280915d1CD7a016BDe']])  # noqa: E501
def test_gitcoin_claim(database, ethereum_manager, eth_transactions):
    """Data for claim taken from
    https://etherscan.io/tx/0x0e22cbdbac56c785f186bec44d715ab0834ceeadd96573c030f2fae1550b64fa
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0x0e22cbdbac56c785f186bec44d715ab0834ceeadd96573c030f2fae1550b64fa'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EthereumTransaction(
        tx_hash=evmhash,
        timestamp=1646375440,
        block_number=14351442,
        from_address='0xdF5CEF8Dc0CEA8DC200F09280915d1CD7a016BDe',
        to_address='0xDE3e5a990bCE7fC60a6f017e7c4a95fc4939299E',
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x09c5eabe000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000002e43f7658fd000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000001a0000000000000000000000000000000000000000000000000000000000000013500050000a7823d6f1e31569f51861e345b30c6bebf70ebe70000000000009cf6f6a78083ca3e2a662d6dd1703c939c8ace2e268d88ad09518695c6c3712ac10a214be5109a655671000927c00101006401867f7a4d000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc20000000000000000000000003f615ba21bc6cc5d4a6d798c5950cc5c42937fbd00000000000000000000000000000000000000000000000007392088b40d14000000000000000000000000000000000000000000000000000000000000000080000000000000000000000000000000000000000000000000000000000000004000000000000000000000000006c187e1b71ffbee4429003bb846c1b3eb1610000000000000000000000000000000000000000000000000000048c52ee05b140000000000000000000000000000000000000000000000000000000000000000000000000000000000000105041b1c1c1c73a08c7605fa9c69f068338cb7cd1c8dd21189cbe56f4cc66cff8dc7f0b0c8cc8c64433ea24643b893c9062beae6a05656b1df5643a242533d63925144c3e5c7dfd0509fb3c4232cfdb4c500e942a95b23439b3e18bab4a40057e1bdfae2d9967025b3f8fdca13354b25250c0d7fa9e4b472dc97df1f0cd0f595dc266d09e711628b3a63c1a6e4c83a11d3655891e31901eacf73b927e10bfbe6b0d5ed808cc228d606779a19a7dfb7393956b4fada14eaef8f6de6ee3824e67d6df18cc2d55f00cf869cc920135a94fb4abc213dc43e97812879d9efab046e4fffb931dcb55e5aa2b86f6a848408fea42cd221df99f1720b2ce22830498d78d04e1d083ba12800000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
        nonce=12,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=473,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000eb9078f7826f80000'),  # noqa: E501
                address=string_to_evm_address('0xDe30da39c46104798bB5aA3fe8B9e0e1F348163F'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000de3e5a990bce7fc60a6f017e7c4a95fc4939299e'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000df5cef8dc0cea8dc200f09280915d1cd7a016bde'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=6,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000018580000000000000000000000000df5cef8dc0cea8dc200f09280915d1cd7a016bde00000000000000000000000000000000000000000000000eb9078f7826f80000bcfadbb867130fed43327b6c801903ab2afb5134ba5f3d47d2647ab858d5e49e'),  # noqa: E501
                address=string_to_evm_address('0xDE3e5a990bCE7fC60a6f017e7c4a95fc4939299E'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x04672052dcb6b5b19a9cc2ec1b8f447f1f5e47b5e24cfa5e4ffb640d63ca2be7'),  # noqa: E501
                ],
            ),
        ],
    )

    dbethtx = DBEthTx(database)
    with database.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
        decoder = EVMTransactionDecoder(
            database=database,
            ethereum_manager=ethereum_manager,
            eth_transactions=eth_transactions,
            msg_aggregator=msg_aggregator,
        )
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)
    assert len(events) == 2
    expected_events = [
        HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x0e22cbdbac56c785f186bec44d715ab0834ceeadd96573c030f2fae1550b64fa',
            ),
            sequence_index=0,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.00393701451),
                usd_value=ZERO,
            ),
            location_label='0xdF5CEF8Dc0CEA8DC200F09280915d1CD7a016BDe',
            notes='Burned 0.00393701451 ETH in gas from 0xdF5CEF8Dc0CEA8DC200F09280915d1CD7a016BDe',  # noqa: E501
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x0e22cbdbac56c785f186bec44d715ab0834ceeadd96573c030f2fae1550b64fa',
            ),
            sequence_index=474,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=EvmToken('eip155:1/erc20:0xDe30da39c46104798bB5aA3fe8B9e0e1F348163F'),
            balance=Balance(amount=FVal('271.5872'), usd_value=ZERO),
            location_label='0xdF5CEF8Dc0CEA8DC200F09280915d1CD7a016BDe',
            notes='Claim 271.5872 GTC from the GTC airdrop',
            counterparty='0xDE3e5a990bCE7fC60a6f017e7c4a95fc4939299E',
        ),
    ]
    assert events == expected_events
