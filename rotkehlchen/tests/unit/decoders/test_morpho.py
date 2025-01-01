from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.morpho.constants import CPT_MORPHO
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_USDC, A_USDT, A_WETH_BASE
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import globaldb_set_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.unit.decoders.test_zerox import A_BASE_USDC
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.morpho import (
    create_base_morpho_vault_token,
    create_base_morpho_vault_tokens_for_bundler_test,
    create_ethereum_morpho_vault_token,
)
from rotkehlchen.types import (
    CacheType,
    ChainID,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress


def _add_morpho_reward_distributor(chain_id: ChainID, address: str):
    """Add Morpho reward distributor address to cache for proper decoding."""
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(
                CacheType.MORPHO_REWARD_DISTRIBUTORS,
                str(chain_id),
            ),
            values=[address],
        )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_morpho_deposit_base(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xf1bfb66819293de78d82ccf1d076ef4987114d01716ddc1d846f4c806df200c0')  # noqa: E501
    vault_token = create_base_morpho_vault_token(database=base_inquirer.database)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, deposit_amount, receive_amount = TimestampMS(1731100821000), base_accounts[0], '0.000007106536379632', '51.573591', '51.333358693113784641'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_amount)),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=496,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_BASE_USDC,
            balance=Balance(amount=FVal(deposit_amount)),
            location_label=user_address,
            notes=f'Set USDC spending approval of {user_address} by 0x23055618898e202386e6c13955a58D3C68200BFB to {deposit_amount}',  # noqa: E501
            address=string_to_evm_address('0x23055618898e202386e6c13955a58D3C68200BFB'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=497,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_BASE_USDC,
            balance=Balance(amount=FVal(deposit_amount)),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} USDC in a Morpho vault',
            counterparty=CPT_MORPHO,
            address=string_to_evm_address('0x23055618898e202386e6c13955a58D3C68200BFB'),
            extra_data={'vault': vault_token.evm_address},
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=498,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=vault_token,
            balance=Balance(amount=FVal(receive_amount)),
            location_label=user_address,
            notes=f'Receive {receive_amount} mwUSDC after deposit in a Morpho vault',
            counterparty=CPT_MORPHO,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0xCa17262d6b9B1F5e1995dAdB35d63f9f53896387']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_morpho_deposit_base_bundler(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test that using the bundler to move funds between vaults is decoded correctly."""
    tx_hash = deserialize_evm_tx_hash('0x7da62153ad02205b019c8af287a9e3232e672dcb5a9ec7217f8f17de3011b168')  # noqa: E501
    re7_token, pyth_token = create_base_morpho_vault_tokens_for_bundler_test(database=base_inquirer.database)  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount = TimestampMS(1731679657000), base_accounts[0], '0.000033559670856685'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_amount)),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=334,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=re7_token,
            balance=Balance(amount=FVal('0.080036912194887522')),
            location_label=user_address,
            notes=f'Set Re7WETH spending approval of {user_address} by 0x23055618898e202386e6c13955a58D3C68200BFB to 0.080036912194887522',  # noqa: E501
            address=string_to_evm_address('0x23055618898e202386e6c13955a58D3C68200BFB'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=335,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=re7_token,
            balance=Balance(amount=FVal('0.080036912194887522')),
            location_label=user_address,
            notes='Return 0.080036912194887522 Re7WETH to a Morpho vault',
            counterparty=CPT_MORPHO,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=336,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_WETH_BASE,
            balance=Balance(amount=FVal('0.081308576708772071')),
            location_label=user_address,
            notes='Withdraw 0.081308576708772071 WETH from a Morpho vault',
            counterparty=CPT_MORPHO,
            address=re7_token.evm_address,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=337,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_WETH_BASE,
            balance=Balance(amount=FVal('0.081308574347035883')),
            location_label=user_address,
            notes='Deposit 0.081308574347035883 WETH in a Morpho vault',
            counterparty=CPT_MORPHO,
            address=pyth_token.evm_address,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=338,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=pyth_token,
            balance=Balance(amount=FVal('0.080458744637341029')),
            location_label=user_address,
            notes='Receive 0.080458744637341029 pythETH after deposit in a Morpho vault',
            counterparty=CPT_MORPHO,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x315178907fE88C7B8CC09D51F03ffb60A55e11e5']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_morpho_withdraw_base(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x72782434a36d0bd5c26751b344dcf301b1510b63cac7d67596b34642bf068a51')  # noqa: E501
    vault_token = create_base_morpho_vault_token(database=base_inquirer.database)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, return_amount, withdraw_amount = TimestampMS(1731408939000), base_accounts[0], '0.000009372834639654', '9951.725252259523570499', '10000'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_amount)),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=vault_token,
            balance=Balance(amount=FVal(return_amount)),
            location_label=user_address,
            notes=f'Return {return_amount} mwUSDC to a Morpho vault',
            counterparty=CPT_MORPHO,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_BASE_USDC,
            balance=Balance(amount=FVal(withdraw_amount)),
            location_label=user_address,
            notes=f'Withdraw {withdraw_amount} USDC from a Morpho vault',
            counterparty=CPT_MORPHO,
            address=vault_token.evm_address,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x7f2A099EEdE569438584790d2126202B39036831']])
def test_morpho_claim_reward_base(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xf1c08fcee3717217b30cbd5e120a4079837e319064d8c01a28d9fb7f44fcb88b')  # noqa: E501
    _add_morpho_reward_distributor(chain_id=ChainID.BASE, address='0x5400dBb270c956E8985184335A1C62AcA6Ce1333')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, reward_amount = TimestampMS(1731272621000), base_accounts[0], '0.000024248426432951', '0.033158'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_amount)),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=591,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_BASE_USDC,
            balance=Balance(amount=FVal(reward_amount)),
            location_label=user_address,
            notes=f'Claim {reward_amount} USDC from Morpho',
            counterparty=CPT_MORPHO,
            address=string_to_evm_address('0x5400dBb270c956E8985184335A1C62AcA6Ce1333'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xECdb72619533A9dC55D6E170F0D905744DcdDa6E']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_morpho_deposit_ethereum(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x3dabc0f6b3b795249b9b1d2b5398e09487f1321aacfc80242e9d6171051a99a8')  # noqa: E501
    vault_token = create_ethereum_morpho_vault_token(database=ethereum_inquirer.database)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, deposit_amount, receive_amount = TimestampMS(1731354683000), ethereum_accounts[0], '0.019537376734385857', '200', '194.826292786685129719'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_amount)),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=406,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_USDC,
            balance=Balance(amount=FVal(deposit_amount)),
            location_label=user_address,
            notes=f'Set USDC spending approval of {user_address} by 0x4095F064B8d3c3548A3bebfd0Bbfd04750E30077 to {deposit_amount}',  # noqa: E501
            address=string_to_evm_address('0x4095F064B8d3c3548A3bebfd0Bbfd04750E30077'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=407,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_USDC,
            balance=Balance(amount=FVal(deposit_amount)),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} USDC in a Morpho vault',
            counterparty=CPT_MORPHO,
            address=string_to_evm_address('0x4095F064B8d3c3548A3bebfd0Bbfd04750E30077'),
            extra_data={'vault': vault_token.evm_address},
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=408,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=vault_token,
            balance=Balance(amount=FVal(receive_amount)),
            location_label=user_address,
            notes=f'Receive {receive_amount} USUALUSDC+ after deposit in a Morpho vault',
            counterparty=CPT_MORPHO,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x7E4E766d0aE5ea9cDED0c694669194Db92800107']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_morpho_withdraw_ethereum(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x8d3a5be47ff121846a85c84e9f1f487c43f66eadd5a3607f6c767ffc6704b50f')  # noqa: E501
    vault_token = create_ethereum_morpho_vault_token(database=ethereum_inquirer.database)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, approve_amount, return_amount, withdraw_amount = TimestampMS(1731405887000), ethereum_accounts[0], '0.035931819008110328', '1141398.660779466856241893', '1141393.264141539859656044', '1172000'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_amount)),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=572,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=vault_token,
            balance=Balance(amount=FVal(approve_amount)),
            location_label=user_address,
            notes=f'Set USUALUSDC+ spending approval of {user_address} by 0x4095F064B8d3c3548A3bebfd0Bbfd04750E30077 to {approve_amount}',  # noqa: E501
            address=string_to_evm_address('0x4095F064B8d3c3548A3bebfd0Bbfd04750E30077'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=573,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=vault_token,
            balance=Balance(amount=FVal(return_amount)),
            location_label=user_address,
            notes=f'Return {return_amount} USUALUSDC+ to a Morpho vault',
            counterparty=CPT_MORPHO,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=574,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_USDC,
            balance=Balance(amount=FVal(withdraw_amount)),
            location_label=user_address,
            notes=f'Withdraw {withdraw_amount} USDC from a Morpho vault',
            counterparty=CPT_MORPHO,
            address=vault_token.evm_address,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xFa3542E4047cA13E66f650740a587736d06d1100']])
def test_morpho_claim_reward_ethereum(
        ethereum_inquirer: 'BaseInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x1a6775590dfffdc2da036ec280627a65c57140b921d5afd11cabe913c78edcba')  # noqa: E501
    _add_morpho_reward_distributor(chain_id=ChainID.ETHEREUM, address='0x330eefa8a787552DC5cAd3C3cA644844B1E61Ddb')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, user_address, reward_amount = TimestampMS(1730476199000), ethereum_accounts[0], '13.56253'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=285,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_USDT,
            balance=Balance(amount=FVal(reward_amount)),
            location_label=user_address,
            notes=f'Claim {reward_amount} USDT from Morpho',
            counterparty=CPT_MORPHO,
            address=string_to_evm_address('0x330eefa8a787552DC5cAd3C3cA644844B1E61Ddb'),
        ),
    ]
