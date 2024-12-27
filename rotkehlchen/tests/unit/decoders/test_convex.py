from typing import TYPE_CHECKING

import pytest

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
from rotkehlchen.chain.ethereum.modules.convex.constants import CPT_CONVEX, CVX_LOCKER_V2
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_CRV, A_CVX, A_ETH
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.tests.fixtures.messages import MockedWsMessage
from rotkehlchen.tests.utils.decoders import patch_decoder_reload_data
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    EvmTransaction,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


@pytest.mark.vcr
@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0xC960338B529e0353F570f62093Fd362B8FB55f0B')]])  # noqa: E501
def test_booster_deposit(
        ethereum_accounts,
        database,
        ethereum_inquirer: 'EthereumInquirer',
) -> None:
    tx_hex = '0x8f643dc245ce64085197692ed98309a94fd176a1e7394e8967ae7bfa10ad1f8f'
    timestamp = TimestampMS(1655810357000)
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=evmhash,
    )
    mocked_notifier = database.msg_aggregator.rotki_notifier
    assert mocked_notifier.pop_message() == MockedWsMessage(
        message_type=WSMessageType.NEW_EVM_TOKEN_DETECTED,
        data={
            'token_identifier': 'eip155:1/erc20:0x9518c9063eB0262D791f38d8d6Eb0aca33c63ed0',  # cvxsteCRV  # noqa: E501
            'seen_tx_hash': tx_hex,
        },
    )
    assert mocked_notifier.pop_message() == MockedWsMessage(
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
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.036417490797828122'),
            location_label=user_address,
            notes='Burn 0.036417490797828122 ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=461,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=EvmToken('eip155:1/erc20:0x06325440D014e39736583c165C2963BA99fAf14E'),
            amount=FVal('3.996511863643743872'),
            location_label=user_address,
            notes='Deposit 3.996511863643743872 steCRV into convex',
            counterparty=CPT_CONVEX,
            address=string_to_evm_address('0x989AEb4d175e16225E39E87d0D97A3360524AD80'),
            identifier=None,
            extra_data={'gauge_address': '0x008aEa5036b819B4FEAEd10b2190FBb3954981E8'},
            product=EvmProduct.GAUGE,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0x53913A03a065f685097f8E8f40284D58016bB0F9')]])  # noqa: E501
def test_booster_withdraw(ethereum_inquirer, ethereum_accounts):
    evmhash = deserialize_evm_tx_hash('0x79fcbafa4367e0563d3e614f774c5e4257c4e41f124ae8288980a310e2b2b547')  # noqa: E501
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1655877898000)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.008100974713577922'),
            location_label=user_address,
            notes='Burn 0.008100974713577922 ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=223,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0xCB6D873f7BbE57584a9b08380901Dc200Be7CE74'),
            amount=FVal('364.338089842514973505'),
            location_label=user_address,
            notes='Return 364.338089842514973505 cvxcvxFXSFXS-f to convex',
            counterparty=CPT_CONVEX,
            address=ZERO_ADDRESS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=229,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0xF3A43307DcAFa93275993862Aae628fCB50dC768'),
            amount=FVal('364.338089842514973505'),
            location_label=user_address,
            notes='Withdraw 364.338089842514973505 cvxFXSFXS-f from convex',
            counterparty=CPT_CONVEX,
            address=string_to_evm_address('0xF403C135812408BFbE8713b5A23a04b3D48AAE31'),
            identifier=None,
            extra_data=None,
            product=EvmProduct.GAUGE,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0xFb305A40Dac406BdCF3b85F6311e5430770f44bA')]])  # noqa: E501
def test_cvxcrv_get_reward(database, ethereum_inquirer, eth_transactions):
    tx_hex = '0x5e62ce39159fcdf528905d044e5387c8f21a1eca015d08cebc652bfb9c183611'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = string_to_evm_address('0xFb305A40Dac406BdCF3b85F6311e5430770f44bA')
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=1655675488,
        block_number=14998088,
        from_address=user_address,
        to_address=string_to_evm_address('0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x7050ccd9000000000000000000000000fb305a40dac406bdcf3b85f6311e5430770f44ba0000000000000000000000000000000000000000000000000000000000000001'),
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
                log_index=449,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000002eac6340ad673319bb'),
                address=string_to_evm_address('0xD533a949740bb3306d119CC777fa900bA034cd52'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000003fe65692bfcd0e6cf84cb1e7d24108e434a7587e'),
                    hexstring_to_bytes('0x000000000000000000000000fb305a40dac406bdcf3b85f6311e5430770f44ba'),
                ],
            ), EvmTxReceiptLog(
                log_index=450,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000003f79cea9e196976aa'),
                address=string_to_evm_address('0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000fb305a40dac406bdcf3b85f6311e5430770f44ba'),
                ],
            ), EvmTxReceiptLog(
                log_index=451,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000002eac6340ad673319bb'),
                address=string_to_evm_address('0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e'),
                topics=[
                    hexstring_to_bytes('0xe2403640ba68fed3a2f88b7557551d1993f84b99bb10ff833f0cf8db0c5e0486'),
                    hexstring_to_bytes('0x000000000000000000000000fb305a40dac406bdcf3b85f6311e5430770f44ba'),
                ],
            ), EvmTxReceiptLog(
                log_index=452,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000001fd601592884f765d9'),
                address=string_to_evm_address('0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000007091dbb7fcba54569ef1387ac89eb2a5c9f6d2ea'),
                    hexstring_to_bytes('0x000000000000000000000000fb305a40dac406bdcf3b85f6311e5430770f44ba'),
                ],
            ), EvmTxReceiptLog(
                log_index=453,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000001fd601592884f765d9'),
                address=string_to_evm_address('0x7091dbb7fcbA54569eF1387Ac89Eb2a5C9F6d2EA'),
                topics=[
                    hexstring_to_bytes('0xe2403640ba68fed3a2f88b7557551d1993f84b99bb10ff833f0cf8db0c5e0486'),
                    hexstring_to_bytes('0x000000000000000000000000fb305a40dac406bdcf3b85f6311e5430770f44ba'),
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
    with dbevmtx.db.conn.read_ctx() as cursor, patch_decoder_reload_data():
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        decoder.reload_data(cursor)

    events, _, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)
    timestamp = TimestampMS(1655675488000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00393701451'),
            location_label='0xFb305A40Dac406BdCF3b85F6311e5430770f44bA',
            notes='Burn 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=450,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_CRV,
            amount=FVal('860.972070701362256315'),
            location_label='0xFb305A40Dac406BdCF3b85F6311e5430770f44bA',
            notes='Claim 860.972070701362256315 CRV reward from convex',
            counterparty=CPT_CONVEX,
            address=string_to_evm_address('0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e'),
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=451,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_CVX,
            amount=FVal('73.182626009615791786'),
            location_label='0xFb305A40Dac406BdCF3b85F6311e5430770f44bA',
            notes='Claim 73.182626009615791786 CVX reward from convex',
            counterparty=CPT_CONVEX,
            address=ZERO_ADDRESS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=453,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=EvmToken('eip155:1/erc20:0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490'),  # name='Curve.fi DAI/USDC/USDT', symbol='3Crv'  # noqa: E501
            amount=FVal('587.269770914653758937'),
            location_label='0xFb305A40Dac406BdCF3b85F6311e5430770f44bA',
            notes='Claim 587.269770914653758937 3Crv reward from convex',
            counterparty=CPT_CONVEX,
            address=string_to_evm_address('0x7091dbb7fcbA54569eF1387Ac89Eb2a5C9F6d2EA'),
            identifier=None,
            extra_data=None,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0xe81FC42336c9314A9Be1EDB3F50eA9e275C93df3')]])  # noqa: E501
def test_cvxcrv_withdraw(ethereum_inquirer, ethereum_accounts):
    evmhash = deserialize_evm_tx_hash('0x0a804804cc62f615b72dff55e8c245d9b69aa8f8ed3de549101ae128a4ae432b')  # noqa: E501
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1655747494000)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.003944294203856622'),
            location_label='0xe81FC42336c9314A9Be1EDB3F50eA9e275C93df3',
            notes='Burn 0.003944294203856622 ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=424,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=EvmToken('eip155:1/erc20:0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
            amount=FVal('15719.844875963195659251'),
            location_label=user_address,
            notes='Withdraw 15719.844875963195659251 cvxCRV from convex',
            counterparty=CPT_CONVEX,
            address=string_to_evm_address('0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e'),
            identifier=None,
            extra_data=None,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0x2AcEcBF2Ee5BFc8eed599D58835EE9A7c45F3E2c')]])  # noqa: E501
def test_cvxcrv_stake(ethereum_inquirer, ethereum_accounts):
    evmhash = deserialize_evm_tx_hash('0x3cc0b25887e2f0dac7f86fabd81aaafb1e041e84dbe8167885073c443320ad5f')  # noqa: E501
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1655750059000)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.003312675833439456'),
            location_label=user_address,
            notes='Burn 0.003312675833439456 ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=426,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=EvmToken('eip155:1/erc20:0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
            amount=FVal('166.415721340864759482'),
            location_label=user_address,
            notes='Deposit 166.415721340864759482 cvxCRV into convex',
            counterparty=CPT_CONVEX,
            address=string_to_evm_address('0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e'),
            identifier=None,
            extra_data={'gauge_address': '0x7091dbb7fcbA54569eF1387Ac89Eb2a5C9F6d2EA'},
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=427,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=EvmToken('eip155:1/erc20:0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
            amount=FVal('115792089237316195423570985008687907853269984665640564035009.494296485710746932'),
            location_label=user_address,
            notes='Set cvxCRV spending approval of 0x2AcEcBF2Ee5BFc8eed599D58835EE9A7c45F3E2c by 0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e to 115792089237316195423570985008687907853269984665640564035009.494296485710746932',  # noqa: E501
            address=string_to_evm_address('0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e'),
            identifier=None,
            extra_data=None,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0x5B186c93A50D3CB435fE2933427d36E6Dc688e4b')]])  # noqa: E501
def test_cvx_stake(database, ethereum_inquirer, eth_transactions):
    evmhash = deserialize_evm_tx_hash('0xc33246acb86798b81fe650061061d32751c53879d46ece6991fb4a3eda808103')  # noqa: E501
    user_address = string_to_evm_address('0x5B186c93A50D3CB435fE2933427d36E6Dc688e4b')
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
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
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=342,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000de0b6b3a7640000'),
                address=A_CVX.resolve_to_evm_token().evm_address,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000005b186c93a50d3cb435fe2933427d36e6dc688e4b'),
                    hexstring_to_bytes('0x000000000000000000000000cf50b810e57ac33b91dcf525c6ddd9881b139332'),
                ],
            ), EvmTxReceiptLog(
                log_index=343,
                data=hexstring_to_bytes('0xfffffffffffffffffffffffffffffffffffffffffffffffff21f494c589bffff'),
                address=A_CVX.resolve_to_evm_token().evm_address,
                topics=[
                    hexstring_to_bytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'),
                    hexstring_to_bytes('0x0000000000000000000000005b186c93a50d3cb435fe2933427d36e6dc688e4b'),
                    hexstring_to_bytes('0x000000000000000000000000cf50b810e57ac33b91dcf525c6ddd9881b139332'),
                ],
            ), EvmTxReceiptLog(
                log_index=344,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000de0b6b3a7640000'),
                address=string_to_evm_address('0xCF50b810E57Ac33B91dCF525C6ddd9881B139332'),
                topics=[
                    hexstring_to_bytes('0x9e71bc8eea02a63969f509818f2dafb9254532904319f9dbda79b67bd34a5f3d'),
                    hexstring_to_bytes('0x0000000000000000000000005b186c93a50d3cb435fe2933427d36e6dc688e4b'),
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
    with dbevmtx.db.conn.read_ctx() as cursor, patch_decoder_reload_data():
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        decoder.reload_data(cursor)

    events, _, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=ZERO,
            location_label='0x5B186c93A50D3CB435fE2933427d36E6Dc688e4b',
            notes='Burn 0 ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=343,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_CVX,
            amount=ONE,
            location_label='0x5B186c93A50D3CB435fE2933427d36E6Dc688e4b',
            notes='Deposit 1 CVX into convex',
            counterparty=CPT_CONVEX,
            address=string_to_evm_address('0xCF50b810E57Ac33B91dCF525C6ddd9881B139332'),
            identifier=None,
            extra_data={'gauge_address': '0xCF50b810E57Ac33B91dCF525C6ddd9881B139332'},
            product=EvmProduct.STAKING,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=344,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_CVX,
            amount=FVal('115792089237316195423570985008687907853269984665640564039456.584007913129639935'),
            location_label='0x5B186c93A50D3CB435fE2933427d36E6Dc688e4b',
            notes='Set CVX spending approval of 0x5B186c93A50D3CB435fE2933427d36E6Dc688e4b by 0xCF50b810E57Ac33B91dCF525C6ddd9881B139332 to 115792089237316195423570985008687907853269984665640564039456.584007913129639935',  # noqa: E501
            address=string_to_evm_address('0xCF50b810E57Ac33B91dCF525C6ddd9881B139332'),
            identifier=None,
            extra_data=None,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0x95c5582D781d507A084c9E5f885C77BabACf8EeA')]])  # noqa: E501
def test_cvx_get_reward(database, ethereum_inquirer, eth_transactions):
    evmhash = deserialize_evm_tx_hash('0xdaead2f96859462b5800584ecdcf30f2b83a1ca2c36c49a838b23e43c61d803f')  # noqa: E501
    user_address = '0x95c5582D781d507A084c9E5f885C77BabACf8EeA'
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
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
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=215,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                address=string_to_evm_address('0xD533a949740bb3306d119CC777fa900bA034cd52'),
                topics=[
                    hexstring_to_bytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'),
                    hexstring_to_bytes('0x000000000000000000000000cf50b810e57ac33b91dcf525c6ddd9881b139332'),
                    hexstring_to_bytes('0x0000000000000000000000008014595f2ab54cd7c604b00e9fb932176fdc86ae'),
                ],
            ), EvmTxReceiptLog(
                log_index=216,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000001b8e10e82689017e0'),
                address=string_to_evm_address('0xD533a949740bb3306d119CC777fa900bA034cd52'),
                topics=[
                    hexstring_to_bytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'),
                    hexstring_to_bytes('0x000000000000000000000000cf50b810e57ac33b91dcf525c6ddd9881b139332'),
                    hexstring_to_bytes('0x0000000000000000000000008014595f2ab54cd7c604b00e9fb932176fdc86ae'),
                ],
            ), EvmTxReceiptLog(
                log_index=217,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000001b8e10e82689017e0'),
                address=string_to_evm_address('0xD533a949740bb3306d119CC777fa900bA034cd52'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000cf50b810e57ac33b91dcf525c6ddd9881b139332'),
                    hexstring_to_bytes('0x0000000000000000000000008014595f2ab54cd7c604b00e9fb932176fdc86ae'),
                ],
            ), EvmTxReceiptLog(
                log_index=218,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000001b8e10e82689017e0'),
                address=string_to_evm_address('0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000cf50b810e57ac33b91dcf525c6ddd9881b139332'),
                ],
            ), EvmTxReceiptLog(
                log_index=219,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000001b8e10e82689017e0'),
                address=string_to_evm_address('0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000cf50b810e57ac33b91dcf525c6ddd9881b139332'),
                    hexstring_to_bytes('0x00000000000000000000000095c5582d781d507a084c9e5f885c77babacf8eea'),
                ],
            ), EvmTxReceiptLog(
                log_index=220,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000001b8e10e82689017e0'),
                address=string_to_evm_address('0xCF50b810E57Ac33B91dCF525C6ddd9881B139332'),
                topics=[
                    hexstring_to_bytes('0xe2403640ba68fed3a2f88b7557551d1993f84b99bb10ff833f0cf8db0c5e0486'),
                    hexstring_to_bytes('0x00000000000000000000000095c5582d781d507a084c9e5f885c77babacf8eea'),
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
    with dbevmtx.db.conn.read_ctx() as cursor, patch_decoder_reload_data():
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        decoder.reload_data(cursor)

    events, _, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=ZERO,
            location_label='0x95c5582D781d507A084c9E5f885C77BabACf8EeA',
            notes='Burn 0 ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=220,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=EvmToken('eip155:1/erc20:0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),  # name='Convex CRV', symbol='cvxCRV'  # noqa: E501
            amount=FVal('31.768689199711000544'),
            location_label='0x95c5582D781d507A084c9E5f885C77BabACf8EeA',
            notes='Claim 31.768689199711000544 cvxCRV reward from convex',
            counterparty=CPT_CONVEX,
            address=string_to_evm_address('0xCF50b810E57Ac33B91dCF525C6ddd9881B139332'),
            identifier=None,
            extra_data=None,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0x84BCE169c271e1c1777715bb0dd38Ad9e6381BAa')]])  # noqa: E501
def test_cvx_withdraw(database, ethereum_inquirer, eth_transactions):
    evmhash = deserialize_evm_tx_hash('0xe725bd6e00b840f4fb8f73cd7286bfa18b04a24ca9278cac7249218ee9f420a8')  # noqa: E501
    user_address = string_to_evm_address('0x84BCE169c271e1c1777715bb0dd38Ad9e6381BAa')
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
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
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=422,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000001dd12c8e3dff5d8fee'),
                address=A_CVX.resolve_to_evm_token().evm_address,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000cf50b810e57ac33b91dcf525c6ddd9881b139332'),
                    hexstring_to_bytes('0x00000000000000000000000084bce169c271e1c1777715bb0dd38ad9e6381baa'),
                ],
            ), EvmTxReceiptLog(
                log_index=423,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000001dd12c8e3dff5d8fee'),
                address=string_to_evm_address('0xCF50b810E57Ac33B91dCF525C6ddd9881B139332'),
                topics=[
                    hexstring_to_bytes('0x7084f5476618d8e60b11ef0d7d3f06914655adb8793e28ff7f018d4c76d505d5'),
                    hexstring_to_bytes('0x00000000000000000000000084bce169c271e1c1777715bb0dd38ad9e6381baa'),
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
    with dbevmtx.db.conn.read_ctx() as cursor, patch_decoder_reload_data():
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        decoder.reload_data(cursor)

    events, _, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=ZERO,
            location_label='0x84BCE169c271e1c1777715bb0dd38Ad9e6381BAa',
            notes='Burn 0 ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=423,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_CVX,
            amount=FVal('550.028156587407675374'),
            location_label='0x84BCE169c271e1c1777715bb0dd38Ad9e6381BAa',
            notes='Withdraw 550.028156587407675374 CVX from convex',
            counterparty=CPT_CONVEX,
            address=string_to_evm_address('0xCF50b810E57Ac33B91dCF525C6ddd9881B139332'),
            identifier=None,
            extra_data=None,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0x999EcCEa3C4f9219B1B1B42b4830e62c26004B40')]])  # noqa: E501
def test_claimzap_abracadabras(database, ethereum_inquirer, eth_transactions):
    evmhash = deserialize_evm_tx_hash('0xe03d27127fda879144ea4cc587470bd37040be9921ff6a90f48d4efd0cb4fe13')  # noqa: E501
    user_address = string_to_evm_address('0x999EcCEa3C4f9219B1B1B42b4830e62c26004B40')
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
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
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=592,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000669e01928977e52a3'),
                address=A_CVX.resolve_to_evm_token().evm_address,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000003ba207c25a278524e1cc7faaea950753049072a4'),
                    hexstring_to_bytes('0x000000000000000000000000999eccea3c4f9219b1b1b42b4830e62c26004b40'),
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
    with dbevmtx.db.conn.read_ctx() as cursor, patch_decoder_reload_data():
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        decoder.reload_data(cursor)

    events, _, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=ZERO,
            location_label='0x999EcCEa3C4f9219B1B1B42b4830e62c26004B40',
            notes='Burn 0 ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=593,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_CVX,
            amount=FVal('118.309589873153954467'),
            location_label='0x999EcCEa3C4f9219B1B1B42b4830e62c26004B40',
            notes='Claim 118.309589873153954467 CVX reward from convex',
            counterparty=CPT_CONVEX,
            address=string_to_evm_address('0x3Ba207c25A278524e1cC7FaAea950753049072A4'),
            identifier=None,
            extra_data=None,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0x0C3Cc503EaE928Ed6B5b01B8a9EE8de2855d03Ac')]])  # noqa: E501
def test_claimzap_cvx_locker(database, ethereum_inquirer, eth_transactions):
    evmhash = deserialize_evm_tx_hash('0x53e092e6f25e540d6323af851a1e889276096d58ec25495aef4500467ef2753c')  # noqa: E501
    user_address = string_to_evm_address('0x0C3Cc503EaE928Ed6B5b01B8a9EE8de2855d03Ac')
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
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
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=306,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000009a1a464320783532c'),
                address=string_to_evm_address('0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000d18140b4b819b895a3dba5442f959fa44994af50'),
                    hexstring_to_bytes('0x0000000000000000000000000c3cc503eae928ed6b5b01b8a9ee8de2855d03ac'),
                ],
            ), EvmTxReceiptLog(
                log_index=307,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000009a1a464320783532c'),
                address=string_to_evm_address('0xD18140b4B819b895A3dba5442F959fA44994AF50'),
                topics=[
                    hexstring_to_bytes('0x540798df468d7b23d11f156fdb954cb19ad414d150722a7b6d55ba369dea792e'),
                    hexstring_to_bytes('0x0000000000000000000000000c3cc503eae928ed6b5b01b8a9ee8de2855d03ac'),
                    hexstring_to_bytes('0x00000000000000000000000062b9c7356a2dc64a1969e19c23e4f579f9810aa7'),
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
    with dbevmtx.db.conn.read_ctx() as cursor, patch_decoder_reload_data():
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        decoder.reload_data(cursor)

    events, _, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=ZERO,
            location_label='0x0C3Cc503EaE928Ed6B5b01B8a9EE8de2855d03Ac',
            notes='Burn 0 ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=307,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=EvmToken('eip155:1/erc20:0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
            amount=FVal('177.668241365710099244'),
            location_label='0x0C3Cc503EaE928Ed6B5b01B8a9EE8de2855d03Ac',
            notes='Claim 177.668241365710099244 cvxCRV reward from convex',
            counterparty=CPT_CONVEX,
            address=string_to_evm_address('0xD18140b4B819b895A3dba5442F959fA44994AF50'),
            identifier=None,
            extra_data=None,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_CONVEX]])
@pytest.mark.parametrize('ethereum_accounts', [['0x983488580460155d43B6b82096eE17C640A7DCac']])
def test_convex_claim_pending_rewards(ethereum_inquirer, ethereum_accounts, load_global_caches):
    """
    Tests a transaction that collects pending rewards but also compounds the pending CRV
    in the pool. In this case the user is rewarded for performing this action.
    """
    user_address = ethereum_accounts[0]
    evmhash = deserialize_evm_tx_hash('0xf3b8bbb2996515bc276626378ad85bc241051cac5d09c709ae9447665a3babd6')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=evmhash,
        load_global_caches=load_global_caches,
    )
    timestamp = TimestampMS(1683871727000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.050474707401697742'),
            location_label=user_address,
            notes='Burn 0.050474707401697742 ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=471,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_CRV,
            amount=FVal('20.239941211089735958'),
            location_label=user_address,
            notes='Claim 20.239941211089735958 CRV after compounding Convex pool',
            counterparty=CPT_CONVEX,
            address=string_to_evm_address('0xF403C135812408BFbE8713b5A23a04b3D48AAE31'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xD18327BB6D6de9241Bed63bb5E78459325FbbD70']])
def test_convex_withdraw_expired_lock(ethereum_inquirer, ethereum_accounts):
    """
    Tests a transaction that collects pending rewards but also compounds the pending CRV
    in the pool. In this case the user is rewarded for performing this action.
    """
    user_address = ethereum_accounts[0]
    evmhash = deserialize_evm_tx_hash('0x4b707540ec6eebf5e787c88df149e8141d2c295cda8a514da6d6111cf2deca40')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash)
    timestamp = TimestampMS(1704839507000)
    gas_str, amount_str = '0.008929295372796715', '26633.698252368450151266'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str),
            location_label=user_address,
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=363,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_CVX,
            amount=FVal(amount_str),
            location_label=user_address,
            notes=f'Unlock {amount_str} CVX from convex',
            counterparty=CPT_CONVEX,
            address=CVX_LOCKER_V2,
        ),
    ]
    assert events == expected_events
