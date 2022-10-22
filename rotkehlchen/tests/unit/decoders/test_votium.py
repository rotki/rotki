import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt, EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.fval import FVal
from rotkehlchen.types import EvmTransaction, Location, deserialize_evm_tx_hash
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.hexbytes import hexstring_to_bytes


@pytest.mark.parametrize('ethereum_accounts', [['0x362C51b56D3c8f79aecf367ff301d1aFd42EDCEA']])  # noqa: E501
def test_votium_claim(database, ethereum_manager, eth_transactions):
    """Data for claim taken from
    https://etherscan.io/tx/0x75b81b2edd454a7b564cc55a6b676e2441e155401bde99a38d867028081d2c30
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0x75b81b2edd454a7b564cc55a6b676e2441e155401bde99a38d867028081d2c30'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        timestamp=1646375440,
        block_number=14318825,
        from_address='0x362C51b56D3c8f79aecf367ff301d1aFd42EDCEA',
        to_address='0x378Ba9B73309bE80BF4C2c027aAD799766a7ED5A',
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x12d18ed60000000000000000000000003432b6a60d23ca0dfca7761b7ab56459d9c964d00000000000000000000000000000000000000000000000000000000000000299000000000000000000000000362c51b56d3c8f79aecf367ff301d1afd42edcea000000000000000000000000000000000000000000000000aba7e67d21ab400000000000000000000000000000000000000000000000000000000000000000a0000000000000000000000000000000000000000000000000000000000000000c0e18ed60844ddec0806bec1c24f10dbda658b3b75a3acb240c22b16b3ff468ace3436e89dee076858d556836040ac7af381d0a234c88318b1dc9d40e84f18243fadf3873bf723871fd88283fe1e9620aef4a1dfff0726d62bcd948314158d22409bd1a16812ff67f9499edef76951b0e1229d5f44cde7bce8ecbcf7ae3754bdf9e0a81af4a9bfe0e9bd0aa8a7dcc056b7479a753aa00ed08b23592eedd8731ec77f2b3cbb78e410486cabd6ab54f3830aa53ab66b9cf50e8a5eaae4465b51dc1cf9d6435d85ac3f55637eb1645df08065fb45cdf9d4a73489086ff005b515c2f04fc96780a5e63605d76a9bc9b984be1cdfbffb8b65181b5756de1ada5ac4f06e33647161699cb812487337b74b45fa4b2a8445e405896e6e0794aa8d998d7d5f4e795b5091f40b0494afbabf6597b73cd051f7c02b72c61eb72544915643a48ec1c2627e04b9d8e0ff748e3b417e6c0e302c4992f406b35b57253583b2913b61cda2f4b7d93800ab88f2405227c0fc34307aac6b884475a4c79cad7af300539'),  # noqa: E501
        nonce=635,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=350,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000aba7e67d21ab4000'),  # noqa: E501
                address=string_to_evm_address('0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000378ba9b73309be80bf4c2c027aad799766a7ed5a'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000362c51b56d3c8f79aecf367ff301d1afd42edcea'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=351,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000299000000000000000000000000000000000000000000000000aba7e67d21ab4000'),  # noqa: E501
                address=string_to_evm_address('0x378Ba9B73309bE80BF4C2c027aAD799766a7ED5A'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x4766921f5c59646d22d7d266a29164c8e9623684d8dfdbd931731dfdca025238'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000003432b6a60d23ca0dfca7761b7ab56459d9c964d0'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000362c51b56d3c8f79aecf367ff301d1afd42edcea'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000017'),  # noqa: E501
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
        transactions=eth_transactions,
        msg_aggregator=msg_aggregator,
    )
    with database.user_write() as cursor:
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)
    assert len(events) == 2
    expected_events = [
        HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x75b81b2edd454a7b564cc55a6b676e2441e155401bde99a38d867028081d2c30',
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
            location_label='0x362C51b56D3c8f79aecf367ff301d1aFd42EDCEA',
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x75b81b2edd454a7b564cc55a6b676e2441e155401bde99a38d867028081d2c30',
            ),
            sequence_index=351,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=EvmToken('eip155:1/erc20:0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0'),
            balance=Balance(amount=FVal('12.369108326706528256'), usd_value=ZERO),
            location_label='0x362C51b56D3c8f79aecf367ff301d1aFd42EDCEA',
            notes='Receive 12.369108326706528256 FXS from votium bribe',
            counterparty='votium',
        )]
    assert events == expected_events
