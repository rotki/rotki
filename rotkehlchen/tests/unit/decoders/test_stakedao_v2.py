from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import get_evm_token
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.stakedao.v2.constants import CPT_STAKEDAO_V2
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import globaldb_set_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import CacheType, Location, TimestampMS, deserialize_evm_tx_hash

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
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.STAKEDAO_V2_VAULTS, str(ethereum_inquirer.chain_id.serialize())),
            values=[','.join([
                (vault_addr := string_to_evm_address('0xCA137e3853Eab95541290B372223e7F2ee4c0cFa')),  # noqa: E501
                (underlying_addr := string_to_evm_address('0x13e12BB0E6A2f1A3d6901a59a9d585e89A6243e1')),  # noqa: E501
            ])],
        )
    tx_hash = deserialize_evm_tx_hash('0xdf9d446855c7a77c8baba4bc0260a711ad02818597009f88c69d1cbc6dc34902')  # noqa: E501
    assert get_evm_token(evm_address=vault_addr, chain_id=ethereum_inquirer.chain_id) is None
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert (vault_token := get_evm_token(evm_address=vault_addr, chain_id=ethereum_inquirer.chain_id)) is not None  # noqa: E501
    assert vault_token.symbol == 'sd-crvfrxUSD-vault'
    assert vault_token.name == 'Stake DAO crvUSD/frxUSD Vault'
    assert vault_token.protocol == CPT_STAKEDAO_V2
    assert vault_token.underlying_tokens is not None
    assert len(vault_token.underlying_tokens) == 1
    assert vault_token.underlying_tokens[0].address == underlying_addr
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
        asset=Asset(f'eip155:1/erc20:{underlying_addr}'),
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
        asset=Asset(f'eip155:1/erc20:{underlying_addr}'),
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
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.STAKEDAO_V2_VAULTS, str(arbitrum_one_inquirer.chain_id.serialize())),  # noqa: E501
            values=[','.join([
                (vault_addr := string_to_evm_address('0x52c43c76D268cF9a343b9aAA38974a50c455f372')),  # noqa: E501
                (underlying_addr := string_to_evm_address('0x78483d06a82ae76E0FF9C72AFd80E5B2CEA3b2A0')),  # noqa: E501
            ])],
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
        asset=Asset(f'eip155:42161/erc20:{vault_addr}'),
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
        asset=Asset(f'eip155:42161/erc20:{underlying_addr}'),
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


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x2e32935bfD5B2718f99BC8FDf8B37c16811f7D97']])
def test_votemarket_claim(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x3242696cf8a0ec3133f1b9051c72d4276680b463f350eaa2fb78fe35e61d2df1')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1771885232000)),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00001255506'),
        location_label=(user_address := arbitrum_one_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(send_amount := '0.000320795167961202'),
        location_label=user_address,
        notes=f'Spend {send_amount} ETH as StakeDAO votemarket fee',
        counterparty=CPT_STAKEDAO_V2,
        address=string_to_evm_address('0x67346f8b9B7dDA4639600C190DDaEcDc654359c8'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=(pusdc := Asset('eip155:42161/erc20:0xc8a096b7D583FC1CC4692563D61d41642cED8441')),
        amount=FVal(claim_1 := '17.10298'),
        location_label=user_address,
        notes=f'Claim {claim_1} pUSDC from StakeDAO votemarket',
        counterparty=CPT_STAKEDAO_V2,
        address=string_to_evm_address('0x8c2c5A295450DDFf4CB360cA73FCCC12243D14D9'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=5,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=pusdc,
        amount=FVal(claim_2 := '19.603382'),
        location_label=user_address,
        notes=f'Claim {claim_2} pUSDC from StakeDAO votemarket',
        counterparty=CPT_STAKEDAO_V2,
        address=string_to_evm_address('0x8c2c5A295450DDFf4CB360cA73FCCC12243D14D9'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=8,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=pusdc,
        amount=FVal(claim_3 := '19.429821'),
        location_label=user_address,
        notes=f'Claim {claim_3} pUSDC from StakeDAO votemarket',
        counterparty=CPT_STAKEDAO_V2,
        address=string_to_evm_address('0x8c2c5A295450DDFf4CB360cA73FCCC12243D14D9'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=11,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=pusdc,
        amount=FVal(claim_4 := '18.851606'),
        location_label=user_address,
        notes=f'Claim {claim_4} pUSDC from StakeDAO votemarket',
        counterparty=CPT_STAKEDAO_V2,
        address=string_to_evm_address('0x8c2c5A295450DDFf4CB360cA73FCCC12243D14D9'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=14,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=pusdc,
        amount=FVal(claim_5 := '18.70199'),
        location_label=user_address,
        notes=f'Claim {claim_5} pUSDC from StakeDAO votemarket',
        counterparty=CPT_STAKEDAO_V2,
        address=string_to_evm_address('0x8c2c5A295450DDFf4CB360cA73FCCC12243D14D9'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=17,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=pusdc,
        amount=FVal(claim_6 := '13.849516'),
        location_label=user_address,
        notes=f'Claim {claim_6} pUSDC from StakeDAO votemarket',
        counterparty=CPT_STAKEDAO_V2,
        address=string_to_evm_address('0x8c2c5A295450DDFf4CB360cA73FCCC12243D14D9'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=20,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=pusdc,
        amount=FVal(claim_7 := '13.65876'),
        location_label=user_address,
        notes=f'Claim {claim_7} pUSDC from StakeDAO votemarket',
        counterparty=CPT_STAKEDAO_V2,
        address=string_to_evm_address('0x8c2c5A295450DDFf4CB360cA73FCCC12243D14D9'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=23,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=pusdc,
        amount=FVal(claim_8 := '11.528301'),
        location_label=user_address,
        notes=f'Claim {claim_8} pUSDC from StakeDAO votemarket',
        counterparty=CPT_STAKEDAO_V2,
        address=string_to_evm_address('0x8c2c5A295450DDFf4CB360cA73FCCC12243D14D9'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x0b304924fAa64b0f040dcA67bC5175Dd6078db52']])
def test_votemarket_bridge_out(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x64e762b0ce41613885695864d491b34a786e7f72e601df5a56d26b5fd82ecaa5')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1770875434000)),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00000877252'),
        location_label=(user_address := arbitrum_one_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:42161/erc20:0x9243A659a67D2Edae7edEf1aDaDCCD5dAb3B0FdA'),
        amount=ZERO,
        location_label=user_address,
        notes='Revoke pOGN spending approval of 0x0b304924fAa64b0f040dcA67bC5175Dd6078db52 by 0x67346f8b9B7dDA4639600C190DDaEcDc654359c8',  # noqa: E501
        address=string_to_evm_address('0x67346f8b9B7dDA4639600C190DDaEcDc654359c8'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=5,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:42161/erc20:0x84EC7B0923ff2d17152256aD36a33184e0079c9b'),
        amount=ZERO,
        location_label=user_address,
        notes='Revoke popASF spending approval of 0x0b304924fAa64b0f040dcA67bC5175Dd6078db52 by 0x67346f8b9B7dDA4639600C190DDaEcDc654359c8',  # noqa: E501
        address=string_to_evm_address('0x67346f8b9B7dDA4639600C190DDaEcDc654359c8'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=7,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:42161/erc20:0x5660bdD5AD5F4ccD27ECc33f6Ef140079e7E9cb8'),
        amount=ZERO,
        location_label=user_address,
        notes='Revoke pWFRAX spending approval of 0x0b304924fAa64b0f040dcA67bC5175Dd6078db52 by 0x67346f8b9B7dDA4639600C190DDaEcDc654359c8',  # noqa: E501
        address=string_to_evm_address('0x67346f8b9B7dDA4639600C190DDaEcDc654359c8'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=9,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:42161/erc20:0x8D037f300C70A2194aD7dB16d54c3A14FdC7B0A2'),
        amount=ZERO,
        location_label=user_address,
        notes='Revoke pOUSD spending approval of 0x0b304924fAa64b0f040dcA67bC5175Dd6078db52 by 0x67346f8b9B7dDA4639600C190DDaEcDc654359c8',  # noqa: E501
        address=string_to_evm_address('0x67346f8b9B7dDA4639600C190DDaEcDc654359c8'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=10,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=Asset('eip155:42161/erc20:0x9243A659a67D2Edae7edEf1aDaDCCD5dAb3B0FdA'),
        amount=FVal(bridge_1 := '4662.160703455214399592'),
        location_label=user_address,
        notes=f'Bridge {bridge_1} pOGN from Arbitrum One to Ethereum for {user_address} via StakeDAO votemarket',  # noqa: E501
        counterparty=CPT_STAKEDAO_V2,
        address=string_to_evm_address('0x67346f8b9B7dDA4639600C190DDaEcDc654359c8'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=11,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=Asset('eip155:42161/erc20:0x84EC7B0923ff2d17152256aD36a33184e0079c9b'),
        amount=FVal(bridge_2 := '560.714771248050753093'),
        location_label=user_address,
        notes=f'Bridge {bridge_2} popASF from Arbitrum One to Ethereum for {user_address} via StakeDAO votemarket',  # noqa: E501
        counterparty=CPT_STAKEDAO_V2,
        address=string_to_evm_address('0x67346f8b9B7dDA4639600C190DDaEcDc654359c8'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=12,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=Asset('eip155:42161/erc20:0x5660bdD5AD5F4ccD27ECc33f6Ef140079e7E9cb8'),
        amount=FVal(bridge_3 := '74.646308931723360141'),
        location_label=user_address,
        notes=f'Bridge {bridge_3} pWFRAX from Arbitrum One to Ethereum for {user_address} via StakeDAO votemarket',  # noqa: E501
        counterparty=CPT_STAKEDAO_V2,
        address=string_to_evm_address('0x67346f8b9B7dDA4639600C190DDaEcDc654359c8'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=13,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=Asset('eip155:42161/erc20:0x8D037f300C70A2194aD7dB16d54c3A14FdC7B0A2'),
        amount=FVal(bridge_4 := '27.616214928846510245'),
        location_label=user_address,
        notes=f'Bridge {bridge_4} pOUSD from Arbitrum One to Ethereum for {user_address} via StakeDAO votemarket',  # noqa: E501
        counterparty=CPT_STAKEDAO_V2,
        address=string_to_evm_address('0x67346f8b9B7dDA4639600C190DDaEcDc654359c8'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=14,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(bridge_fee := '0.000294853053533268'),
        location_label=user_address,
        notes=f'Spend {bridge_fee} ETH as StakeDAO votemarket bridge fee',
        counterparty=CPT_STAKEDAO_V2,
        address=string_to_evm_address('0x67346f8b9B7dDA4639600C190DDaEcDc654359c8'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=15,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REFUND,
        asset=A_ETH,
        amount=FVal(refund_amount := '0.00000578143242222'),
        location_label=user_address,
        notes=f'Refund of {refund_amount} ETH from StakeDAO votemarket bridge',
        counterparty=CPT_STAKEDAO_V2,
        address=string_to_evm_address('0xF0000058000021003E4754dCA700C766DE7601C2'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x0b304924fAa64b0f040dcA67bC5175Dd6078db52']])
def test_votemarket_bridge_in(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash(
        '0xfa2ffd8656f2c485ff2c0d95fe8d465826bbb2bf14daf313e77210f46c023ba9',
    )
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1770876623000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=Asset('eip155:1/erc20:0x8207c1FfC5B6804F6024322CcF34F29c3541Ae26'),
        amount=FVal(bridge_1 := '4662.160703455214399592'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Bridge {bridge_1} OGN from Arbitrum One to Ethereum for {user_address} via StakeDAO votemarket',  # noqa: E501
        counterparty=CPT_STAKEDAO_V2,
        address=string_to_evm_address('0x96006425Da428E45c282008b00004a00002B345e'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=Asset('eip155:1/erc20:0x7fE24F1A024D33506966CB7CA48Bab8c65fB632d'),
        amount=FVal(bridge_2 := '560.714771248050753093'),
        location_label=user_address,
        notes=f'Bridge {bridge_2} opASF from Arbitrum One to Ethereum for {user_address} via StakeDAO votemarket',  # noqa: E501
        counterparty=CPT_STAKEDAO_V2,
        address=string_to_evm_address('0x96006425Da428E45c282008b00004a00002B345e'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=Asset('eip155:1/erc20:0x04ACaF8D2865c0714F79da09645C13FD2888977f'),
        amount=FVal(bridge_3 := '74.646308931723360141'),
        location_label=user_address,
        notes=f'Bridge {bridge_3} WFRAX from Arbitrum One to Ethereum for {user_address} via StakeDAO votemarket',  # noqa: E501
        counterparty=CPT_STAKEDAO_V2,
        address=string_to_evm_address('0x96006425Da428E45c282008b00004a00002B345e'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=Asset('eip155:1/erc20:0x2A8e1E676Ec238d8A992307B495b45B3fEAa5e86'),
        amount=FVal(bridge_4 := '27.616214928846510245'),
        location_label=user_address,
        notes=f'Bridge {bridge_4} OUSD from Arbitrum One to Ethereum for {user_address} via StakeDAO votemarket',  # noqa: E501
        counterparty=CPT_STAKEDAO_V2,
        address=string_to_evm_address('0x96006425Da428E45c282008b00004a00002B345e'),
    )]
