from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset, UnderlyingToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.stakedao.v2.constants import CPT_STAKEDAO_V2
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, TokenKind, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x4F243B4b795502AA5Cf562cB42EccD444c0321b0']])
def test_vault_deposit(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    vault_token = get_or_create_evm_token(
        userdb=ethereum_inquirer.database,
        evm_address=string_to_evm_address('0xCA137e3853Eab95541290B372223e7F2ee4c0cFa'),
        chain_id=ethereum_inquirer.chain_id,
        symbol='sd-crvfrxUSD-vault',
        name='Stake DAO crvUSD/frxUSD Vault',
        protocol=CPT_STAKEDAO_V2,
        underlying_tokens=[UnderlyingToken(
            address=(underlying_token := get_or_create_evm_token(
                userdb=ethereum_inquirer.database,
                evm_address=string_to_evm_address('0x13e12BB0E6A2f1A3d6901a59a9d585e89A6243e1'),
                chain_id=ethereum_inquirer.chain_id,
                symbol='crvfrxUSD',
                name='crvUSD/frxUSD',
            )).evm_address,
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )
    tx_hash = deserialize_evm_tx_hash('0xdf9d446855c7a77c8baba4bc0260a711ad02818597009f88c69d1cbc6dc34902')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1761791039000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.001560228422549888'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=32,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=underlying_token,
        amount=ZERO,
        location_label=user_address,
        notes=f'Revoke crvfrxUSD spending approval of {user_address} by {vault_token.evm_address}',
        address=vault_token.evm_address,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=33,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=underlying_token,
        amount=FVal(deposit_amount := '96962.496900975243663975'),
        location_label=user_address,
        notes=f'Deposit {deposit_amount} crvfrxUSD in StakeDAO',
        counterparty=CPT_STAKEDAO_V2,
        address=string_to_evm_address('0x52f541764E6e90eeBc5c21Ff570De0e2D63766B6'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=34,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=vault_token,
        amount=FVal(receive_amount := '96962.496900975243663975'),
        location_label=user_address,
        notes=f'Receive {receive_amount} sd-crvfrxUSD-vault after deposit in StakeDAO',
        counterparty=CPT_STAKEDAO_V2,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xA6174cb9779661A182F8207dbdC1458bb653FDCc']])
def test_vault_withdraw(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    vault_token = get_or_create_evm_token(
        userdb=arbitrum_one_inquirer.database,
        evm_address=string_to_evm_address('0x52c43c76D268cF9a343b9aAA38974a50c455f372'),
        chain_id=arbitrum_one_inquirer.chain_id,
        symbol='sd-alUSDUSDC-vault',
        name='Stake DAO alUSD/USDC Vault',
        protocol=CPT_STAKEDAO_V2,
        underlying_tokens=[UnderlyingToken(
            address=(underlying_token := get_or_create_evm_token(
                userdb=arbitrum_one_inquirer.database,
                evm_address=string_to_evm_address('0x78483d06a82ae76E0FF9C72AFd80E5B2CEA3b2A0'),
                chain_id=arbitrum_one_inquirer.chain_id,
                symbol='alUSDUSDC',
                name='alUSD/USDC',
            )).evm_address,
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )
    tx_hash = deserialize_evm_tx_hash('0x88cae3b3c521f4b5db1f85899ecdb4f3b6feb0cafef92b07e0087e98790bebc5')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1763219831000)),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00000506625'),
        location_label=(user_address := arbitrum_one_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=vault_token,
        amount=FVal(return_amount := '2028.096975475269105104'),
        location_label=user_address,
        notes=f'Return {return_amount} sd-alUSDUSDC-vault to StakeDAO',
        counterparty=CPT_STAKEDAO_V2,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=underlying_token,
        amount=FVal(withdraw_amount := '2028.096975475269105104'),
        location_label=user_address,
        notes=f'Withdraw {withdraw_amount} alUSDUSDC from StakeDAO',
        counterparty=CPT_STAKEDAO_V2,
        address=string_to_evm_address('0xe5d6D047DF95c6627326465cB27B64A8b77A8b91'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x30044b7C080A6e456386d5b9c370Dc7c259AE2cd']])
def test_claim_from_accountant(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xfdc4cf33482072219ae333ab5eacec615d18be1a8b4fe80afb0bfbb9c6e2ad66')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1763462549000)),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.0000036404'),
        location_label=(user_address := arbitrum_one_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=18,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=Asset('eip155:42161/erc20:0x11cDb42B0EB46D95f990BeDD4695A6e3fA034978'),
        amount=FVal(claim_amount := '30.540820796635738526'),
        location_label=user_address,
        notes=f'Claim {claim_amount} CRV from StakeDAO',
        counterparty=CPT_STAKEDAO_V2,
        address=string_to_evm_address('0x93b4B9bd266fFA8AF68e39EDFa8cFe2A62011Ce0'),
    )]
