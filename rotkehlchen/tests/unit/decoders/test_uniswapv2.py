import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
from rotkehlchen.chain.ethereum.modules.airdrops.constants import CPT_UNISWAP
from rotkehlchen.chain.ethereum.modules.airdrops.decoder import UNISWAP_DISTRIBUTOR
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V2
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_UNI, A_USDC
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.decoders import patch_decoder_reload_data
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    UNISWAP_PROTOCOL,
    ChainID,
    EvmTokenKind,
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
ADDY_4 = string_to_evm_address('0x43e141534d718D72552De1B606a5FCBc72256cD7')


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDY_1]])
def test_uniswap_v2_swap(ethereum_inquirer):
    tx_hash = deserialize_evm_tx_hash('0x67cf6c4ce5078f9750a14afd2f5070c327caf8c5180bdee2be59644ac59974e1')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1628753094000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(0.00847616)),
            location_label=ADDY_1,
            notes='Burned 0.00847616 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1628753094000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.15')),
            location_label=ADDY_1,
            notes='Swap 0.15 ETH in uniswap-v2 from 0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',
            counterparty=CPT_UNISWAP_V2,
            address=string_to_evm_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=TimestampMS(1628753094000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=EvmToken('eip155:1/erc20:0x853d955aCEf822Db058eb8505911ED77F175b99e'),
            balance=Balance(amount=FVal('462.967761432322996701')),
            location_label=ADDY_1,
            notes='Receive 462.967761432322996701 FRAX in uniswap-v2 from 0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',  # noqa: E501
            counterparty=CPT_UNISWAP_V2,
            address=string_to_evm_address('0xE1573B9D29e2183B1AF0e743Dc2754979A40D237'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDY_1]])
def test_uniswap_v2_swap_eth_returned(ethereum_inquirer):
    """Test a transaction where eth is swapped and some of it is returned due to change in price"""
    tx_hash = deserialize_evm_tx_hash('0x20ecc226c438a8803a6195d8031ae7dd97a27351e6b7429621b36194121b9b76')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1634652419000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(0.006697194528224109)),
            location_label=ADDY_1,
            notes='Burned 0.006697194528224109 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REFUND,
            asset=A_ETH,
            balance=Balance(amount=FVal(0.008104374914845978)),
            location_label=ADDY_1,
            notes='Refund of 0.008104374914845978 ETH in uniswap-v2 due to price change',
            counterparty=CPT_UNISWAP_V2,
            address=string_to_evm_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(amount=FVal('1.59134916748576351')),
            location_label=ADDY_1,
            notes='Swap 1.59134916748576351 ETH in uniswap-v2 from 0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',  # noqa: E501
            counterparty=CPT_UNISWAP_V2,
            address=string_to_evm_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=EvmToken('eip155:1/erc20:0x761D38e5ddf6ccf6Cf7c55759d5210750B5D60F3'),
            balance=Balance(amount=FVal('10000000000')),
            location_label=ADDY_1,
            notes='Receive 10000000000 ELON in uniswap-v2 from 0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',  # noqa: E501
            counterparty=CPT_UNISWAP_V2,
            address=string_to_evm_address('0x7B73644935b8e68019aC6356c40661E1bc315860'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xa931b486F661540c6D709aE6DfC8BcEF347ea437']])
def test_uniswap_v2_swap_with_approval(ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0xcbe558177f62ccdb77f59b6be11e60b0a3fed1d224d5ce28d2bb6dff59447d3b')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hex)
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1667857559000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('0.003227029072809172')),
            location_label=user_address,
            notes='Burned 0.003227029072809172 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1667857559000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0x33349B282065b0284d756F0577FB39c158F935e6'),
            balance=Balance(amount=FVal('115792089237316195423570985008687907853269984665640564039436.930578017129639935')),
            location_label=user_address,
            notes='Set MPL spending approval of 0xa931b486F661540c6D709aE6DfC8BcEF347ea437 by 0x617Dee16B86534a5d792A4d7A62FB491B544111E to 115792089237316195423570985008687907853269984665640564039436.930578017129639935',  # noqa: E501
            address=string_to_evm_address('0x617Dee16B86534a5d792A4d7A62FB491B544111E'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1667857559000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0x33349B282065b0284d756F0577FB39c158F935e6'),
            balance=Balance(amount=FVal('20.653429896')),
            location_label=user_address,
            notes='Swap 20.653429896 MPL in uniswap-v2',
            counterparty=CPT_UNISWAP_V2,
            address=string_to_evm_address('0x7b28470032DA06051f2E620531adBAeAdb285408'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=3,
            timestamp=TimestampMS(1667857559000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            balance=Balance(amount=FVal('273.798721')),
            location_label=user_address,
            notes=f'Receive 273.798721 USDC as a result of a {CPT_UNISWAP_V2} swap',
            counterparty=CPT_UNISWAP_V2,
            address=string_to_evm_address('0x7b28470032DA06051f2E620531adBAeAdb285408'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDY_2]])
def test_uniswap_v2_add_liquidity(ethereum_inquirer):
    """This checks that adding liquidity to a Uniswap V2 pool is decoded properly."""
    tx_hash = deserialize_evm_tx_hash('0x1bab8a89a6a3f8cb127cfaf7cd58809201a4e230d0a05f9e067674749605959e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    lp_token_identifier = evm_address_to_identifier(
        address='0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5',
        chain_id=ChainID.ETHEREUM,
        token_type=EvmTokenKind.ERC20,
    )
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1672348871000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.002931805211106758')),
            location_label=ADDY_2,
            notes='Burned 0.002931805211106758 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=118,
            timestamp=TimestampMS(1672348871000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_USDC,
            balance=Balance(amount=FVal('25')),
            location_label=ADDY_2,
            notes='Deposit 25 USDC to uniswap-v2 LP 0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5',
            counterparty=CPT_UNISWAP_V2,
            address=string_to_evm_address('0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5'),
            extra_data={'pool_address': '0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5'},
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=119,
            timestamp=TimestampMS(1672348871000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_DAI,
            balance=Balance(amount=FVal('24.994824629555601269')),
            location_label=ADDY_2,
            notes='Deposit 24.994824629555601269 DAI to uniswap-v2 LP 0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5',  # noqa: E501
            counterparty=CPT_UNISWAP_V2,
            address=string_to_evm_address('0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5'),
            extra_data={'pool_address': '0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5'},
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=120,
            timestamp=TimestampMS(1672348871000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset(lp_token_identifier),
            balance=Balance(amount=FVal('0.000022187913295974')),
            location_label=ADDY_2,
            notes='Receive 0.000022187913295974 UNI-V2 DAI-USDC from uniswap-v2 pool',
            counterparty=CPT_UNISWAP_V2,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events
    lp_token = EvmToken(lp_token_identifier)
    assert lp_token.protocol == UNISWAP_PROTOCOL
    assert lp_token.symbol == 'UNI-V2 DAI-USDC'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDY_3]])
def test_uniswap_v2_remove_liquidity(ethereum_inquirer):
    """This checks that removing liquidity from a Uniswap V2 pool is decoded properly."""
    tx_hash = deserialize_evm_tx_hash('0x0936a16e1d3655e832c60bed52040fd5ac0d99d03865d11225b3183dba318f43')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
        ), EvmEvent(
            tx_hash=tx_hash,
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
            address=string_to_evm_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
            extra_data={'pool_address': '0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'},
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=33,
            timestamp=TimestampMS(1672784687000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'),
            balance=Balance(amount=FVal('9.6176228659E-8')),
            location_label=ADDY_3,
            notes='Set UNI-V2 spending approval of 0x65fc65C639467423Bf19801a59FCfd62f0F29777 by 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D to 0.000000096176228659',  # noqa: E501
            address=string_to_evm_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=34,
            timestamp=TimestampMS(1672784687000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'),
            balance=Balance(amount=FVal('9.6176228659E-8')),
            location_label=ADDY_3,
            notes='Send 0.000000096176228659 UNI-V2 USDC-WETH to uniswap-v2 pool',
            counterparty=CPT_UNISWAP_V2,
            address=string_to_evm_address('0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'),
        ), EvmEvent(
            tx_hash=tx_hash,
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
            address=string_to_evm_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
            extra_data={'pool_address': '0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'},
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDY_4]])
def test_uniswap_v2_swap_events_order(
        database,
        ethereum_inquirer,
        eth_transactions,
        ethereum_accounts,
):
    """Check that the order of swap events are consecutive.

    This transaction hash does not exist on-chain.
    It was mocked to avoid leaking user info to the public.

    It checks that an approval event does not come between trade events.
    """
    tx_hash = '0xec15324d55274d9ad3181ed2f29d29e9812841e5e79aa9228a0f3ef4d3ce8d2c'
    evmhash = deserialize_evm_tx_hash(tx_hash)
    user_address = ethereum_accounts[0]
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1672784687),
        block_number=16329226,
        from_address=ADDY_4,
        to_address='0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
        value=0,
        gas=354181,
        gas_price=20000000000,
        gas_used=234471,
        input_data=hexstring_to_bytes('0x38ed1739000000000000000000000000000000000000000000000001405cc9cdb5ccd5f50000000000000000000000000000000000000000000000032232ec1cbf43ca0100000000000000000000000000000000000000000000000000000000000000a00000000000000000000000007db7da086318462a46327b8f2d46f457008cc111000000000000000000000000000000000000000000000000000000005f7258b30000000000000000000000000000000000000000000000000000000000000003000000000000000000000000a3bed4e1c75d00fa6f4e5e6922db7261b5e9acd2000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc20000000000000000000000006b175474e89094c44da98b954eedeac495271d0f'),
        nonce=2,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=31,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000001405cc9cdb5ccd5f5'),
                address=string_to_evm_address('0xa3BeD4E1c75D00fa6f4E5E6922DB7261B5E9AcD2'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x00000000000000000000000043e141534d718D72552De1B606a5FCBc72256cD7'),
                    hexstring_to_bytes('0x0000000000000000000000000d0d65e7a7db277d3e0f5e1676325e75f3340455'),
                ],
            ), EvmTxReceiptLog(
                log_index=32,
                data=hexstring_to_bytes('0xfffffffffffffffffffffffffffffffffffffffffffffffebfa336324a332a0a'),
                address=string_to_evm_address('0xa3BeD4E1c75D00fa6f4E5E6922DB7261B5E9AcD2'),
                topics=[
                    hexstring_to_bytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'),
                    hexstring_to_bytes('0x00000000000000000000000043e141534d718D72552De1B606a5FCBc72256cD7'),
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),
                ],
            ), EvmTxReceiptLog(
                log_index=33,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000002476b12c1292c7a'),
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000000d0d65e7a7db277d3e0f5e1676325e75f3340455'),
                    hexstring_to_bytes('0x000000000000000000000000a478c2975ab1ea89e8196811f51a7b7ade33eb11'),
                ],
            ), EvmTxReceiptLog(
                log_index=34,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000085458f584469791bd7960000000000000000000000000000000000000000000000f36cd1acc023153ced'),
                address=string_to_evm_address('0x0d0d65E7A7dB277d3E0F5E1676325E75f3340455'),
                topics=[
                    hexstring_to_bytes('0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1'),
                ],
            ), EvmTxReceiptLog(
                log_index=35,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000001405cc9cdb5ccd5f50000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002476b12c1292c7a'),
                address=string_to_evm_address('0x0d0d65E7A7dB277d3E0F5E1676325E75f3340455'),
                topics=[
                    hexstring_to_bytes('0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'),
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),
                    hexstring_to_bytes('0x000000000000000000000000a478c2975ab1ea89e8196811f51a7b7ade33eb11'),
                ],
            ), EvmTxReceiptLog(
                log_index=36,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000026068b3a890000000000000000000000000000000000000000000000074f0bf96ef2478fa7ad'),
                address=string_to_evm_address('0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'),
                topics=[
                    hexstring_to_bytes('0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1'),
                ],
            ), EvmTxReceiptLog(
                log_index=37,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000000006beed50000000000000000000000000000000000000000000000000014bed67222b2ba'),
                address=string_to_evm_address('0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'),
                topics=[
                    hexstring_to_bytes('0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496'),
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),
                ],
            ), EvmTxReceiptLog(
                log_index=38,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000032c190329a9b16bef'),
                address=string_to_evm_address('0x6B175474E89094C44Da98b954EedeAC495271d0F'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000a478c2975ab1ea89e8196811f51a7b7ade33eb11'),
                    hexstring_to_bytes('0x00000000000000000000000043e141534d718D72552De1B606a5FCBc72256cD7'),
                ],
            ), EvmTxReceiptLog(
                log_index=39,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000997f8a78f8b20f05afd018000000000000000000000000000000000000000000006df1960f8fb9530fad8a'),
                address=string_to_evm_address('0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11'),
                topics=[
                    hexstring_to_bytes('0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1'),
                ],
            ), EvmTxReceiptLog(
                log_index=40,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002476b12c1292c7a0000000000000000000000000000000000000000000000032c190329a9b16bef0000000000000000000000000000000000000000000000000000000000000000'),
                address=string_to_evm_address('0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11'),
                topics=[
                    hexstring_to_bytes('0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'),
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),
                    hexstring_to_bytes('0x00000000000000000000000043e141534d718D72552De1B606a5FCBc72256cD7'),
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
    with database.user_write() as cursor, patch_decoder_reload_data():
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        decoder.reload_data(cursor)

    events, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            timestamp=1672784687000,
            location=Location.ETHEREUM,
            sequence_index=0,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(FVal('0.00468942')),
            location_label=user_address,
            notes='Burned 0.00468942 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            timestamp=1672784687000,
            location=Location.ETHEREUM,
            sequence_index=33,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0xa3BeD4E1c75D00fa6f4E5E6922DB7261B5E9AcD2'),
            balance=Balance(FVal('115792089237316195423570985008687907853269984665640564039434.499460237779741194')),
            location_label=user_address,
            notes=f'Set MTA spending approval of {user_address} by 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D to 115792089237316195423570985008687907853269984665640564039434.499460237779741194',  # noqa: E501
            counterparty=None,
            address=string_to_evm_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        ), EvmEvent(
            tx_hash=evmhash,
            timestamp=1672784687000,
            location=Location.ETHEREUM,
            sequence_index=34,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0xa3BeD4E1c75D00fa6f4E5E6922DB7261B5E9AcD2'),
            balance=Balance(FVal('23.084547675349898741')),
            location_label=user_address,
            notes=f'Swap 23.084547675349898741 MTA in uniswap-v2 from {user_address}',
            counterparty=CPT_UNISWAP_V2,
            address=string_to_evm_address('0x0d0d65E7A7dB277d3E0F5E1676325E75f3340455'),
        ), EvmEvent(
            tx_hash=evmhash,
            timestamp=1672784687000,
            location=Location.ETHEREUM,
            sequence_index=35,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_DAI,
            balance=Balance(FVal('58.517806710690769903')),
            location_label=user_address,
            notes=f'Receive 58.517806710690769903 DAI in uniswap-v2 from {user_address}',
            counterparty=CPT_UNISWAP_V2,
            address=string_to_evm_address('0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xbcce162c23480a4d44b88F57D5D2D9997402010e']])
def test_remove_liquidity_with_weth(ethereum_inquirer, ethereum_accounts):
    """Test that removing liquidity as weth gets correctly decoded"""
    tx_hex = deserialize_evm_tx_hash('0x00007120e5281e9bdf9a57739e3ecaf736013e4a1a31ecfe44f719c229cc2cbd')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hex)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1615943669000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.018446778')),
            location_label=user_address,
            notes='Burned 0.018446778 ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=238,
            timestamp=TimestampMS(1615943669000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0xFfA98A091331Df4600F87C9164cD27e8a5CD2405'),
            balance=Balance(amount=FVal('17.988110986983157473')),
            location_label=user_address,
            notes='Send 17.988110986983157473 UNI-V2 POLS-WETH to uniswap-v2 pool',
            counterparty=CPT_UNISWAP_V2,
            address=string_to_evm_address('0xFfA98A091331Df4600F87C9164cD27e8a5CD2405'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=240,
            timestamp=TimestampMS(1615943669000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:1/erc20:0x83e6f1E41cdd28eAcEB20Cb649155049Fac3D5Aa'),
            balance=Balance(amount=FVal('518.338444992444885019')),
            location_label=user_address,
            notes='Remove 518.338444992444885019 POLS from uniswap-v2 LP 0xFfA98A091331Df4600F87C9164cD27e8a5CD2405',  # noqa: E501
            counterparty=CPT_UNISWAP_V2,
            address=string_to_evm_address('0xFfA98A091331Df4600F87C9164cD27e8a5CD2405'),
            extra_data={'pool_address': '0xFfA98A091331Df4600F87C9164cD27e8a5CD2405'},
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=241,
            timestamp=TimestampMS(1615943669000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
            balance=Balance(amount=FVal('1.378246251315897532')),
            location_label=user_address,
            notes='Remove 1.378246251315897532 WETH from uniswap-v2 LP 0xFfA98A091331Df4600F87C9164cD27e8a5CD2405',  # noqa: E501
            counterparty=CPT_UNISWAP_V2,
            address=string_to_evm_address('0xFfA98A091331Df4600F87C9164cD27e8a5CD2405'),
            extra_data={'pool_address': '0xFfA98A091331Df4600F87C9164cD27e8a5CD2405'},
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x3163Bb273E8D9960Ce003fD542bF26b4C529f515']])
def test_claim_airdrop(ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x0e50e7374e0ffbe0aea82dbe94a04ab0da3981f3bfb1a66927eb250c7aff29e3')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hex)
    timestamp = TimestampMS(1600446008000)
    gas_amount, claimed_amount = '0.027890731101011885', '408.638074'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_amount)),
            location_label=user_address,
            notes=f'Burned {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=163,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=A_UNI,
            balance=Balance(amount=FVal(claimed_amount)),
            location_label=user_address,
            notes=f'Claim {claimed_amount} UNI from the uniswap airdrop',
            counterparty=CPT_UNISWAP,
            address=UNISWAP_DISTRIBUTOR,
            extra_data={AIRDROP_IDENTIFIER_KEY: 'uniswap'},
        ),
    ]
    assert events == expected_events
