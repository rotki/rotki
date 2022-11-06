import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.ens.constants import CPT_ENS
from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt, EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    EvmTokenKind,
    EvmTransaction,
    Location,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes

ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'


@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_mint_ens_name(database, ethereum_manager, function_scope_messages_aggregator):
    """Data taken from
    https://etherscan.io/tx/0x74e72600c6cd5a1f0170a3ca38ecbf7d59edeb8ceb48adab2ed9b85d12cc2b99
    """
    # TODO: For faster tests hard-code the transaction and the logs here so no remote query needed
    tx_hash = deserialize_evm_tx_hash('0x74e72600c6cd5a1f0170a3ca38ecbf7d59edeb8ceb48adab2ed9b85d12cc2b99')  # noqa: E501
    events, decoder = get_decoded_events_of_transaction(
        ethereum_manager=ethereum_manager,
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        tx_hash=tx_hash,
    )
    expires_timestamp = 2142055301
    expected_events = [
        HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=1637144069000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.023654025517055036')),
            location_label=ADDY,
            notes='Burned 0.023654025517055036 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=2,
            timestamp=1637144069000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.021279711243535527')),
            location_label=ADDY,
            notes=f'Register ENS name hania.eth for 0.019345192039577752 ETH until {decoder.decoders["Ens"].timestamp_to_date(expires_timestamp)}',  # noqa: E501
            counterparty=CPT_ENS,
        )]
    assert expected_events == events[0:2]
    erc721_asset = get_or_create_evm_token(  # TODO: Better way to test than this for ERC721 ...?
        userdb=database,
        evm_address='0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85',
        chain=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC721,
        ethereum_manager=ethereum_manager,
    )
    assert events[2] == HistoryBaseEntry(
        event_identifier=tx_hash,
        sequence_index=47,
        timestamp=1637144069000,
        location=Location.BLOCKCHAIN,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=erc721_asset,
        balance=Balance(amount=ONE),
        location_label=ADDY,
        notes='Receive ENS name ERC721 token for hania.eth with id 88045077199635585930173998576189366882372899073811035545363728149974713265418',  # noqa: E501
        counterparty=CPT_ENS,
        extra_data={
            'token_id': 88045077199635585930173998576189366882372899073811035545363728149974713265418,  # noqa: E501
            'token_name': 'ERC721 token',
        },
    )


@pytest.mark.parametrize('ethereum_accounts', [['0x4bBa290826C253BD854121346c370a9886d1bC26']])  # noqa: E501
def test_text_changed(evm_transaction_decoder, ethereum_accounts):
    """
    Data taken from
    https://etherscan.io/tx/0xaa59cb2029651d2ed2c0d1ee34b9b88f0b90278fc6da5b51446d4abf24d7f598
    """
    tx_hash = deserialize_evm_tx_hash('0xaa59cb2029651d2ed2c0d1ee34b9b88f0b90278fc6da5b51446d4abf24d7f598')  # noqa: E501
    transaction = EvmTransaction(
        tx_hash=tx_hash,
        timestamp=0,
        block_number=0,
        from_address=ethereum_accounts[0],
        to_address='0x4976fb03C32e5B8cfe2b6cCB31c09Ba78EBaBa41',
        value=ZERO,
        gas=0,
        gas_price=0,
        gas_used=0,
        input_data=b'',
        nonce=0,
    )
    receipt = EthereumTxReceipt(
        tx_hash=tx_hash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=289,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000375726c0000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                address=string_to_evm_address('0x4976fb03C32e5B8cfe2b6cCB31c09Ba78EBaBa41'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xd8c9334b1a9c2f9da342a0a2b32629c1a229b6445dad78947f674b44444a7550'),  # noqa: E501
                    hexstring_to_bytes('0x3b0f515e5cdd012547353abc42e419c23a4f3f0d78c3ba681a942d7ed618f5cd'),  # noqa: E501
                    hexstring_to_bytes('0xb68b5f5089998f2978a1dcc681e8ef27962b90d5c26c4c0b9c1945814ffa5ef0'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=290,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000066176617461720000000000000000000000000000000000000000000000000000'),  # noqa: E501
                address=string_to_evm_address('0x4976fb03C32e5B8cfe2b6cCB31c09Ba78EBaBa41'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xd8c9334b1a9c2f9da342a0a2b32629c1a229b6445dad78947f674b44444a7550'),  # noqa: E501
                    hexstring_to_bytes('0x3b0f515e5cdd012547353abc42e419c23a4f3f0d78c3ba681a942d7ed618f5cd'),  # noqa: E501
                    hexstring_to_bytes('0xd1f86c93d831119ad98fe983e643a7431e4ac992e3ead6e3007f4dd1adf66343'),  # noqa: E501
                ],
            ),
        ],
    )

    dbethtx = DBEthTx(evm_transaction_decoder.database)
    with dbethtx.db.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
        events = evm_transaction_decoder.decode_transaction(
            write_cursor=cursor,
            transaction=transaction,
            tx_receipt=receipt,
        )
    expected_events = [
        HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(),
            location_label='0x4bBa290826C253BD854121346c370a9886d1bC26',
            notes='Burned 0 ETH for gas',
            counterparty='gas',
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=290,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label='0x4bBa290826C253BD854121346c370a9886d1bC26',
            notes='Set ENS url attribute for nebolax.eth',
            counterparty='ens',
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=291,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label='0x4bBa290826C253BD854121346c370a9886d1bC26',
            notes='Set ENS avatar attribute for nebolax.eth',
            counterparty='ens',
            identifier=None,
            extra_data=None,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0x4bBa290826C253BD854121346c370a9886d1bC26']])  # noqa: E501
def test_set_resolver(evm_transaction_decoder, ethereum_accounts):
    """
    Data taken from
    https://etherscan.io/tx/0xae2cd848ce02c425bc50a8f46f8430eec32234475efb6fcff28315d2791329f6
    """
    tx_hash = deserialize_evm_tx_hash('0xae2cd848ce02c425bc50a8f46f8430eec32234475efb6fcff28315d2791329f6')  # noqa: E501
    transaction = EvmTransaction(
        tx_hash=tx_hash,
        timestamp=0,
        block_number=0,
        from_address=ethereum_accounts[0],
        to_address='0x084b1c3C81545d370f3634392De611CaaBFf8148',
        value=ZERO,
        gas=0,
        gas_price=0,
        gas_used=0,
        input_data=b'',
        nonce=0,
    )
    receipt = EthereumTxReceipt(
        tx_hash=tx_hash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=269,
                data=hexstring_to_bytes('0x000000000000000000000000084b1c3c81545d370f3634392de611caabff8148'),  # noqa: E501
                address=string_to_evm_address('0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xce0457fe73731f824cc272376169235128c118b49d344817417c6d108d155e82'),  # noqa: E501
                    hexstring_to_bytes('0x91d1777781884d03a6757a803996e38de2a42967fb37eeaca72729271025a9e2'),  # noqa: E501
                    hexstring_to_bytes('0xa5809490c7b97cf8ebf6dd2d9667569d617a4fdcccaf3dd7b4e74fbcdeda8fb0'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=270,
                data=hexstring_to_bytes('0x000000000000000000000000a2c122be93b0074270ebee7f6b7292c7deb45047'),  # noqa: E501
                address=string_to_evm_address('0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x335721b01866dc23fbee8b6b2c7b1e14d6f05c28cd35a2c934239f94095602a0'),  # noqa: E501
                    hexstring_to_bytes('0x9c74c6eee8c468cc09629fac3a5d83791d48b57b4f8ec0841dd847fd6f0a1d20'),  # noqa: E501
                ],
            ),
        ],
    )

    dbethtx = DBEthTx(evm_transaction_decoder.database)
    with dbethtx.db.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
        events = evm_transaction_decoder.decode_transaction(
            write_cursor=cursor,
            transaction=transaction,
            tx_receipt=receipt,
        )

    expected_events = [
        HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(),
            location_label='0x4bBa290826C253BD854121346c370a9886d1bC26',
            notes='Burned 0 ETH for gas',
            counterparty='gas',
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=271,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(amount=ZERO, usd_value=ZERO),
            location_label='0x4bBa290826C253BD854121346c370a9886d1bC26',
            notes='Set ENS address for nebolax.eth',
            counterparty='ens',
            identifier=None,
            extra_data=None,
        ),
    ]
    assert events == expected_events
