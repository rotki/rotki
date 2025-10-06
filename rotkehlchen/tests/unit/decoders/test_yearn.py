from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset, UnderlyingToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.modules.yearn.constants import (
    CPT_YEARN_V1,
    CPT_YEARN_V2,
    CPT_YEARN_V3,
    YEARN_PARTNER_TRACKER,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_1INCH, A_DAI, A_ETH, A_USDC, A_YFI
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    Location,
    Timestamp,
    TimestampMS,
    TokenKind,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.fixture(name='curve_savings_vault')
def fixture_yearn_v3_curve_savings_vault(database: 'DBHandler') -> 'EvmToken':
    return get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0x0655977FEb2f289A4aB78af67BAB0d17aAb84367'),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        symbol='scrvUSD',
        name='Curve Savings',
        protocol=CPT_YEARN_V3,
        underlying_tokens=[UnderlyingToken(
            address=string_to_evm_address('0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E'),
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd0002c648CCa8DeE2f2b8D70D542Ccde8ad6EC03']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_deposit_yearn_v3(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0xa622b53ffa01e0f843d42464a0cb3b3ef192229522fa523139a15c08940dd213')  # noqa: E501
    get_or_create_evm_token(
        userdb=ethereum_inquirer.database,
        evm_address=string_to_evm_address('0xBF319dDC2Edc1Eb6FDf9910E39b37Be221C8805F'),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        symbol='yvcrvUSD-2',
        name='crvUSD-2 yVault',
        decimals=18,
        protocol=CPT_YEARN_V3,
        started=Timestamp(1713104219),
        underlying_tokens=[UnderlyingToken(
            address=string_to_evm_address('0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E'),
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, vault_address = ethereum_accounts[0], string_to_evm_address('0xBF319dDC2Edc1Eb6FDf9910E39b37Be221C8805F')  # noqa: E501
    timestamp, gas_amount, deposit_amount, receive_amount, approve_amount = TimestampMS(1722289343000), '0.000357122879546472', '7445', '7336.974656759870797081', '57896044618658097711785492504343953926634992332820282012283.792003956564819967'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=213,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E'),
            amount=FVal(approve_amount),
            location_label=user_address,
            notes=f'Set crvUSD spending approval of {user_address} by {vault_address} to {approve_amount}',  # noqa: E501
            address=vault_address,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=214,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:1/erc20:0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E'),
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} crvUSD in yearn-v3 vault crvUSD-2 yVault',
            counterparty=CPT_YEARN_V3,
            address=vault_address,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=215,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xBF319dDC2Edc1Eb6FDf9910E39b37Be221C8805F'),
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} yvcrvUSD-2 after deposit in a yearn-v3 vault',
            counterparty=CPT_YEARN_V3,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x54991866A907891c9B85478CC1Fb0560B17D2b1D']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_withdraw_yearn_v3(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x18a1d6b96e3c561c593bf3604a0fa21f6b760b58231d5921933661c7ee5f856e')  # noqa: E501
    get_or_create_evm_token(
        userdb=ethereum_inquirer.database,
        evm_address=string_to_evm_address('0x028eC7330ff87667b6dfb0D94b954c820195336c'),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        symbol='yvDAI-1',
        name='DAI yVault',
        decimals=18,
        protocol=CPT_YEARN_V3,
        started=Timestamp(1710272855),
        underlying_tokens=[UnderlyingToken(
            address=string_to_evm_address('0x6B175474E89094C44Da98b954EedeAC495271d0F'),
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, spend_amount, withdraw_amount = ethereum_accounts[0], TimestampMS(1727442071000), '0.001061009713017075', '499.439625255006111083', '515.966865078770444084'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0x028eC7330ff87667b6dfb0D94b954c820195336c'),
            amount=FVal(spend_amount),
            location_label=user_address,
            notes=f'Return {spend_amount} yvDAI-1 to a yearn-v3 vault',
            counterparty=CPT_YEARN_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_DAI,
            amount=FVal(withdraw_amount),
            location_label=user_address,
            notes=f'Withdraw {withdraw_amount} DAI from yearn-v3 vault DAI yVault',
            counterparty=CPT_YEARN_V3,
            address=string_to_evm_address('0x028eC7330ff87667b6dfb0D94b954c820195336c'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x34A7a276eD77c6FE866c75Bbc8d79127c4E14a09']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_deposit_yearn_v2(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x7e6493bb2e0c09b9986ab43a562409fd2cf99caca3d1b65fa4b0d46ef5588081')  # noqa: E501
    get_or_create_evm_token(
        userdb=ethereum_inquirer.database,
        evm_address=string_to_evm_address('0xcC2EFb8bEdB6eD69ADeE0c3762470c38D4730C50'),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        symbol='yvCurve-crvDOLA-f',
        name='Curve crvDOLA Factory yVault',
        decimals=18,
        protocol=CPT_YEARN_V2,
        started=Timestamp(1635529757),
        underlying_tokens=[UnderlyingToken(
            address=string_to_evm_address('0xef484de8C07B6e2d732A92B5F78e81B38f99f95E'),
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, deposit_amount, receive_amount, approve_amount = TimestampMS(1729145687000), ethereum_accounts[0], '0.001446241576196176', '38541.366598671832692528', '38514.207134567395983686', '57896044618658097711785492504343953926634992332820281981187.425405284732127439'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=365,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0xef484de8C07B6e2d732A92B5F78e81B38f99f95E'),
            amount=FVal(approve_amount),
            location_label=user_address,
            notes=f'Set crvDOLA spending approval of {user_address} by {YEARN_PARTNER_TRACKER} to {approve_amount}',  # noqa: E501
            address=YEARN_PARTNER_TRACKER,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=366,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:1/erc20:0xef484de8C07B6e2d732A92B5F78e81B38f99f95E'),
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} crvDOLA in yearn-v2 vault',
            counterparty=CPT_YEARN_V2,
            address=YEARN_PARTNER_TRACKER,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=367,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xcC2EFb8bEdB6eD69ADeE0c3762470c38D4730C50'),
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} yvCurve-crvDOLA-f after deposit in a yearn-v2 vault',
            counterparty=CPT_YEARN_V2,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x4201A38615EC7D1F57Df6143E7a7ED82Dd7a8eE4']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_increase_deposit_yearn_v2(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x94111f9d55d22aad6eabc504fd2a5d1ca28b3c7895bc82e2fd4c66dbf1fe1ee8')  # noqa: E501
    get_or_create_evm_token(
        userdb=ethereum_inquirer.database,
        evm_address=string_to_evm_address('0xa354F35829Ae975e850e23e9615b11Da1B3dC4DE'),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        symbol='yvUSDC',
        name='USDC yVault',
        decimals=6,
        protocol=CPT_YEARN_V2,
        started=Timestamp(1635529757),
        underlying_tokens=[UnderlyingToken(
            address=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, deposit_amount, receive_amount = TimestampMS(1729346255000), ethereum_accounts[0], '0.0020739662607066', '10000', '9035.10865'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_USDC,
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} USDC in yearn-v2 vault',
            counterparty=CPT_YEARN_V2,
            address=YEARN_PARTNER_TRACKER,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xa354F35829Ae975e850e23e9615b11Da1B3dC4DE'),
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} yvUSDC after deposit in a yearn-v2 vault',
            counterparty=CPT_YEARN_V2,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9E406B2c2021966f3983E899643609C45E3bBFFe']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_withdraw_yearn_v2(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x4c06090b9efcd8bf75014fc7c340d5c2f93b800ac1a1ff09b867fec0417afdfa')  # noqa: E501
    get_or_create_evm_token(
        userdb=ethereum_inquirer.database,
        evm_address=string_to_evm_address('0x790a60024bC3aea28385b60480f15a0771f26D09'),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        symbol='yvCurve-YFIETH',
        name='Curve YFI-ETH Pool yVault',
        decimals=18,
        protocol=CPT_YEARN_V2,
        started=Timestamp(1644320324),
        underlying_tokens=[UnderlyingToken(
            address=string_to_evm_address('0x29059568bB40344487d62f7450E78b8E6C74e0e5'),
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, spend_amount, withdraw_amount, = TimestampMS(1724060255000), ethereum_accounts[0], '0.001505082528630685', '45.146296079003811902', '48.170851555046499871'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0x790a60024bC3aea28385b60480f15a0771f26D09'),
            amount=FVal(spend_amount),
            location_label=user_address,
            notes=f'Return {spend_amount} yvCurve-YFIETH to a yearn-v2 vault',
            counterparty=CPT_YEARN_V2,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:1/erc20:0x29059568bB40344487d62f7450E78b8E6C74e0e5'),
            amount=FVal(withdraw_amount),
            location_label=user_address,
            notes=f'Withdraw {withdraw_amount} YFIETH-f from yearn-v2 vault Curve YFI-ETH Pool yVault',  # noqa: E501
            counterparty=CPT_YEARN_V2,
            address=string_to_evm_address('0x790a60024bC3aea28385b60480f15a0771f26D09'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xb524c787669185E11d01C645D1910631e04Fa5Eb']])
def test_deposit_yearn_v2_without_logs(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x5d7e7646e3749fcd575ea76e35763fa8eeb6dfb83c4c242a4448ee1495f695ba')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1667679923000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(0.001003537266292329),
            location_label=user_address,
            notes='Burn 0.001003537266292329 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=157,
            timestamp=TimestampMS(1667679923000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_YFI,
            amount=FVal('115792089237316195423570985008687907853269984665640564039457.562087073129639935'),
            location_label=user_address,
            notes='Set YFI spending approval of 0xb524c787669185E11d01C645D1910631e04Fa5Eb by 0xdb25cA703181E7484a155DD612b06f57E12Be5F0 to 115792089237316195423570985008687907853269984665640564039457.562087073129639935',  # noqa: E501
            address=string_to_evm_address('0xdb25cA703181E7484a155DD612b06f57E12Be5F0'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=158,
            timestamp=TimestampMS(1667679923000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_YFI,
            amount=FVal('0.02192084'),
            location_label=user_address,
            notes='Deposit 0.02192084 YFI in yearn-v2 vault YFI yVault',
            counterparty=CPT_YEARN_V2,
            address=string_to_evm_address('0xdb25cA703181E7484a155DD612b06f57E12Be5F0'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=159,
            timestamp=TimestampMS(1667679923000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xdb25cA703181E7484a155DD612b06f57E12Be5F0'),
            amount=FVal('0.02164738945170483'),
            location_label=user_address,
            notes='Receive 0.02164738945170483 yvYFI after deposit in a yearn-v2 vault',
            counterparty=CPT_YEARN_V2,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x7b33b34D45A395518a4143846Ac40dA78CbcAA91']])
def test_withdraw_yearn_v2_without_logs(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xfaf3edf9fc4130e003468787d0d21cad89107bb2d648d3cd810864dd2854b76a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1667180495000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(0.000631154785993836),
            location_label=user_address,
            notes='Burn 0.000631154785993836 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1667180495000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0xB8C3B7A2A618C552C23B1E4701109a9E756Bab67'),
            amount=FVal('86.244532826510255848'),
            location_label=user_address,
            notes='Return 86.244532826510255848 yv1INCH to a yearn-v2 vault',
            counterparty=CPT_YEARN_V2,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=TimestampMS(1667180495000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:1/erc20:0x111111111117dC0aa78b770fA6A738034120C302'),
            amount=FVal('92.236538270354905336'),
            location_label=user_address,
            notes='Withdraw 92.236538270354905336 1INCH from yearn-v2 vault 1INCH yVault',
            counterparty=CPT_YEARN_V2,
            address=string_to_evm_address('0xB8C3B7A2A618C552C23B1E4701109a9E756Bab67'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x3380d0FA7355a6ACB40089Db837a740c4c1dDc85']])
def test_deposit_yearn_v1(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x521a39061231eb8fa7f96675a1e65f74b90350b4fedc0e430a2279945e162979')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1618272693000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(0.007502376),
            location_label=user_address,
            notes='Burn 0.007502376 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1618272693000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:1/erc20:0x49849C98ae39Fff122806C06791Fa73784FB3675'),
            amount=FVal('0.980572717318809472'),
            location_label=user_address,
            notes='Deposit 0.980572717318809472 crvRenWBTC in yearn-v1 vault yearn Curve.fi renBTC/wBTC',  # noqa: E501
            counterparty=CPT_YEARN_V1,
            address=string_to_evm_address('0x5334e150B938dd2b6bd040D9c4a03Cff0cED3765'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=TimestampMS(1618272693000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0x5334e150B938dd2b6bd040D9c4a03Cff0cED3765'),
            amount=FVal('0.976977709586838245'),
            location_label=user_address,
            notes='Receive 0.976977709586838245 yvcrvRenWBTC after deposit in a yearn-v1 vault',
            counterparty=CPT_YEARN_V1,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xaf7B5d7f84b7DD6b960aC6aDF2D763DD49686992']])
def test_withdraw_yearn_v1(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x6f518f5160beb181f33c813bd6bdc6ebc586f18ca4eca6e24fef6309836bedee')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1633988135000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(0.008944164419689952),
            location_label=user_address,
            notes='Burn 0.008944164419689952 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1633988135000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0x5334e150B938dd2b6bd040D9c4a03Cff0cED3765'),
            amount=FVal('0.1084'),
            location_label=user_address,
            notes='Return 0.1084 yvcrvRenWBTC to a yearn-v1 vault',
            counterparty=CPT_YEARN_V1,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=TimestampMS(1633988135000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:1/erc20:0x49849C98ae39Fff122806C06791Fa73784FB3675'),
            amount=FVal('0.109958510122911208'),
            location_label=user_address,
            notes='Withdraw 0.109958510122911208 crvRenWBTC from yearn-v1 vault yearn Curve.fi renBTC/wBTC',  # noqa: E501
            counterparty=CPT_YEARN_V1,
            address=string_to_evm_address('0x5334e150B938dd2b6bd040D9c4a03Cff0cED3765'),
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xfDb7EEc5eBF4c4aC7734748474123aC25C6eDCc8']])
def test_deposit_yearn_full_amount(ethereum_inquirer, ethereum_accounts):
    """
    In the case of deposits and withdrawals for yearn there are two different signatures for
    the functions used. If no amount is provided all the available amount is deposited/withdrawn.
    """
    tx_hash = deserialize_evm_tx_hash('0x02486ccc1fe49b3c7df60c51efad78ddca5af025834e30ba1a736ff352b33592')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1614241909000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(0.0108951),
            location_label=user_address,
            notes='Burn 0.0108951 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=224,
            timestamp=TimestampMS(1614241909000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_1INCH,
            amount=FVal('115792089237316195423570985008687907853269984665640564038972.292276463862611574'),
            location_label=user_address,
            notes='Set 1INCH spending approval of 0xfDb7EEc5eBF4c4aC7734748474123aC25C6eDCc8 by 0xB8C3B7A2A618C552C23B1E4701109a9E756Bab67 to 115792089237316195423570985008687907853269984665640564038972.292276463862611574',  # noqa: E501
            counterparty=None,
            address=string_to_evm_address('0xB8C3B7A2A618C552C23B1E4701109a9E756Bab67'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=225,
            timestamp=TimestampMS(1614241909000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_1INCH,
            amount=FVal('485.291731449267028361'),
            location_label=user_address,
            notes='Deposit 485.291731449267028361 1INCH in yearn-v2 vault 1INCH yVault',
            counterparty=CPT_YEARN_V2,
            address=string_to_evm_address('0xB8C3B7A2A618C552C23B1E4701109a9E756Bab67'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=226,
            timestamp=TimestampMS(1614241909000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xB8C3B7A2A618C552C23B1E4701109a9E756Bab67'),
            amount=FVal('484.583645343659242764'),
            location_label=user_address,
            notes='Receive 484.583645343659242764 yv1INCH after deposit in a yearn-v2 vault',
            counterparty=CPT_YEARN_V2,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xcd931775F36bf0cEDDC20ae8E256838890E49212']])
def test_withdraw_yearn_v2_many_transfers_in_tx(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test for an issue where our matching logic for a subtype of yearn v2 vault events was
    matching other transfers of either vault or underlying token that did not involve the user's
    address and as such failed to properly decode either deposit or withdrawal"""
    vault_address = string_to_evm_address('0xdA816459F1AB5631232FE5e97a05BBBb94970c95')
    get_or_create_evm_token(
        userdb=ethereum_inquirer.database,
        evm_address=vault_address,
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        symbol='yvDAI',
        name='DAI yVault',
        decimals=18,
        protocol=CPT_YEARN_V2,
        started=Timestamp(1625883889),
        underlying_tokens=[UnderlyingToken(
            address=string_to_evm_address('0x6B175474E89094C44Da98b954EedeAC495271d0F'),  # DAI
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )
    tx_hash = deserialize_evm_tx_hash('0x5e7266993a6c47164f503421b409735acd5474ef07346ce80314b1ba53ff0c9e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas, vault_amount, underlying_amount = ethereum_accounts[0], TimestampMS(1691423519000), '0.028290459798220144', '507845.778194128464278875', '540236.846296294579041898'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0xdA816459F1AB5631232FE5e97a05BBBb94970c95'),
            amount=FVal(vault_amount),
            location_label=user_address,
            notes=f'Return {vault_amount} yvDAI to a yearn-v2 vault',
            counterparty=CPT_YEARN_V2,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F'),
            amount=FVal(underlying_amount),
            location_label=user_address,
            notes=f'Withdraw {underlying_amount} DAI from yearn-v2 vault DAI yVault',
            counterparty=CPT_YEARN_V2,
            address=vault_address,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xBFF9C95D12eA2661bbC9ea2d18C4D1b3868C9Fe0']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_yearn_v3_curve_savings_deposit(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        curve_savings_vault: 'EvmToken',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x516d98ed5c091bb2f452742b1a4079f2084f525be3662b026159a1ed7a9bef66')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1741194983000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.00019683257061538')),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=285,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=(a_crvusd := Asset('eip155:1/erc20:0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E')),
        amount=(approve_amount := FVal('9999900000')),
        location_label=user_address,
        notes=f'Set crvUSD spending approval of {user_address} by {curve_savings_vault.evm_address} to {approve_amount}',  # noqa: E501
        address=curve_savings_vault.evm_address,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=286,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=a_crvusd,
        amount=(deposit_amount := FVal('27292.191642525541816366')),
        location_label=user_address,
        notes=f'Deposit {deposit_amount} crvUSD in Curve Savings',
        counterparty=CPT_CURVE,
        address=curve_savings_vault.evm_address,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=287,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=curve_savings_vault,
        amount=(receive_amount := FVal('26201.448750994790858145')),
        location_label=user_address,
        notes=f'Receive {receive_amount} scrvUSD after deposit in Curve Savings',
        counterparty=CPT_CURVE,
        address=curve_savings_vault.evm_address,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x5275817b74021E97c980E95EdE6bbAc0D0d6f3a2']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_yearn_v3_curve_savings_withdraw(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        curve_savings_vault: 'EvmToken',
):
    tx_hash = deserialize_evm_tx_hash('0x1d5db358dfdec9f554e81dedf0395b857db30fdca838c36c05cceaae00768cad')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1741204907000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000056238373116988')),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=curve_savings_vault,
        amount=(spend_amount := FVal('53747.564298310073222919')),
        location_label=user_address,
        notes=f'Return {spend_amount} scrvUSD to Curve Savings',
        counterparty=CPT_CURVE,
        address=curve_savings_vault.evm_address,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=Asset('eip155:1/erc20:0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E'),
        amount=(withdraw_amount := FVal('55985.692533876701394441')),
        location_label=user_address,
        notes=f'Withdraw {withdraw_amount} crvUSD from Curve Savings',
        counterparty=CPT_CURVE,
        address=curve_savings_vault.evm_address,
    )]
