from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import get_single_underlying_token
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.safe.constants import CPT_SAFE_MULTISIG
from rotkehlchen.chain.evm.decoding.superfluid.constants import CPT_SUPERFLUID
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_WXDAI, A_XDAI
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import globaldb_set_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.optimism import OPTIMISM_MAINNET_NODE
from rotkehlchen.types import (
    CacheType,
    ChainID,
    ChecksumEvmAddress,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer


def _setup_super_token_cache(
        chain_id: ChainID,
        super_token: str,
        underlying_token: str | None = None,
) -> None:
    """Add the given super token to the general cache so decoding related txs works correctly."""
    if underlying_token is None:
        underlying_token = 'native'

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.SUPERFLUID_SUPER_TOKENS, str(chain_id.serialize_for_db())),
            values=[f'{super_token},{underlying_token}'],
        )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x56a1A34F0d33788ebA53e2706854A37A5F275536']])
def test_token_upgrade(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    _setup_super_token_cache(
        chain_id=arbitrum_one_inquirer.chain_id,
        super_token=(super_token_address := string_to_evm_address('0xFc55F2854e74b4f42D01a6d3DAAC4c52D9dfdcFf')),  # noqa: E501
        underlying_token=(underlying_token_address := string_to_evm_address('0xaf88d065e77c8cC2239327C5EDb3A432268e5831')),  # noqa: E501
    )
    tx_hash = deserialize_evm_tx_hash('0x33f13f009fa63df4689bf9011df3174e268cd3b8c15e785bc4693f63dec44bbd')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1765230188000)),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00000096384'),
        location_label=(user_address := arbitrum_one_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=(underlying_token := Asset(f'eip155:42161/erc20:{underlying_token_address}')),
        amount=FVal(wrap_amount := '4'),
        location_label=user_address,
        notes=f'Wrap {wrap_amount} USDC with Superfluid super token',
        counterparty=CPT_SUPERFLUID,
        address=super_token_address,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=(super_token := Asset(f'eip155:42161/erc20:{super_token_address}')),
        amount=FVal(wrap_amount),
        location_label=user_address,
        notes=f'Receive {wrap_amount} USDCx from Superfluid',
        counterparty=CPT_SUPERFLUID,
        address=ZERO_ADDRESS,
    )]
    # also check that the super token was created properly
    super_token = super_token.resolve_to_evm_token()
    assert get_single_underlying_token(super_token) == underlying_token
    assert super_token.protocol == CPT_SUPERFLUID


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9dB850A236A4AF48eFc4B549e07FFBAc8D5d6388']])
def test_native_upgrade(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    _setup_super_token_cache(
        chain_id=ethereum_inquirer.chain_id,
        super_token=(super_token_address := string_to_evm_address('0xC22BeA0Be9872d8B7B3933CEc70Ece4D53A900da')),  # noqa: E501
    )
    tx_hash = deserialize_evm_tx_hash('0x52a5caac12f19ec610a5182815f12bb2d4e47e1e603d4dfebae71aa4a785709a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1764591623000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000009698056558752'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_ETH,
        amount=FVal(wrap_amount := '0.01'),
        location_label=user_address,
        notes=f'Wrap {wrap_amount} ETH with Superfluid super token',
        counterparty=CPT_SUPERFLUID,
        address=super_token_address,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset(f'eip155:1/erc20:{super_token_address}'),
        amount=FVal(wrap_amount),
        location_label=user_address,
        notes=f'Receive {wrap_amount} ETHx from Superfluid',
        counterparty=CPT_SUPERFLUID,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_manager_connect_at_start', [(OPTIMISM_MAINNET_NODE,)])
@pytest.mark.parametrize('optimism_accounts', [['0x0BeBD2FcA9854F657329324aA7dc90F656395189']])
def test_token_downgrade(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
) -> None:
    _setup_super_token_cache(
        chain_id=optimism_inquirer.chain_id,
        super_token=(super_token_address := string_to_evm_address('0x1828Bff08BD244F7990edDCd9B19cc654b33cDB4')),  # noqa: E501
        underlying_token=(underlying_token_address := string_to_evm_address('0x4200000000000000000000000000000000000042')),  # noqa: E501
    )
    tx_hash = deserialize_evm_tx_hash('0x7157b063a1da86a45ed3d6a022fb48d74f1ab2d76db39179a785e93bf86be675')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1710495225000)),
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=Asset(f'eip155:10/erc20:{super_token_address}'),
        amount=FVal(unwrap_amount := '57132.8001858056214645'),
        location_label=(user_address := optimism_accounts[0]),
        notes=f'Return {unwrap_amount} OPx to Superfluid',
        counterparty=CPT_SUPERFLUID,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=Asset(f'eip155:10/erc20:{underlying_token_address}'),
        amount=FVal(unwrap_amount),
        location_label=user_address,
        notes=f'Unwrap {unwrap_amount} OP from Superfluid',
        counterparty=CPT_SUPERFLUID,
        address=super_token_address,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=70,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ZERO,
        location_label='0x17FEA6550d0C9d56B257aF6235E80B02B43F1E21',
        notes=f'Successfully executed safe transaction 0xafbf20785cb6f9140e91ed5ae0eaeee225451da44f369a971aec4e0f6f0e24f0 for multisig {user_address}',  # noqa: E501
        counterparty=CPT_SAFE_MULTISIG,
        address=user_address,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0xC224cd7Ab43c5150Dfc60B153a433a43600107F2']])
def test_wrapped_native_downgrade(
        gnosis_inquirer: 'GnosisInquirer',
        gnosis_accounts: list['ChecksumEvmAddress'],
) -> None:
    _setup_super_token_cache(
        chain_id=gnosis_inquirer.chain_id,
        super_token=(super_token_address := string_to_evm_address('0x59988e47A3503AaFaA0368b9deF095c818Fdca01')),  # noqa: E501
    )
    tx_hash = deserialize_evm_tx_hash('0x62e1329db9eededf8b9861efc6964ea749f29d7061a2bfbf76ad2b72424de7ad')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1765169835000)),
        location=Location.GNOSIS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_XDAI,
        amount=FVal(gas_amount := '0.0002731'),
        location_label=(user_address := gnosis_accounts[0]),
        notes=f'Burn {gas_amount} XDAI for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=Asset(f'eip155:100/erc20:{super_token_address}'),
        amount=FVal(unwrap_amount := '0.82349143579240667'),
        location_label=user_address,
        notes=f'Return {unwrap_amount} xDAIx to Superfluid',
        counterparty=CPT_SUPERFLUID,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_WXDAI,
        amount=FVal(unwrap_amount),
        location_label=user_address,
        notes=f'Unwrap {unwrap_amount} WXDAI from Superfluid',
        counterparty=CPT_SUPERFLUID,
        address=super_token_address,
    )]
