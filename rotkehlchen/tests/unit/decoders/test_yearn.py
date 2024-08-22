import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
from rotkehlchen.chain.ethereum.modules.yearn.constants import CPT_YEARN_V1, CPT_YEARN_V2
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_1INCH, A_ETH, A_YFI
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.decoders import patch_decoder_reload_data
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    EvmTransaction,
    Location,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes


@pytest.mark.parametrize('ethereum_accounts', [['0xb524c787669185E11d01C645D1910631e04Fa5Eb']])
def test_deposit_yearn_v2(database, ethereum_inquirer, eth_transactions):
    """
    Data taken from
    https://etherscan.io/tx/0x5d7e7646e3749fcd575ea76e35763fa8eeb6dfb83c4c242a4448ee1495f695ba
    """
    tx_hex = '0x5d7e7646e3749fcd575ea76e35763fa8eeb6dfb83c4c242a4448ee1495f695ba'
    user_address = string_to_evm_address('0xb524c787669185E11d01C645D1910631e04Fa5Eb')
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        chain_id=ChainID.ETHEREUM,
        tx_hash=evmhash,
        timestamp=Timestamp(1646375440),
        block_number=14318825,
        from_address=user_address,
        to_address=string_to_evm_address('0xdb25cA703181E7484a155DD612b06f57E12Be5F0'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xb6b55f25000000000000000000000000000000000000000000000000004de0e34960d000'),
        nonce=507,
    )
    receipt = EvmTxReceipt(
        chain_id=ChainID.ETHEREUM,
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=154,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000004ce82f9e9559fe'),
                address=string_to_evm_address('0xdb25cA703181E7484a155DD612b06f57E12Be5F0'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000b524c787669185e11d01c645d1910631e04fa5eb'),
                ],
            ), EvmTxReceiptLog(
                log_index=120,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000004de0e34960d000'),
                address=string_to_evm_address('0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000b524c787669185e11d01c645d1910631e04fa5eb'),
                    hexstring_to_bytes('0x000000000000000000000000db25ca703181e7484a155dd612b06f57e12be5f0'),
                ],
            ), EvmTxReceiptLog(
                log_index=156,
                data=hexstring_to_bytes('0xffffffffffffffffffffffffffffffffffffffffffffffffffb21f1cb69f2fff'),
                address=string_to_evm_address('0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d'),
                topics=[
                    hexstring_to_bytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'),
                    hexstring_to_bytes('0x000000000000000000000000b524c787669185e11d01c645d1910631e04fa5eb'),
                    hexstring_to_bytes('0x000000000000000000000000db25ca703181e7484a155dd612b06f57e12be5f0'),
                ],
            ),
        ],
    )

    dbethtx = DBEvmTx(database)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    with database.user_write() as cursor, patch_decoder_reload_data():
        dbethtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        decoder.reload_data(cursor)
    events, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)

    assert len(events) == 3
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
            location_label=user_address,
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=121,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_YFI,
            balance=Balance(amount=FVal('0.02192084'), usd_value=ZERO),
            location_label=user_address,
            notes='Deposit 0.02192084 YFI in yearn-v2 vault YFI yVault',
            counterparty=CPT_YEARN_V2,
            address=string_to_evm_address('0xdb25cA703181E7484a155DD612b06f57E12Be5F0'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=155,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xdb25cA703181E7484a155DD612b06f57E12Be5F0'),
            balance=Balance(amount=FVal('0.02164738945170483'), usd_value=ZERO),
            location_label=user_address,
            notes='Receive 0.02164738945170483 YFI yVault after deposit in a yearn-v2 vault',
            counterparty=CPT_YEARN_V2,
            address=ZERO_ADDRESS,
        )]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0x7b33b34D45A395518a4143846Ac40dA78CbcAA91']])
def test_withdraw_yearn_v2(database, ethereum_inquirer, eth_transactions):
    """
    Data taken from
    https://etherscan.io/tx/0xfaf3edf9fc4130e003468787d0d21cad89107bb2d648d3cd810864dd2854b76a
    """
    tx_hex = '0xfaf3edf9fc4130e003468787d0d21cad89107bb2d648d3cd810864dd2854b76a'
    user_address = string_to_evm_address('0x7b33b34D45A395518a4143846Ac40dA78CbcAA91')
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        chain_id=ChainID.ETHEREUM,
        tx_hash=evmhash,
        timestamp=Timestamp(1646375440),
        block_number=14318825,
        from_address=user_address,
        to_address=string_to_evm_address('0xB8C3B7A2A618C552C23B1E4701109a9E756Bab67'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x2e1a7d4d000000000000000000000000000000000000000000000004ace221a99fa8e6e8'),
        nonce=507,
    )
    receipt = EvmTxReceipt(
        chain_id=ChainID.ETHEREUM,
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=78,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000004ace221a99fa8e6e8'),
                address=string_to_evm_address('0xB8C3B7A2A618C552C23B1E4701109a9E756Bab67'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000007b33b34d45a395518a4143846ac40da78cbcaa91'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=79,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000005000a02dde43a18f8'),
                address=string_to_evm_address('0x111111111117dC0aa78b770fA6A738034120C302'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000b8c3b7a2a618c552c23b1e4701109a9e756bab67'),
                    hexstring_to_bytes('0x0000000000000000000000007b33b34d45a395518a4143846ac40da78cbcaa91'),
                ],
            ),
        ],
    )

    dbethtx = DBEvmTx(database)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    with database.user_write() as cursor, patch_decoder_reload_data():
        dbethtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        decoder.reload_data(cursor)
    events, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)

    assert len(events) == 3
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
            location_label=user_address,
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=79,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0xB8C3B7A2A618C552C23B1E4701109a9E756Bab67'),
            balance=Balance(amount=FVal('86.244532826510255848'), usd_value=ZERO),
            location_label=user_address,
            notes='Return 86.244532826510255848 yv1INCH to a yearn-v2 vault',
            counterparty=CPT_YEARN_V2,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=80,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:1/erc20:0x111111111117dC0aa78b770fA6A738034120C302'),
            balance=Balance(amount=FVal('92.236538270354905336'), usd_value=ZERO),
            location_label=user_address,
            notes='Withdraw 92.236538270354905336 1INCH from yearn-v2 vault 1INCH yVault',
            counterparty=CPT_YEARN_V2,
            address=string_to_evm_address('0xB8C3B7A2A618C552C23B1E4701109a9E756Bab67'),
        )]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0x3380d0FA7355a6ACB40089Db837a740c4c1dDc85']])
def test_deposit_yearn_v1(database, ethereum_inquirer, eth_transactions):
    """
    Data taken from
    https://etherscan.io/tx/0x521a39061231eb8fa7f96675a1e65f74b90350b4fedc0e430a2279945e162979
    """
    tx_hex = '0x521a39061231eb8fa7f96675a1e65f74b90350b4fedc0e430a2279945e162979'
    user_address = string_to_evm_address('0x3380d0FA7355a6ACB40089Db837a740c4c1dDc85')
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        chain_id=ChainID.ETHEREUM,
        tx_hash=evmhash,
        timestamp=Timestamp(1646375440),
        block_number=14318825,
        from_address=user_address,
        to_address=string_to_evm_address('0x5334e150B938dd2b6bd040D9c4a03Cff0cED3765'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xb6b55f250000000000000000000000000000000000000000000000000d9bb1b0ec3a2780'),
        nonce=507,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=289,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000d9bb1b0ec3a2780'),
                address=string_to_evm_address('0x49849C98ae39Fff122806C06791Fa73784FB3675'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000003380d0fa7355a6acb40089db837a740c4c1ddc85'),
                    hexstring_to_bytes('0x0000000000000000000000005334e150b938dd2b6bd040d9c4a03cff0ced3765'),
                ],
            ), EvmTxReceiptLog(
                log_index=290,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000d8eec0cf565f2e5'),
                address=string_to_evm_address('0x5334e150B938dd2b6bd040D9c4a03Cff0cED3765'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x0000000000000000000000003380d0fa7355a6acb40089db837a740c4c1ddc85'),
                ],
            ),
        ],
    )

    dbethtx = DBEvmTx(database)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    with database.user_write() as cursor, patch_decoder_reload_data():
        dbethtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        decoder.reload_data(cursor)
    events, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)

    assert len(events) == 3
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
            location_label=user_address,
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=290,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:1/erc20:0x49849C98ae39Fff122806C06791Fa73784FB3675'),
            balance=Balance(amount=FVal('0.980572717318809472'), usd_value=ZERO),
            location_label=user_address,
            notes='Deposit 0.980572717318809472 crvRenWBTC in yearn-v1 vault yearn Curve.fi renBTC/wBTC',  # noqa: E501
            counterparty=CPT_YEARN_V1,
            address=string_to_evm_address('0x5334e150B938dd2b6bd040D9c4a03Cff0cED3765'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=291,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0x5334e150B938dd2b6bd040D9c4a03Cff0cED3765'),
            balance=Balance(amount=FVal('0.976977709586838245'), usd_value=ZERO),
            location_label=user_address,
            notes='Receive 0.976977709586838245 yearn Curve.fi renBTC/wBTC after deposit in a yearn-v1 vault',  # noqa: E501
            counterparty=CPT_YEARN_V1,
            address=ZERO_ADDRESS,
        )]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0xaf7B5d7f84b7DD6b960aC6aDF2D763DD49686992']])
def test_withdraw_yearn_v1(database, ethereum_inquirer, eth_transactions):
    """
    Data taken from
    https://etherscan.io/tx/0x6f518f5160beb181f33c813bd6bdc6ebc586f18ca4eca6e24fef6309836bedee
    """
    tx_hex = '0xfaf3edf9fc4130e003468787d0d21cad89107bb2d648d3cd810864dd2854b76a'
    user_address = string_to_evm_address('0xaf7B5d7f84b7DD6b960aC6aDF2D763DD49686992')
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1646375440),
        block_number=14318825,
        from_address=user_address,
        to_address=string_to_evm_address('0x5334e150B938dd2b6bd040D9c4a03Cff0cED3765'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x2e1a7d4d00000000000000000000000000000000000000000000000001811d39c5a70000'),
        nonce=507,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=78,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000001811d39c5a70000'),
                address=string_to_evm_address('0x5334e150B938dd2b6bd040D9c4a03Cff0cED3765'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000af7b5d7f84b7dd6b960ac6adf2d763dd49686992'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=79,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000186a6aeafe845e8'),
                address=string_to_evm_address('0x49849C98ae39Fff122806C06791Fa73784FB3675'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000005334e150b938dd2b6bd040d9c4a03cff0ced3765'),
                    hexstring_to_bytes('0x000000000000000000000000af7b5d7f84b7dd6b960ac6adf2d763dd49686992'),
                ],
            ),
        ],
    )

    dbethtx = DBEvmTx(database)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    with database.user_write() as cursor, patch_decoder_reload_data():
        dbethtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        decoder.reload_data(cursor)
    events, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)

    assert len(events) == 3
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
            location_label=user_address,
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=79,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0x5334e150B938dd2b6bd040D9c4a03Cff0cED3765'),
            balance=Balance(amount=FVal('0.1084'), usd_value=ZERO),
            location_label=user_address,
            notes='Return 0.1084 yvcrvRenWBTC to a yearn-v1 vault',
            counterparty=CPT_YEARN_V1,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=80,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:1/erc20:0x49849C98ae39Fff122806C06791Fa73784FB3675'),
            balance=Balance(amount=FVal('0.109958510122911208'), usd_value=ZERO),
            location_label=user_address,
            notes='Withdraw 0.109958510122911208 crvRenWBTC from yearn-v1 vault yearn Curve.fi renBTC/wBTC',  # noqa: E501
            counterparty=CPT_YEARN_V1,
            address=string_to_evm_address('0x5334e150B938dd2b6bd040D9c4a03Cff0cED3765'),
        )]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xfDb7EEc5eBF4c4aC7734748474123aC25C6eDCc8']])
def test_deposit_yearn_full_amount(ethereum_inquirer, ethereum_accounts):
    """
    In the case of deposits and withdrawals for yearn there are two different signatures for
    the functions used. If no amount is provided all the available amount is deposited/withdrawn.
    """
    tx_hex = deserialize_evm_tx_hash('0x02486ccc1fe49b3c7df60c51efad78ddca5af025834e30ba1a736ff352b33592')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hex)
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1614241909000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.0108951),
                usd_value=ZERO,
            ),
            location_label=user_address,
            notes='Burned 0.0108951 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=222,
            timestamp=TimestampMS(1614241909000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xB8C3B7A2A618C552C23B1E4701109a9E756Bab67'),
            balance=Balance(amount=FVal('484.583645343659242764'), usd_value=ZERO),
            location_label=user_address,
            notes='Receive 484.583645343659242764 1INCH yVault after deposit in a yearn-v2 vault',
            counterparty=CPT_YEARN_V2,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=223,
            timestamp=TimestampMS(1614241909000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_1INCH,
            balance=Balance(amount=FVal('485.291731449267028361'), usd_value=ZERO),
            location_label=user_address,
            notes='Deposit 485.291731449267028361 1INCH in yearn-v2 vault 1INCH yVault',
            counterparty=CPT_YEARN_V2,
            address=string_to_evm_address('0xB8C3B7A2A618C552C23B1E4701109a9E756Bab67'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=224,
            timestamp=TimestampMS(1614241909000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_1INCH,
            balance=Balance(amount=FVal('115792089237316195423570985008687907853269984665640564038972.292276463862611574'), usd_value=ZERO),  # noqa: E501
            location_label=user_address,
            notes='Set 1INCH spending approval of 0xfDb7EEc5eBF4c4aC7734748474123aC25C6eDCc8 by 0xB8C3B7A2A618C552C23B1E4701109a9E756Bab67 to 115792089237316195423570985008687907853269984665640564038972.292276463862611574',  # noqa: E501
            counterparty=None,
            address=string_to_evm_address('0xB8C3B7A2A618C552C23B1E4701109a9E756Bab67'),
        ),
    ]
