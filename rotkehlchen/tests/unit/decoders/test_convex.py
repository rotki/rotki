import warnings as test_warnings

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import (
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.constants import ZERO_ADDRESS
from rotkehlchen.chain.ethereum.contracts import EthereumContract
from rotkehlchen.chain.ethereum.decoding import EVMTransactionDecoder
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.convex.constants import CONVEX_POOLS, CPT_CONVEX
from rotkehlchen.chain.ethereum.modules.convex.decoder import BOOSTER
from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt, EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.chain.ethereum.utils import multicall
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_CRV, A_CVX, A_ETH
from rotkehlchen.constants.ethereum import EthereumConstants
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.fval import FVal
from rotkehlchen.types import EthereumTransaction, Location, deserialize_evm_tx_hash
from rotkehlchen.utils.hexbytes import hexstring_to_bytes
from rotkehlchen.utils.misc import hex_or_bytes_to_address


def test_convex_pools(ethereum_manager):
    """Tests that our hardcoded information about convex pools is up-to-date.
    Queries data about convex pools reward addresses and their names from chain and compares it
    to the current hardcoded info."""
    booster_contract = EthereumConstants.contract('CONVEX_BOOSTER')
    pools_count = booster_contract.call(
        ethereum=ethereum_manager,
        method_name='poolLength',
    )
    calls_to_booster = []
    for i in range(pools_count):
        calls_to_booster.append(
            (
                booster_contract.address,
                booster_contract.encode('poolInfo', [i]),
            ),
        )
    booster_result = multicall(
        ethereum=ethereum_manager,
        calls=calls_to_booster,
    )
    convex_rewards_addrs = []
    convex_lp_tokens_addrs = []
    lp_tokens_contract = EthereumContract(  # only need it to encode and decode
        address=ZERO_ADDRESS,
        abi=EthereumConstants.abi('CONVEX_LP_TOKEN'),
        deployed_block=0,
    )
    for single_booster_result in booster_result:
        lp_token_addr = hex_or_bytes_to_address(single_booster_result[0:32])
        crv_rewards = hex_or_bytes_to_address(single_booster_result[3 * 32:4 * 32])
        convex_rewards_addrs.append(crv_rewards)
        convex_lp_tokens_addrs.append(lp_token_addr)

    # We query this info from chain instead of using data from our assets database since
    # if convex adds a new pool with new lp token we won't know its properties (because it won't
    # be in our DB)
    calls_to_lp_tokens = []
    for lp_token_addr in convex_lp_tokens_addrs:
        calls_to_lp_tokens.append((lp_token_addr, lp_tokens_contract.encode('symbol')))

    lp_tokens_result = multicall(
        ethereum=ethereum_manager,
        calls=calls_to_lp_tokens,
    )

    queried_convex_pools_info = {}
    for convex_reward_addr, single_lp_token_result in zip(convex_rewards_addrs, lp_tokens_result):
        decoded_lp_token_result = lp_tokens_contract.decode(single_lp_token_result, 'symbol')
        queried_convex_pools_info[convex_reward_addr] = decoded_lp_token_result[0]  # pylint: disable=unsubscriptable-object  # noqa: E501

    if CONVEX_POOLS != queried_convex_pools_info:
        added_pools_addrs = queried_convex_pools_info.keys() - CONVEX_POOLS.keys()
        added_pools = {addr: queried_convex_pools_info[addr] for addr in added_pools_addrs}
        test_warnings.warn(UserWarning(
            f'Convex pools have changed on chain. Please update CONVEX_POOLS constant. '
            f'New pools: {added_pools}',
        ))


@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0xC960338B529e0353F570f62093Fd362B8FB55f0B')]])  # noqa: E501
def test_booster_deposit(database, ethereum_manager, eth_transactions):
    msg_aggregator = database.msg_aggregator
    tx_hex = '0x8f643dc245ce64085197692ed98309a94fd176a1e7394e8967ae7bfa10ad1f8f'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = string_to_evm_address('0xC960338B529e0353F570f62093Fd362B8FB55f0B')
    transaction = EthereumTransaction(
        tx_hash=evmhash,
        timestamp=0,
        block_number=0,
        from_address=user_address,
        to_address=BOOSTER,
        value=0,
        gas=0,
        gas_price=0,
        gas_used=0,
        input_data=b'',
        nonce=0,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=460,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000003776765d951ea680'),  # noqa: E501
                address=string_to_evm_address('0x06325440D014e39736583c165C2963BA99fAf14E'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c960338b529e0353f570f62093fd362b8fb55f0b'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000989aeb4d175e16225e39e87d0d97a3360524ad80'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=480,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000003776765d951ea680'),  # noqa: E501
                address=string_to_evm_address('0xF403C135812408BFbE8713b5A23a04b3D48AAE31'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x73a19dd210f1a7f902193214c0ee91dd35ee5b4d920cba8d519eca65a7b488ca'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c960338b529e0353f570f62093fd362b8fb55f0b'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000019'),  # noqa: E501
                ],
            ),
        ],
    )
    dbethtx = DBEthTx(database)
    with dbethtx.db.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
    decoder = EVMTransactionDecoder(
        database=database,
        ethereum_manager=ethereum_manager,
        eth_transactions=eth_transactions,
        msg_aggregator=msg_aggregator,
    )
    with dbethtx.db.user_write() as cursor:
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=ZERO, usd_value=ZERO),
            location_label='0xC960338B529e0353F570f62093Fd362B8FB55f0B',
            notes='Burned 0 ETH in gas from 0xC960338B529e0353F570f62093Fd362B8FB55f0B',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=461,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.NONE,
            asset=EvmToken('eip155:1/erc20:0x06325440D014e39736583c165C2963BA99fAf14E'),
            balance=Balance(amount=FVal('3.996511863643743872'), usd_value=ZERO),
            location_label='0xC960338B529e0353F570f62093Fd362B8FB55f0B',
            notes='Deposit 3.996511863643743872 steCRV into convex',
            counterparty=CPT_CONVEX,
            identifier=None,
            extra_data=None,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0x53913A03a065f685097f8E8f40284D58016bB0F9')]])  # noqa: E501
def test_booster_withdraw(database, ethereum_manager, eth_transactions):
    msg_aggregator = database.msg_aggregator
    tx_hex = '0x79fcbafa4367e0563d3e614f774c5e4257c4e41f124ae8288980a310e2b2b547'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = string_to_evm_address('0x53913A03a065f685097f8E8f40284D58016bB0F9')
    transaction = EthereumTransaction(
        tx_hash=evmhash,
        timestamp=0,
        block_number=0,
        from_address=user_address,
        to_address=BOOSTER,
        value=0,
        gas=0,
        gas_price=0,
        gas_used=0,
        input_data=b'',
        nonce=0,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=222,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000013c034ea5da775d341'),  # noqa: E501
                address=string_to_evm_address('0xCB6D873f7BbE57584a9b08380901Dc200Be7CE74'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000053913a03a065f685097f8e8f40284d58016bb0f9'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=228,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000013c034ea5da775d341'),  # noqa: E501
                address=string_to_evm_address('0xF3A43307DcAFa93275993862Aae628fCB50dC768'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000f403c135812408bfbe8713b5a23a04b3d48aae31'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000053913a03a065f685097f8e8f40284d58016bb0f9'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=229,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000013c034ea5da775d341'),  # noqa: E501
                address=string_to_evm_address('0xF403C135812408BFbE8713b5A23a04b3D48AAE31'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x92ccf450a286a957af52509bc1c9939d1a6a481783e142e41e2499f0bb66ebc6'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000053913a03a065f685097f8e8f40284d58016bb0f9'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000048'),  # noqa: E501
                ],
            ),
        ],
    )
    dbethtx = DBEthTx(database)
    with dbethtx.db.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
    decoder = EVMTransactionDecoder(
        database=database,
        ethereum_manager=ethereum_manager,
        eth_transactions=eth_transactions,
        msg_aggregator=msg_aggregator,
    )
    with dbethtx.db.user_write() as cursor:
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=ZERO, usd_value=ZERO),
            location_label='0x53913A03a065f685097f8E8f40284D58016bB0F9',
            notes='Burned 0 ETH in gas from 0x53913A03a065f685097f8E8f40284D58016bB0F9',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=223,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0xCB6D873f7BbE57584a9b08380901Dc200Be7CE74'),
            balance=Balance(amount=FVal('364.338089842514973505'), usd_value=ZERO),
            location_label='0x53913A03a065f685097f8E8f40284D58016bB0F9',
            notes='Return 364.338089842514973505 cvxcvxFXSFXS-f to convex',
            counterparty=CPT_CONVEX,
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=229,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=EvmToken('eip155:1/erc20:0xF3A43307DcAFa93275993862Aae628fCB50dC768'),
            balance=Balance(amount=FVal('364.338089842514973505'), usd_value=ZERO),
            location_label='0x53913A03a065f685097f8E8f40284D58016bB0F9',
            notes='Withdraw 364.338089842514973505 cvxFXSFXS-f from convex',
            counterparty=CPT_CONVEX,
            identifier=None,
            extra_data=None,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0xFb305A40Dac406BdCF3b85F6311e5430770f44bA')]])  # noqa: E501
def test_cvxcrv_get_reward(database, ethereum_manager, eth_transactions):
    msg_aggregator = database.msg_aggregator
    tx_hex = '0x5e62ce39159fcdf528905d044e5387c8f21a1eca015d08cebc652bfb9c183611'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = string_to_evm_address('0xFb305A40Dac406BdCF3b85F6311e5430770f44bA')
    transaction = EthereumTransaction(
        tx_hash=evmhash,
        timestamp=1655675488,
        block_number=14998088,
        from_address=user_address,
        to_address=string_to_evm_address('0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x7050ccd9000000000000000000000000fb305a40dac406bdcf3b85f6311e5430770f44ba0000000000000000000000000000000000000000000000000000000000000001'),  # noqa: E501
        nonce=507,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=449,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000002eac6340ad673319bb'),  # noqa: E501
                address=string_to_evm_address('0xD533a949740bb3306d119CC777fa900bA034cd52'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000003fe65692bfcd0e6cf84cb1e7d24108e434a7587e'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000fb305a40dac406bdcf3b85f6311e5430770f44ba'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=450,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000003f79cea9e196976aa'),  # noqa: E501
                address=string_to_evm_address('0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000fb305a40dac406bdcf3b85f6311e5430770f44ba'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=451,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000002eac6340ad673319bb'),  # noqa: E501
                address=string_to_evm_address('0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xe2403640ba68fed3a2f88b7557551d1993f84b99bb10ff833f0cf8db0c5e0486'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000fb305a40dac406bdcf3b85f6311e5430770f44ba'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=452,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000001fd601592884f765d9'),  # noqa: E501
                address=string_to_evm_address('0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007091dbb7fcba54569ef1387ac89eb2a5c9f6d2ea'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000fb305a40dac406bdcf3b85f6311e5430770f44ba'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=453,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000001fd601592884f765d9'),  # noqa: E501
                address=string_to_evm_address('0x7091dbb7fcbA54569eF1387Ac89Eb2a5C9F6d2EA'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xe2403640ba68fed3a2f88b7557551d1993f84b99bb10ff833f0cf8db0c5e0486'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000fb305a40dac406bdcf3b85f6311e5430770f44ba'),  # noqa: E501
                ],
            ),
        ],
    )
    dbethtx = DBEthTx(database)
    with dbethtx.db.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
    decoder = EVMTransactionDecoder(
        database=database,
        ethereum_manager=ethereum_manager,
        eth_transactions=eth_transactions,
        msg_aggregator=msg_aggregator,
    )
    with dbethtx.db.user_write() as cursor:
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=1655675488000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.00393701451'), usd_value=ZERO),
            location_label='0xFb305A40Dac406BdCF3b85F6311e5430770f44bA',
            notes='Burned 0.00393701451 ETH in gas from 0xFb305A40Dac406BdCF3b85F6311e5430770f44bA',  # noqa: E501
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=450,
            timestamp=1655675488000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_CRV,
            balance=Balance(amount=FVal('860.972070701362256315'), usd_value=ZERO),
            location_label='0xFb305A40Dac406BdCF3b85F6311e5430770f44bA',
            notes='Claim 860.972070701362256315 CRV reward from convex',
            counterparty=CPT_CONVEX,
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=451,
            timestamp=1655675488000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_CVX,
            balance=Balance(amount=FVal('73.182626009615791786'), usd_value=ZERO),
            location_label='0xFb305A40Dac406BdCF3b85F6311e5430770f44bA',
            notes='Claim 73.182626009615791786 CVX reward from convex',
            counterparty=CPT_CONVEX,
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=453,
            timestamp=1655675488000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=EvmToken('eip155:1/erc20:0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490'),  # name='Curve.fi DAI/USDC/USDT', symbol='3Crv'  # noqa: E501
            balance=Balance(amount=FVal('587.269770914653758937'), usd_value=ZERO),
            location_label='0xFb305A40Dac406BdCF3b85F6311e5430770f44bA',
            notes='Claim 587.269770914653758937 3Crv reward from convex',
            counterparty=CPT_CONVEX,
            identifier=None,
            extra_data=None,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0xe81FC42336c9314A9Be1EDB3F50eA9e275C93df3')]])  # noqa: E501
def test_cvxcrv_withdraw(database, ethereum_manager, eth_transactions):
    msg_aggregator = database.msg_aggregator
    tx_hex = '0x0a804804cc62f615b72dff55e8c245d9b69aa8f8ed3de549101ae128a4ae432b'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = string_to_evm_address('0xe81FC42336c9314A9Be1EDB3F50eA9e275C93df3')
    transaction = EthereumTransaction(
        tx_hash=evmhash,
        timestamp=0,
        block_number=0,
        from_address=user_address,
        to_address=string_to_evm_address('0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e'),
        value=0,
        gas=0,
        gas_price=0,
        gas_used=0,
        input_data=b'',
        nonce=0,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=422,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000003542cabeb617ec713f3'),  # noqa: E501
                address=string_to_evm_address('0x7091dbb7fcbA54569eF1387Ac89Eb2a5C9F6d2EA'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x7084f5476618d8e60b11ef0d7d3f06914655adb8793e28ff7f018d4c76d505d5'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000e81fc42336c9314a9be1edb3f50ea9e275c93df3'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=423,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000003542cabeb617ec713f3'),  # noqa: E501
                address=string_to_evm_address('0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000003fe65692bfcd0e6cf84cb1e7d24108e434a7587e'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000e81fc42336c9314a9be1edb3f50ea9e275c93df3'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=424,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000003542cabeb617ec713f3'),  # noqa: E501
                address=string_to_evm_address('0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x7084f5476618d8e60b11ef0d7d3f06914655adb8793e28ff7f018d4c76d505d5'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000e81fc42336c9314a9be1edb3f50ea9e275c93df3'),  # noqa: E501
                ],
            ),
        ],
    )
    dbethtx = DBEthTx(database)
    with dbethtx.db.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
    decoder = EVMTransactionDecoder(
        database=database,
        ethereum_manager=ethereum_manager,
        eth_transactions=eth_transactions,
        msg_aggregator=msg_aggregator,
    )
    with dbethtx.db.user_write() as cursor:
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=ZERO, usd_value=ZERO),
            location_label='0xe81FC42336c9314A9Be1EDB3F50eA9e275C93df3',
            notes='Burned 0 ETH in gas from 0xe81FC42336c9314A9Be1EDB3F50eA9e275C93df3',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=424,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=EvmToken('eip155:1/erc20:0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
            balance=Balance(amount=FVal('15719.844875963195659251'), usd_value=ZERO),
            location_label='0xe81FC42336c9314A9Be1EDB3F50eA9e275C93df3',
            notes='Withdraw 15719.844875963195659251 cvxCRV from convex',  # noqa: E501
            counterparty=CPT_CONVEX,
            identifier=None,
            extra_data=None,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0x2AcEcBF2Ee5BFc8eed599D58835EE9A7c45F3E2c')]])  # noqa: E501
def test_cvxcrv_stake(database, ethereum_manager, eth_transactions):
    msg_aggregator = database.msg_aggregator
    tx_hex = '0x3cc0b25887e2f0dac7f86fabd81aaafb1e041e84dbe8167885073c443320ad5f'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = string_to_evm_address('0x2AcEcBF2Ee5BFc8eed599D58835EE9A7c45F3E2c')
    transaction = EthereumTransaction(
        tx_hash=evmhash,
        timestamp=0,
        block_number=0,
        from_address=user_address,
        to_address=string_to_evm_address('0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e'),
        value=0,
        gas=0,
        gas_price=0,
        gas_used=0,
        input_data=b'',  # noqa: E501
        nonce=0,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=425,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000009057b68d9eaa306ba'),  # noqa: E501
                address=string_to_evm_address('0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000002acecbf2ee5bfc8eed599d58835ee9a7c45f3e2c'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000003fe65692bfcd0e6cf84cb1e7d24108e434a7587e'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=426,
                data=hexstring_to_bytes('0xffffffffffffffffffffffffffffffffffffffffffffff0ede5ad67232e75534'),  # noqa: E501
                address=string_to_evm_address('0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000002acecbf2ee5bfc8eed599d58835ee9a7c45f3e2c'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000003fe65692bfcd0e6cf84cb1e7d24108e434a7587e'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=427,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000009057b68d9eaa306ba'),  # noqa: E501
                address=string_to_evm_address('0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x9e71bc8eea02a63969f509818f2dafb9254532904319f9dbda79b67bd34a5f3d'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000002acecbf2ee5bfc8eed599d58835ee9a7c45f3e2c'),  # noqa: E501
                ],
            ),
        ],
    )
    dbethtx = DBEthTx(database)
    with dbethtx.db.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
    decoder = EVMTransactionDecoder(
        database=database,
        ethereum_manager=ethereum_manager,
        eth_transactions=eth_transactions,
        msg_aggregator=msg_aggregator,
    )
    with dbethtx.db.user_write() as cursor:
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=ZERO, usd_value=ZERO),
            location_label='0x2AcEcBF2Ee5BFc8eed599D58835EE9A7c45F3E2c',
            notes='Burned 0 ETH in gas from 0x2AcEcBF2Ee5BFc8eed599D58835EE9A7c45F3E2c',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=426,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.NONE,
            asset=EvmToken('eip155:1/erc20:0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
            balance=Balance(amount=FVal('166.415721340864759482'), usd_value=ZERO),
            location_label='0x2AcEcBF2Ee5BFc8eed599D58835EE9A7c45F3E2c',
            notes='Deposit 166.415721340864759482 cvxCRV into convex',
            counterparty=CPT_CONVEX,
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=427,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=EvmToken('eip155:1/erc20:0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
            balance=Balance(amount=FVal('1.157920892373161954235709850E+59'), usd_value=ZERO),
            location_label='0x2AcEcBF2Ee5BFc8eed599D58835EE9A7c45F3E2c',
            notes='Approve 1.157920892373161954235709850E+59 cvxCRV of 0x2AcEcBF2Ee5BFc8eed599D58835EE9A7c45F3E2c for spending by 0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e',  # noqa: E501
            counterparty='0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e',
            identifier=None,
            extra_data=None,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0x5B186c93A50D3CB435fE2933427d36E6Dc688e4b')]])  # noqa: E501
def test_cvx_stake(database, ethereum_manager, eth_transactions):
    msg_aggregator = database.msg_aggregator
    tx_hex = '0xc33246acb86798b81fe650061061d32751c53879d46ece6991fb4a3eda808103'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = string_to_evm_address('0x5B186c93A50D3CB435fE2933427d36E6Dc688e4b')
    transaction = EthereumTransaction(
        tx_hash=evmhash,
        timestamp=0,
        block_number=0,
        from_address=user_address,
        to_address=string_to_evm_address('0xCF50b810E57Ac33B91dCF525C6ddd9881B139332'),
        value=0,
        gas=0,
        gas_price=0,
        gas_used=0,
        input_data=b'',
        nonce=0,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=342,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000de0b6b3a7640000'),  # noqa: E501
                address=A_CVX.evm_address,
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000005b186c93a50d3cb435fe2933427d36e6dc688e4b'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000cf50b810e57ac33b91dcf525c6ddd9881b139332'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=343,
                data=hexstring_to_bytes('0xfffffffffffffffffffffffffffffffffffffffffffffffff21f494c589bffff'),  # noqa: E501
                address=A_CVX.evm_address,
                removed=False,
                topics=[
                    hexstring_to_bytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000005b186c93a50d3cb435fe2933427d36e6dc688e4b'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000cf50b810e57ac33b91dcf525c6ddd9881b139332'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=344,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000de0b6b3a7640000'),  # noqa: E501
                address=string_to_evm_address('0xCF50b810E57Ac33B91dCF525C6ddd9881B139332'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x9e71bc8eea02a63969f509818f2dafb9254532904319f9dbda79b67bd34a5f3d'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000005b186c93a50d3cb435fe2933427d36e6dc688e4b'),  # noqa: E501
                ],
            ),
        ],
    )
    dbethtx = DBEthTx(database)
    with dbethtx.db.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
    decoder = EVMTransactionDecoder(
        database=database,
        ethereum_manager=ethereum_manager,
        eth_transactions=eth_transactions,
        msg_aggregator=msg_aggregator,
    )
    with dbethtx.db.user_write() as cursor:
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=ZERO, usd_value=ZERO),
            location_label='0x5B186c93A50D3CB435fE2933427d36E6Dc688e4b',
            notes='Burned 0 ETH in gas from 0x5B186c93A50D3CB435fE2933427d36E6Dc688e4b',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=343,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_CVX,
            balance=Balance(amount=ONE, usd_value=ZERO),
            location_label='0x5B186c93A50D3CB435fE2933427d36E6Dc688e4b',
            notes='Deposit 1 CVX into convex',
            counterparty=CPT_CONVEX,
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=344,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_CVX,
            balance=Balance(amount=FVal('1.157920892373161954235709850E+59'), usd_value=ZERO),
            location_label='0x5B186c93A50D3CB435fE2933427d36E6Dc688e4b',
            notes='Approve 1.157920892373161954235709850E+59 CVX of 0x5B186c93A50D3CB435fE2933427d36E6Dc688e4b for spending by 0xCF50b810E57Ac33B91dCF525C6ddd9881B139332',  # noqa: E501
            counterparty='0xCF50b810E57Ac33B91dCF525C6ddd9881B139332',
            identifier=None,
            extra_data=None,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0x95c5582D781d507A084c9E5f885C77BabACf8EeA')]])  # noqa: E501
def test_cvx_get_reward(database, ethereum_manager, eth_transactions):
    msg_aggregator = database.msg_aggregator
    tx_hex = '0xdaead2f96859462b5800584ecdcf30f2b83a1ca2c36c49a838b23e43c61d803f'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = '0x95c5582D781d507A084c9E5f885C77BabACf8EeA'
    transaction = EthereumTransaction(
        tx_hash=evmhash,
        timestamp=0,
        block_number=0,
        from_address=user_address,
        to_address=string_to_evm_address('0xCF50b810E57Ac33B91dCF525C6ddd9881B139332'),
        value=0,
        gas=0,
        gas_price=0,
        gas_used=0,
        input_data=b'',
        nonce=0,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=215,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                address=string_to_evm_address('0xD533a949740bb3306d119CC777fa900bA034cd52'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000cf50b810e57ac33b91dcf525c6ddd9881b139332'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000008014595f2ab54cd7c604b00e9fb932176fdc86ae'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=216,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000001b8e10e82689017e0'),  # noqa: E501
                address=string_to_evm_address('0xD533a949740bb3306d119CC777fa900bA034cd52'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000cf50b810e57ac33b91dcf525c6ddd9881b139332'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000008014595f2ab54cd7c604b00e9fb932176fdc86ae'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=217,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000001b8e10e82689017e0'),  # noqa: E501
                address=string_to_evm_address('0xD533a949740bb3306d119CC777fa900bA034cd52'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000cf50b810e57ac33b91dcf525c6ddd9881b139332'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000008014595f2ab54cd7c604b00e9fb932176fdc86ae'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=218,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000001b8e10e82689017e0'),  # noqa: E501
                address=string_to_evm_address('0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000cf50b810e57ac33b91dcf525c6ddd9881b139332'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=219,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000001b8e10e82689017e0'),  # noqa: E501
                address=string_to_evm_address('0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000cf50b810e57ac33b91dcf525c6ddd9881b139332'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000095c5582d781d507a084c9e5f885c77babacf8eea'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=220,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000001b8e10e82689017e0'),  # noqa: E501
                address=string_to_evm_address('0xCF50b810E57Ac33B91dCF525C6ddd9881B139332'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xe2403640ba68fed3a2f88b7557551d1993f84b99bb10ff833f0cf8db0c5e0486'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000095c5582d781d507a084c9e5f885c77babacf8eea'),  # noqa: E501
                ],
            ),
        ],
    )
    dbethtx = DBEthTx(database)
    with dbethtx.db.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
    decoder = EVMTransactionDecoder(
        database=database,
        ethereum_manager=ethereum_manager,
        eth_transactions=eth_transactions,
        msg_aggregator=msg_aggregator,
    )
    with dbethtx.db.user_write() as cursor:
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=ZERO, usd_value=ZERO),
            location_label='0x95c5582D781d507A084c9E5f885C77BabACf8EeA',
            notes='Burned 0 ETH in gas from 0x95c5582D781d507A084c9E5f885C77BabACf8EeA',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=220,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=EvmToken('eip155:1/erc20:0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),  # name='Convex CRV', symbol='cvxCRV'  # noqa: E501
            balance=Balance(amount=FVal('31.768689199711000544'), usd_value=ZERO),
            location_label='0x95c5582D781d507A084c9E5f885C77BabACf8EeA',
            notes='Claim 31.768689199711000544 cvxCRV reward from convex',
            counterparty=CPT_CONVEX,
            identifier=None,
            extra_data=None,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0x84BCE169c271e1c1777715bb0dd38Ad9e6381BAa')]])  # noqa: E501
def test_cvx_withdraw(database, ethereum_manager, eth_transactions):
    msg_aggregator = database.msg_aggregator
    tx_hex = '0xe725bd6e00b840f4fb8f73cd7286bfa18b04a24ca9278cac7249218ee9f420a8'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = string_to_evm_address('0x84BCE169c271e1c1777715bb0dd38Ad9e6381BAa')
    transaction = EthereumTransaction(
        tx_hash=evmhash,
        timestamp=0,
        block_number=0,
        from_address=user_address,
        to_address=string_to_evm_address('0xCF50b810E57Ac33B91dCF525C6ddd9881B139332'),
        value=0,
        gas=0,
        gas_price=0,
        gas_used=0,
        input_data=b'',
        nonce=0,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=422,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000001dd12c8e3dff5d8fee'),  # noqa: E501
                address=A_CVX.evm_address,
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000cf50b810e57ac33b91dcf525c6ddd9881b139332'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000084bce169c271e1c1777715bb0dd38ad9e6381baa'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=423,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000001dd12c8e3dff5d8fee'),  # noqa: E501
                address=string_to_evm_address('0xCF50b810E57Ac33B91dCF525C6ddd9881B139332'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x7084f5476618d8e60b11ef0d7d3f06914655adb8793e28ff7f018d4c76d505d5'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000084bce169c271e1c1777715bb0dd38ad9e6381baa'),  # noqa: E501
                ],
            ),
        ],
    )
    dbethtx = DBEthTx(database)
    with dbethtx.db.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
    decoder = EVMTransactionDecoder(
        database=database,
        ethereum_manager=ethereum_manager,
        eth_transactions=eth_transactions,
        msg_aggregator=msg_aggregator,
    )
    with dbethtx.db.user_write() as cursor:
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=ZERO, usd_value=ZERO),
            location_label='0x84BCE169c271e1c1777715bb0dd38Ad9e6381BAa',
            notes='Burned 0 ETH in gas from 0x84BCE169c271e1c1777715bb0dd38Ad9e6381BAa',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=423,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_CVX,
            balance=Balance(amount=FVal('550.028156587407675374'), usd_value=ZERO),
            location_label='0x84BCE169c271e1c1777715bb0dd38Ad9e6381BAa',
            notes='Withdraw 550.028156587407675374 CVX from convex',
            counterparty=CPT_CONVEX,
            identifier=None,
            extra_data=None,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0x999EcCEa3C4f9219B1B1B42b4830e62c26004B40')]])  # noqa: E501
def test_claimzap_abracadabras(database, ethereum_manager, eth_transactions):
    msg_aggregator = database.msg_aggregator
    tx_hex = '0xe03d27127fda879144ea4cc587470bd37040be9921ff6a90f48d4efd0cb4fe13'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = string_to_evm_address('0x999EcCEa3C4f9219B1B1B42b4830e62c26004B40')
    transaction = EthereumTransaction(
        tx_hash=evmhash,
        timestamp=0,
        block_number=0,
        from_address=user_address,
        to_address=string_to_evm_address('0xDd49A93FDcae579AE50B4b9923325e9e335ec82B'),
        value=0,
        gas=0,
        gas_price=0,
        gas_used=0,
        input_data=b'',
        nonce=0,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=592,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000669e01928977e52a3'),  # noqa: E501
                address=A_CVX.evm_address,
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000003ba207c25a278524e1cc7faaea950753049072a4'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000999eccea3c4f9219b1b1b42b4830e62c26004b40'),  # noqa: E501
                ],
            ),
        ],
    )
    dbethtx = DBEthTx(database)
    with dbethtx.db.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
    decoder = EVMTransactionDecoder(
        database=database,
        ethereum_manager=ethereum_manager,
        eth_transactions=eth_transactions,
        msg_aggregator=msg_aggregator,
    )
    with dbethtx.db.user_write() as cursor:
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=ZERO, usd_value=ZERO),
            location_label='0x999EcCEa3C4f9219B1B1B42b4830e62c26004B40',
            notes='Burned 0 ETH in gas from 0x999EcCEa3C4f9219B1B1B42b4830e62c26004B40',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=593,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_CVX,
            balance=Balance(amount=FVal('118.309589873153954467'), usd_value=ZERO),
            location_label='0x999EcCEa3C4f9219B1B1B42b4830e62c26004B40',
            notes='Claim 118.309589873153954467 CVX reward from convex',
            counterparty=CPT_CONVEX,
            identifier=None,
            extra_data=None,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0x0C3Cc503EaE928Ed6B5b01B8a9EE8de2855d03Ac')]])  # noqa: E501
def test_claimzap_cvx_locker(database, ethereum_manager, eth_transactions):
    msg_aggregator = database.msg_aggregator
    tx_hex = '0x53e092e6f25e540d6323af851a1e889276096d58ec25495aef4500467ef2753c'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = string_to_evm_address('0x0C3Cc503EaE928Ed6B5b01B8a9EE8de2855d03Ac')
    transaction = EthereumTransaction(
        tx_hash=evmhash,
        timestamp=0,
        block_number=0,
        from_address=user_address,
        to_address=string_to_evm_address('0xF403C135812408BFbE8713b5A23a04b3D48AAE31'),
        value=0,
        gas=0,
        gas_price=0,
        gas_used=0,
        input_data=b'',
        nonce=0,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=306,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000009a1a464320783532c'),  # noqa: E501
                address=string_to_evm_address('0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000d18140b4b819b895a3dba5442f959fa44994af50'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000c3cc503eae928ed6b5b01b8a9ee8de2855d03ac'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=307,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000009a1a464320783532c'),  # noqa: E501
                address=string_to_evm_address('0xD18140b4B819b895A3dba5442F959fA44994AF50'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x540798df468d7b23d11f156fdb954cb19ad414d150722a7b6d55ba369dea792e'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000c3cc503eae928ed6b5b01b8a9ee8de2855d03ac'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000062b9c7356a2dc64a1969e19c23e4f579f9810aa7'),  # noqa: E501
                ],
            ),
        ],
    )
    dbethtx = DBEthTx(database)
    with dbethtx.db.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
    decoder = EVMTransactionDecoder(
        database=database,
        ethereum_manager=ethereum_manager,
        eth_transactions=eth_transactions,
        msg_aggregator=msg_aggregator,
    )
    with dbethtx.db.user_write() as cursor:
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=ZERO, usd_value=ZERO),
            location_label='0x0C3Cc503EaE928Ed6B5b01B8a9EE8de2855d03Ac',
            notes='Burned 0 ETH in gas from 0x0C3Cc503EaE928Ed6B5b01B8a9EE8de2855d03Ac',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=307,
            timestamp=0,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=EvmToken('eip155:1/erc20:0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
            balance=Balance(amount=FVal('177.668241365710099244'), usd_value=ZERO),
            location_label='0x0C3Cc503EaE928Ed6B5b01B8a9EE8de2855d03Ac',
            notes='Claim 177.668241365710099244 cvxCRV reward from convex',
            counterparty=CPT_CONVEX,
            identifier=None,
            extra_data=None,
        ),
    ]
    assert events == expected_events
