from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset, UnderlyingToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.yearn.constants import (
    CPT_YEARN_STAKING,
    CPT_YEARN_V1,
    CPT_YEARN_V2,
    CPT_YEARN_V3,
    YEARN_PARTNER_TRACKER,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_1INCH, A_DAI, A_ETH, A_USDC, A_YFI
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.optimism import OPTIMISM_MAINNET_NODE
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
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
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


@pytest.fixture(name='yearn_yfi_eth_gauge')
def fixture_yearn_yfi_eth_gauge(database: 'DBHandler') -> 'EvmToken':
    return get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0x7Fd8Af959B54A677a1D8F92265Bd0714274C56a3'),
        chain_id=ChainID.ETHEREUM,
        symbol='yG-yvCurve-YFIETH',
        name='yGauge Curve YFI-ETH Pool yVault',
        protocol=CPT_YEARN_STAKING,
        underlying_tokens=[UnderlyingToken(
            address=get_or_create_evm_token(
                userdb=database,
                evm_address=string_to_evm_address('0x790a60024bC3aea28385b60480f15a0771f26D09'),
                chain_id=ChainID.ETHEREUM,
                symbol='yvCurve-YFIETH',
                name='Curve YFI-ETH Pool yVault',
                protocol=CPT_YEARN_V2,
            ).evm_address,
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )


@pytest.fixture(name='yearn_yvcurve_upyfi_gauge')
def fixture_yearn_yvcurve_upyfi_gauge(database: 'DBHandler') -> 'EvmToken':
    return get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0xf719B2d3925CC445D2Bb67FA12963265E224Fa11'),
        chain_id=ChainID.ETHEREUM,
        symbol='yG-yvCurve-upYFI-f',
        name='yGauge Curve upYFI Factory yVault',
        protocol=CPT_YEARN_STAKING,
        underlying_tokens=[UnderlyingToken(
            address=get_or_create_evm_token(
                userdb=database,
                evm_address=string_to_evm_address('0xFCa9Ab2996e7b010516adCC575eB63de4f4fa47A'),
                chain_id=ChainID.ETHEREUM,
                symbol='yvCurve-upYFI-f',
                name='Curve upYFI Factory yVault',
                protocol=CPT_YEARN_V2,
                underlying_tokens=[UnderlyingToken(
                    address=get_or_create_evm_token(
                        userdb=database,
                        evm_address=string_to_evm_address('0x13120b7599DdF33782c748A847cc1d3c96387Ecd'),
                        chain_id=ChainID.ETHEREUM,
                        symbol='upYFI',
                        name='YFI/upYFI',
                        protocol=CPT_YEARN_V2,
                    ).evm_address,
                    token_kind=TokenKind.ERC20,
                    weight=ONE,
                )],
            ).evm_address,
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
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1722289343000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.000357122879546472'),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=213,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E'),
            amount=FVal(approve_amount := '57896044618658097711785492504343953926634992332820282012283.792003956564819967'),  # noqa: E501
            location_label=user_address,
            notes=f'Set crvUSD spending approval of {user_address} by {vault_address} to {approve_amount}',  # noqa: E501
            address=vault_address,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=214,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:1/erc20:0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E'),
            amount=FVal(deposit_amount := '7445'),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} crvUSD in yearn-v3 vault crvUSD-2 yVault',
            counterparty=CPT_YEARN_V3,
            address=vault_address,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=215,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xBF319dDC2Edc1Eb6FDf9910E39b37Be221C8805F'),
            amount=FVal(receive_amount := '7336.974656759870797081'),
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1729145687000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.001446241576196176'),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=365,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0xef484de8C07B6e2d732A92B5F78e81B38f99f95E'),
            amount=FVal(approve_amount := '57896044618658097711785492504343953926634992332820281981187.425405284732127439'),  # noqa: E501
            location_label=user_address,
            notes=f'Set crvDOLA spending approval of {user_address} by {YEARN_PARTNER_TRACKER} to {approve_amount}',  # noqa: E501
            address=YEARN_PARTNER_TRACKER,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=366,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:1/erc20:0xef484de8C07B6e2d732A92B5F78e81B38f99f95E'),
            amount=FVal(deposit_amount := '38541.366598671832692528'),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} crvDOLA in yearn-v2 vault',
            counterparty=CPT_YEARN_V2,
            address=YEARN_PARTNER_TRACKER,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=367,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xcC2EFb8bEdB6eD69ADeE0c3762470c38D4730C50'),
            amount=FVal(receive_amount := '38514.207134567395983686'),
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
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1729346255000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.0020739662607066'),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_USDC,
            amount=FVal(deposit_amount := '10000'),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} USDC in yearn-v2 vault',
            counterparty=CPT_YEARN_V2,
            address=YEARN_PARTNER_TRACKER,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xa354F35829Ae975e850e23e9615b11Da1B3dC4DE'),
            amount=FVal(receive_amount := '9035.10865'),
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xFa4Ebcb83902Bb1106b85Bb3D4916Dfd72E06721']])
def test_yearn_staking_withdraw(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        yearn_yfi_eth_gauge: 'EvmToken',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x1420b1caf7ee2d8d59f2814d2254ac9f72eb8d2d64fdacc1a4b393184c75d841')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1760597219000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000031728668')),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=yearn_yfi_eth_gauge,
        amount=(spend_amount := FVal('3.256705603870174511')),
        location_label=user_address,
        notes=f'Return {spend_amount} yG-yvCurve-YFIETH to a Yearn Staking gauge',
        counterparty=CPT_YEARN_STAKING,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=Asset('eip155:1/erc20:0x790a60024bC3aea28385b60480f15a0771f26D09'),
        amount=spend_amount,
        location_label=user_address,
        notes=f'Withdraw {spend_amount} yvCurve-YFIETH from Yearn Staking gauge yGauge Curve YFI-ETH Pool yVault',  # noqa: E501
        counterparty=CPT_YEARN_STAKING,
        address=yearn_yfi_eth_gauge.evm_address,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=Asset('eip155:1/erc20:0x41252E8691e964f7DE35156B68493bAb6797a275'),
        amount=(reward_amount := FVal('0.622517149171265675')),
        location_label=user_address,
        notes=f'Claim {reward_amount} dYFI from Yearn Staking gauge yGauge Curve YFI-ETH Pool yVault',  # noqa: E501
        counterparty=CPT_YEARN_STAKING,
        address=yearn_yfi_eth_gauge.evm_address,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x5a90d3E6CfCC55d4D63bA4f729922413D9364c67']])
def test_yearn_staking_deposit(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        yearn_yfi_eth_gauge: 'EvmToken',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x6fc593a4ff83dfe34dcfc186ab0efabf8399e36c9654cb9ec42e2fdb6f271290')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1757604551000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000606145590629498')),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=69,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:1/erc20:0x790a60024bC3aea28385b60480f15a0771f26D09'),
        amount=ZERO,
        location_label=user_address,
        notes=f'Revoke yvCurve-YFIETH spending approval of {user_address} by {yearn_yfi_eth_gauge.evm_address}',  # noqa: E501
        address=yearn_yfi_eth_gauge.evm_address,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=70,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=Asset('eip155:1/erc20:0x790a60024bC3aea28385b60480f15a0771f26D09'),
        amount=(deposit_amount := FVal('0.027196890718070549')),
        location_label=user_address,
        notes=f'Deposit {deposit_amount} yvCurve-YFIETH in Yearn Staking gauge yGauge Curve YFI-ETH Pool yVault',  # noqa: E501
        counterparty=CPT_YEARN_STAKING,
        address=yearn_yfi_eth_gauge.evm_address,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=71,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=yearn_yfi_eth_gauge,
        amount=deposit_amount,
        location_label=user_address,
        notes=f'Receive {deposit_amount} yG-yvCurve-YFIETH after deposit in a Yearn Staking gauge',
        counterparty=CPT_YEARN_STAKING,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xFa4Ebcb83902Bb1106b85Bb3D4916Dfd72E06721']])
def test_yearn_staking_deposit_zap(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        yearn_yvcurve_upyfi_gauge: 'EvmToken',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x0d2868d59f5d0088d6e71838e2b6a76b5c0d3c4ad11a718fe5600184255dc4a1')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1753464215000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000122339162')),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=414,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:1/erc20:0x13120b7599DdF33782c748A847cc1d3c96387Ecd'),
        amount=FVal('2160000'),
        location_label=user_address,
        notes='Set upYFI spending approval of 0xFa4Ebcb83902Bb1106b85Bb3D4916Dfd72E06721 by 0x1104215963474A0FA0Ac09f4E212EF7282F2A0bC to 2160000',  # noqa: E501
        address=string_to_evm_address('0x1104215963474A0FA0Ac09f4E212EF7282F2A0bC'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=415,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=Asset('eip155:1/erc20:0x13120b7599DdF33782c748A847cc1d3c96387Ecd'),
        amount=(deposit_amount := FVal('240573.900589001185320181')),
        location_label=user_address,
        notes=f'Deposit {deposit_amount} upYFI in Yearn Staking gauge yGauge Curve upYFI Factory yVault',  # noqa: E501
        counterparty=CPT_YEARN_STAKING,
        address=string_to_evm_address('0x1104215963474A0FA0Ac09f4E212EF7282F2A0bC'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=416,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:1/erc20:0xf719B2d3925CC445D2Bb67FA12963265E224Fa11'),
        amount=(receive_amount := FVal('238918.86777749203798664')),
        location_label=user_address,
        notes=f'Receive {receive_amount} yG-yvCurve-upYFI-f after deposit in a Yearn Staking gauge',  # noqa: E501
        counterparty=CPT_YEARN_STAKING,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xa1ecA898ad4A4909c527c78B559fFDad005e761d']])
def test_yearn_v2_vault_deposit_optimism(optimism_inquirer: 'OptimismInquirer', optimism_accounts: list['ChecksumEvmAddress']) -> None:  # noqa: E501
    get_or_create_evm_token(
        userdb=optimism_inquirer.database,
        evm_address=(vault_address := string_to_evm_address('0x5B977577Eb8a480f63e11FC615D6753adB8652Ae')),  # noqa: E501
        chain_id=ChainID.OPTIMISM,
        token_kind=TokenKind.ERC20,
        symbol='yvWETH',
        name='WETH yVault',
        decimals=18,
        protocol=CPT_YEARN_V2,
        underlying_tokens=[UnderlyingToken(
            address=string_to_evm_address('0x4200000000000000000000000000000000000006'),
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=(tx_hash := deserialize_evm_tx_hash('0xdc3f8c5bc84bf3e2e57e408d6605fc441d2d5773398c902ba8d8a48f624d1e18')))  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1714123975000)),
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000007147891756595')),
        location_label=(user_address := optimism_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_ETH,
        amount=(deposit_amount := FVal('0.04')),
        location_label=user_address,
        notes=f'Deposit {deposit_amount} ETH in yearn-v2 vault {vault_address}',
        counterparty=CPT_YEARN_V2,
        address=string_to_evm_address('0xDeAFc27aC8f977E6973d671E43cBfd2573021d9e'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=452,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:10/erc20:0x5B977577Eb8a480f63e11FC615D6753adB8652Ae'),
        amount=(receive_amount := FVal('0.039243540093362109')),
        location_label=user_address,
        notes=f'Receive {receive_amount} yvWETH after deposit in a yearn-v2 vault',
        counterparty=CPT_YEARN_V2,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x158e02e4A130AFD22426bc3cCA06dD346f4f54Ea']])
def test_yearn_staking_deposit_optimism(optimism_inquirer: 'OptimismInquirer', optimism_accounts: list['ChecksumEvmAddress']) -> None:  # noqa: E501
    vault_address = get_or_create_evm_token(
        userdb=optimism_inquirer.database,
        evm_address=string_to_evm_address('0x5B977577Eb8a480f63e11FC615D6753adB8652Ae'),
        chain_id=ChainID.OPTIMISM,
        token_kind=TokenKind.ERC20,
        symbol='yvWETH',
        name='WETH yVault',
        decimals=18,
        protocol=CPT_YEARN_V2,
        underlying_tokens=[UnderlyingToken(
            address=string_to_evm_address('0x4200000000000000000000000000000000000006'),
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    ).evm_address
    gauge_address = string_to_evm_address('0xE35Fec3895Dcecc7d2a91e8ae4fF3c0d43ebfFE0')
    get_or_create_evm_token(
        userdb=optimism_inquirer.database,
        evm_address=gauge_address,
        chain_id=ChainID.OPTIMISM,
        token_kind=TokenKind.ERC20,
        symbol='yG-yvWETH',
        name='Yearn staking WETH yVault',
        protocol=CPT_YEARN_STAKING,
        underlying_tokens=[UnderlyingToken(
            address=vault_address,
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=(tx_hash := deserialize_evm_tx_hash('0xae3b94eee8fe5bdbb99787536f379bd6e8496ebaf238819f7ea30465d3e32195')))  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1717645191000)),
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.00000752535695313')),
        location_label=(user_address := optimism_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=13,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:10/erc20:0x5B977577Eb8a480f63e11FC615D6753adB8652Ae'),
        amount=ZERO,
        location_label=user_address,
        notes=f'Revoke yvWETH spending approval of {user_address} by {gauge_address}',
        address=gauge_address,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=14,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=Asset('eip155:10/erc20:0x5B977577Eb8a480f63e11FC615D6753adB8652Ae'),
        amount=(deposit_amount := FVal('0.004967732224659097')),
        location_label=user_address,
        notes=f'Deposit {deposit_amount} yvWETH in Yearn Staking gauge {gauge_address}',
        counterparty=CPT_YEARN_STAKING,
        address=gauge_address,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x14f55785385EEE92e3A1baAf71C77Eb490441981']])
@pytest.mark.parametrize('optimism_manager_connect_at_start', [(OPTIMISM_MAINNET_NODE,)])
def test_yearn_staking_withdraw_optimism(optimism_inquirer: 'OptimismInquirer', optimism_accounts: list['ChecksumEvmAddress']) -> None:  # noqa: E501
    vault_address = get_or_create_evm_token(
        userdb=optimism_inquirer.database,
        evm_address=string_to_evm_address('0x5B977577Eb8a480f63e11FC615D6753adB8652Ae'),
        chain_id=ChainID.OPTIMISM,
        token_kind=TokenKind.ERC20,
        symbol='yvWETH',
        name='WETH yVault',
        decimals=18,
        protocol=CPT_YEARN_V2,
        underlying_tokens=[UnderlyingToken(
            address=string_to_evm_address('0x4200000000000000000000000000000000000006'),
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    ).evm_address
    get_or_create_evm_token(
        userdb=optimism_inquirer.database,
        evm_address=string_to_evm_address('0x7D2382b1f8Af621229d33464340541Db362B4907'),
        chain_id=ChainID.OPTIMISM,
        token_kind=TokenKind.ERC20,
        symbol='yvOP',
        name='OP yVault',
        decimals=18,
        protocol=CPT_YEARN_V2,
        underlying_tokens=[UnderlyingToken(
            address=string_to_evm_address('0x4200000000000000000000000000000000000042'),
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )
    gauge_address = string_to_evm_address('0xE35Fec3895Dcecc7d2a91e8ae4fF3c0d43ebfFE0')
    get_or_create_evm_token(
        userdb=optimism_inquirer.database,
        evm_address=gauge_address,
        chain_id=ChainID.OPTIMISM,
        token_kind=TokenKind.ERC20,
        symbol='yG-yvWETH',
        name='Yearn staking WETH yVault',
        protocol=CPT_YEARN_STAKING,
        underlying_tokens=[UnderlyingToken(
            address=vault_address,
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )
    tx_hash = deserialize_evm_tx_hash(
        '0xd5a67db8551f49294f8cfaa11b8d5cd5ab72f344ae0e3916df37849fc6761ea2',
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1731717589000)),
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000000289621487974')),
        location_label=(user_address := optimism_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=Asset('eip155:10/erc20:0x5B977577Eb8a480f63e11FC615D6753adB8652Ae'),
        amount=(withdraw_amount := FVal('0.014877797634975937')),
        location_label=user_address,
        notes=f'Withdraw {withdraw_amount} yvWETH from Yearn Staking gauge {gauge_address}',
        counterparty=CPT_YEARN_STAKING,
        address=gauge_address,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=5,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=Asset('eip155:10/erc20:0x7D2382b1f8Af621229d33464340541Db362B4907'),
        amount=(reward_amount := FVal('0.225419331547291755')),
        location_label=user_address,
        notes=f'Claim {reward_amount} yvOP from Yearn Staking gauge {gauge_address}',
        counterparty=CPT_YEARN_STAKING,
        address=gauge_address,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x178E89A81C694259f15d350E05469f3E674eA853']])
@pytest.mark.parametrize('optimism_manager_connect_at_start', [(OPTIMISM_MAINNET_NODE,)])
def test_yearn_v2_withdraw_yvop_optimism(optimism_inquirer: 'OptimismInquirer', optimism_accounts: list['ChecksumEvmAddress']) -> None:  # noqa: E501
    get_or_create_evm_token(
        userdb=optimism_inquirer.database,
        evm_address=string_to_evm_address('0x7D2382b1f8Af621229d33464340541Db362B4907'),
        chain_id=ChainID.OPTIMISM,
        token_kind=TokenKind.ERC20,
        symbol='yvOP',
        name='OP yVault',
        decimals=18,
        protocol=CPT_YEARN_V2,
        underlying_tokens=[UnderlyingToken(
            address=string_to_evm_address('0x4200000000000000000000000000000000000042'),
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )
    tx_hash = deserialize_evm_tx_hash(
        '0x92ff46d7594279adb12eb87d1ed69c78f204927eb16912f67260a112eb133e5e',
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1729075467000)),
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000000235293360937')),
        location_label=(user_address := optimism_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=Asset('eip155:10/erc20:0x7D2382b1f8Af621229d33464340541Db362B4907'),
        amount=(return_amount := FVal('0.091636676131660261')),
        location_label=user_address,
        notes=f'Return {return_amount} yvOP to a yearn-v2 vault',
        counterparty=CPT_YEARN_V2,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=Asset('eip155:10/erc20:0x4200000000000000000000000000000000000042'),
        amount=(withdraw_amount := FVal('0.093534987466925365')),
        location_label=user_address,
        notes=f'Withdraw {withdraw_amount} OP from yearn-v2 vault 0x7D2382b1f8Af621229d33464340541Db362B4907',  # noqa: E501
        counterparty=CPT_YEARN_V2,
        address=string_to_evm_address('0x7D2382b1f8Af621229d33464340541Db362B4907'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x8D72a9BeBBd5160FBD61E57bcca7810b9F2d1d86']])
@pytest.mark.parametrize('optimism_manager_connect_at_start', [(OPTIMISM_MAINNET_NODE,)])
def test_yearn_v2_withdraw_weth_to_eth_optimism(optimism_inquirer: 'OptimismInquirer', optimism_accounts: list['ChecksumEvmAddress']) -> None:  # noqa: E501
    get_or_create_evm_token(
        userdb=optimism_inquirer.database,
        evm_address=string_to_evm_address('0x5B977577Eb8a480f63e11FC615D6753adB8652Ae'),
        chain_id=ChainID.OPTIMISM,
        token_kind=TokenKind.ERC20,
        symbol='yvWETH',
        name='WETH yVault',
        decimals=18,
        protocol=CPT_YEARN_V2,
        underlying_tokens=[UnderlyingToken(
            address=string_to_evm_address('0x4200000000000000000000000000000000000006'),
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )
    tx_hash = deserialize_evm_tx_hash(
        '0x62afbede75870d3eab885fdab63596f2a8b318b04000b3458030dfb6bae4695b',
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1720169539000)),
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000026070215176204')),
        location_label=(user_address := optimism_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=89,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:10/erc20:0x5B977577Eb8a480f63e11FC615D6753adB8652Ae'),
        amount=ZERO,
        location_label=user_address,
        notes=f'Revoke yvWETH spending approval of {user_address} by 0xDeAFc27aC8f977E6973d671E43cBfd2573021d9e',  # noqa: E501
        address=string_to_evm_address('0xDeAFc27aC8f977E6973d671E43cBfd2573021d9e'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=90,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=Asset('eip155:10/erc20:0x5B977577Eb8a480f63e11FC615D6753adB8652Ae'),
        amount=(return_amount := FVal('19.963070628915426321')),
        location_label=user_address,
        notes=f'Return {return_amount} yvWETH to a yearn-v2 vault',
        counterparty=CPT_YEARN_V2,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=91,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_ETH,
        amount=(withdraw_amount := FVal('20.265292269383422208')),
        location_label=user_address,
        notes=f'Withdraw {withdraw_amount} ETH from yearn-v2 vault 0x5B977577Eb8a480f63e11FC615D6753adB8652Ae',  # noqa: E501
        counterparty=CPT_YEARN_V2,
        address=string_to_evm_address('0x5B977577Eb8a480f63e11FC615D6753adB8652Ae'),
    )]
