import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.balancer.constants import CPT_BALANCER_V1, CPT_BALANCER_V2
from rotkehlchen.chain.ethereum.modules.balancer.v2.constants import VAULT_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_BAL, A_BPT, A_DAI, A_ETH, A_USDC, A_WETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x20A1CF262Cd3A42a50D226fD728104119e6fD0a1']])
def test_balancer_v2_swap(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x35dd639ba80940cb14d79c965002a11ea2aef17bbf1f1b85cc03c336da1ddebe')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_str = ethereum_accounts[0], TimestampMS(1669622603000), '0.001085530186197622'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_str)),
            location_label='0x20A1CF262Cd3A42a50D226fD728104119e6fD0a1',
            notes=f'Burned {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(amount=FVal(0.001)),
            location_label=user_address,
            notes='Swap 0.001 ETH in Balancer v2',
            counterparty=CPT_BALANCER_V2,
            address=VAULT_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=204,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_DAI,
            balance=Balance(amount=FVal('1.207092929058998715')),
            location_label=user_address,
            notes='Receive 1.207092929058998715 DAI as the result of a swap via Balancer v2',
            counterparty=CPT_BALANCER_V2,
            address=VAULT_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x7716a99194d758c8537F056825b75Dd0C8FDD89f']])
def test_balancer_v1_join(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xb9dff9df4e3838c75d354d62c4596d94e5eb8904e07cee07a3b7ffa611c05544')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_str = ethereum_accounts[0], TimestampMS(1597144247000), '0.0141724'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_str)),
            location_label=user_address,
            notes=f'Burned {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_BPT,
            balance=Balance(amount=FVal('0.042569019597126949')),
            location_label=user_address,
            notes='Receive 0.042569019597126949 BPT from a Balancer v1 pool',
            counterparty=CPT_BALANCER_V1,
            address=string_to_evm_address('0x13830EB6444768cCea2C9d41308195Ceb18eF772'),
            extra_data={'deposit_events_num': 1},
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_WETH,
            balance=Balance(amount=FVal(0.05)),
            location_label=user_address,
            notes='Deposit 0.05 WETH to a Balancer v1 pool',
            counterparty=CPT_BALANCER_V1,
            address=string_to_evm_address('0x13830EB6444768cCea2C9d41308195Ceb18eF772'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x7716a99194d758c8537F056825b75Dd0C8FDD89f']])
def test_balancer_v1_exit(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xfa1dfeb83480e51a15137a93cb0eba9ac92c1b6b0ee0bd8551a422c1ed83695b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_str = ethereum_accounts[0], TimestampMS(1597243001000), '0.03071222'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_str)),
            location_label=user_address,
            notes=f'Burned {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_BPT,
            balance=Balance(amount=FVal('0.042569019597126949')),
            location_label=user_address,
            notes='Return 0.042569019597126949 BPT to a Balancer v1 pool',
            counterparty=CPT_BALANCER_V1,
            address=string_to_evm_address('0x59A19D8c652FA0284f44113D0ff9aBa70bd46fB4'),
            identifier=None,
            extra_data={'withdrawal_events_num': 2},
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_BAL,
            balance=Balance(amount=FVal('0.744372160905819159')),
            location_label=user_address,
            notes='Receive 0.744372160905819159 BAL after removing liquidity from a Balancer v1 pool',  # noqa: E501
            counterparty=CPT_BALANCER_V1,
            address=string_to_evm_address('0x59A19D8c652FA0284f44113D0ff9aBa70bd46fB4'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_WETH,
            balance=Balance(amount=FVal('0.010687148200906598')),
            location_label=user_address,
            notes='Receive 0.010687148200906598 WETH after removing liquidity from a Balancer v1 pool',  # noqa: E501
            counterparty=CPT_BALANCER_V1,
            address=string_to_evm_address('0x59A19D8c652FA0284f44113D0ff9aBa70bd46fB4'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x549C0421c69Be943A2A60e76B19b4A801682cBD3']])
def test_deposit_with_excess_tokens(ethereum_inquirer, ethereum_accounts):
    """Verify that when a refund is made for a deposit in balancer v1 this is properly decoded"""
    tx_hash = deserialize_evm_tx_hash('0x22162f5c71261421db82a03ba4ad13725ef4fe9639c62bf6702538f980fbe7ba')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp = ethereum_accounts[0], TimestampMS(1593186380000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.01452447')),
            location_label=user_address,
            notes='Burned 0.01452447 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=132,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0xe2f2a5C287993345a840Db3B0845fbC70f5935a5'),
            balance=Balance(amount=FVal('115792089237316195423570985008687907853269984665640563907878.636639492077148372')),
            location_label=user_address,
            notes='Set mUSD spending approval of 0x549C0421c69Be943A2A60e76B19b4A801682cBD3 by 0x9ED47950144e51925166192Bf0aE95553939030a to 115792089237316195423570985008687907853269984665640563907878.636639492077148372',  # noqa: E501
            address=string_to_evm_address('0x9ED47950144e51925166192Bf0aE95553939030a'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=133,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0x72Cd8f4504941Bf8c5a21d1Fd83A96499FD71d2C'),
            balance=Balance(amount=FVal('1675.495956074927519908')),
            location_label=user_address,
            notes='Receive 1675.495956074927519908 BPT from a Balancer v1 pool',
            counterparty=CPT_BALANCER_V1,
            extra_data={'deposit_events_num': 4},
            address=string_to_evm_address('0x9ED47950144e51925166192Bf0aE95553939030a'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=134,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:1/erc20:0xe2f2a5C287993345a840Db3B0845fbC70f5935a5'),
            balance=Balance(amount=FVal('131578.947368421052491563')),
            location_label=user_address,
            notes='Deposit 131578.947368421052491563 mUSD to a Balancer v1 pool',
            counterparty=CPT_BALANCER_V1,
            address=string_to_evm_address('0x9ED47950144e51925166192Bf0aE95553939030a'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=135,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_USDC,
            balance=Balance(amount=FVal('131421.703252')),
            location_label=user_address,
            notes='Deposit 131421.703252 USDC to a Balancer v1 pool',
            counterparty=CPT_BALANCER_V1,
            address=string_to_evm_address('0x9ED47950144e51925166192Bf0aE95553939030a'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=136,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REFUND,
            asset=Asset('eip155:1/erc20:0xe2f2a5C287993345a840Db3B0845fbC70f5935a5'),
            balance=Balance(amount=FVal('6578.947368421052624578')),
            location_label=user_address,
            notes='Refunded 6578.947368421052624578 mUSD after depositing in Balancer V1 pool',
            counterparty=CPT_BALANCER_V1,
            address=string_to_evm_address('0x9ED47950144e51925166192Bf0aE95553939030a'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=137,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REFUND,
            asset=A_USDC,
            balance=Balance(amount=FVal('6571.085163')),
            location_label=user_address,
            notes='Refunded 6571.085163 USDC after depositing in Balancer V1 pool',
            counterparty=CPT_BALANCER_V1,
            address=string_to_evm_address('0x9ED47950144e51925166192Bf0aE95553939030a'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xAB12253171A0d73df64B115cD43Fe0A32Feb9dAA']])
def test_balancer_trade(ethereum_inquirer, ethereum_accounts):
    """Test a balancer trade of token to token"""
    tx_hash = deserialize_evm_tx_hash('0xc9e8094d4435c3786bbb28b64546ecdf8a1f384057319e715eab7f28cfb01e4f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_str = ethereum_accounts[0], TimestampMS(1643362575000), '0.01196446449981698'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_str)),
            location_label=user_address,
            notes=f'Burned {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=56,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDC,
            balance=Balance(amount=FVal(1000)),
            location_label=user_address,
            notes='Swap 1000 USDC via Balancer v2',
            counterparty=CPT_BALANCER_V2,
            address=VAULT_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=57,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0x3E828ac5C480069D4765654Fb4b8733b910b13b2'),
            balance=Balance(amount=FVal('1881.157063057509114271')),
            location_label=user_address,
            notes='Receive 1881.157063057509114271 CLNY as the result of a swap via Balancer v2',
            counterparty=CPT_BALANCER_V2,
            address=VAULT_ADDRESS,
        ),
    ]
