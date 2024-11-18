import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset, UnderlyingToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.balancer.constants import CPT_BALANCER_V1, CPT_BALANCER_V2
from rotkehlchen.chain.evm.decoding.balancer.v2.constants import VAULT_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_BAL, A_DAI, A_ETH, A_USDC, A_WETH, A_XDAI
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChainID, EvmTokenKind, Location, TimestampMS, deserialize_evm_tx_hash

A_BPT = Asset('eip155:1/erc20:0x59A19D8c652FA0284f44113D0ff9aBa70bd46fB4')


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
            notes=f'Burn {gas_str} ETH for gas',
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
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
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
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
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
            notes=f'Burn {gas_str} ETH for gas',
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
            notes='Burn 0.01452447 ETH for gas',
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
            sequence_index=134,
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
            sequence_index=135,
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
            sequence_index=136,
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
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=137,
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
            notes=f'Burn {gas_str} ETH for gas',
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


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xF01adF04216C35448456fdaA6BBFff4055527Dd1']])
def test_balancer_v1_non_proxy_join(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xbba2e9e46c773b91b1528e48af1ed479132353473726d75e7a0f74bfb687613e')  # noqa: E501
    balancer_qqq_weth_pool_token = get_or_create_evm_token(
        userdb=ethereum_inquirer.database,
        evm_address=string_to_evm_address('0x0ce69A796aBe0c0451585aA88F6F45ebaC9E12dc'),
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        symbol='BCoW-80QQQ-20WETH',
        name='Balancer CoW AMM 80 QQQ 20 WETH',
        decimals=18,
        protocol=CPT_BALANCER_V1,
        underlying_tokens=[
            UnderlyingToken(  # including just one of two underlying token.
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                token_kind=EvmTokenKind.ERC20,
                weight=FVal('0.2'),
            ),
        ],
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_str, approve_amt, receive_amt, deposit_qqq_amt, deposit_weth_amt = ethereum_accounts[0], TimestampMS(1730837051000), '0.002106711205202376', '0.000000001', '4152.559258169060848717', '3545739.463723403', '0.726672467956343618'  # noqa: E501
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
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=164,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0x690031313d70c2545357F4487C6a3F134C434507'),
            balance=Balance(amount=FVal(approve_amt)),
            location_label=user_address,
            notes=f'Set QQQ spending approval of {user_address} by {balancer_qqq_weth_pool_token.evm_address} to {approve_amt}',  # noqa: E501
            address=balancer_qqq_weth_pool_token.evm_address,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=165,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:1/erc20:0x690031313d70c2545357F4487C6a3F134C434507'),
            balance=Balance(amount=FVal(deposit_qqq_amt)),
            location_label=user_address,
            notes=f'Deposit {deposit_qqq_amt} QQQ to a Balancer v1 pool',
            counterparty=CPT_BALANCER_V1,
            address=balancer_qqq_weth_pool_token.evm_address,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=166,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_WETH,
            balance=Balance(amount=FVal(deposit_weth_amt)),
            location_label=user_address,
            notes=f'Deposit {deposit_weth_amt} WETH to a Balancer v1 pool',
            counterparty=CPT_BALANCER_V1,
            address=balancer_qqq_weth_pool_token.evm_address,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=167,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=balancer_qqq_weth_pool_token,
            balance=Balance(amount=FVal(receive_amt)),
            location_label=user_address,
            counterparty=CPT_BALANCER_V1,
            notes=f'Receive {receive_amt} BCoW-80QQQ-20WETH from a Balancer v1 pool',
            address=balancer_qqq_weth_pool_token.evm_address,
            extra_data={'deposit_events_num': 2},
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x6D3B90747dbf5883bF88fF7Eb5fCC86f408b5409']])
def test_balancer_v1_non_proxy_exit(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2a1b671429d1a2c797ba0b46735f029e69a85ba514a4d1132eab6b22c7052540')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, pool_address, timestamp, gas_str, return_amt, withdrawn_sfrx_eth_amt, withdrawn_fxs_amt = ethereum_accounts[0], string_to_evm_address('0x11F2A400de0a2FC93a32F88D8779d8199152c6a4'), TimestampMS(1730953079000), '0.001983415737154446', '224630.905650719593790621', '11.361467105948316099', '18310.050732769125107569'  # noqa: E501
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
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0x11F2A400de0a2FC93a32F88D8779d8199152c6a4'),
            balance=Balance(amount=FVal(return_amt)),
            location_label=user_address,
            counterparty=CPT_BALANCER_V1,
            notes=f'Return {return_amt} BCoW-50sfrxETH-50FXS to a Balancer v1 pool',
            address=pool_address,
            extra_data={'withdrawal_events_num': 2},
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:1/erc20:0xac3E018457B222d93114458476f3E3416Abbe38F'),
            balance=Balance(amount=FVal(withdrawn_sfrx_eth_amt)),
            location_label=user_address,
            notes=f'Receive {withdrawn_sfrx_eth_amt} sfrxETH after removing liquidity from a Balancer v1 pool',  # noqa: E501
            counterparty=CPT_BALANCER_V1,
            address=pool_address,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:1/erc20:0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0'),
            balance=Balance(amount=FVal(withdrawn_fxs_amt)),
            location_label=user_address,
            notes=f'Receive {withdrawn_fxs_amt} FXS after removing liquidity from a Balancer v1 pool',  # noqa: E501
            counterparty=CPT_BALANCER_V1,
            address=pool_address,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xE3B73F6f37F782128Ebe11e058B23BA0bA6c03C3']])
def test_balancer_v1_exit_arbitrum(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0xf674623c5877257dbb9e8d328ff56e5dfda4f5a650ea51be3100261a1f8aae65')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, pool_address, timestamp, gas_str, return_amt, withdrawn_usdc_amt, withdrawn_wsteth_amt = arbitrum_one_accounts[0], string_to_evm_address('0xFEa755D5523F3A78c0945141AD396d4E970D2fab'), TimestampMS(1728651192000), '0.00000317535', '1.822676898893300983', '11.664549', '0.004234826018688223'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_str)),
            location_label=user_address,
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:42161/erc20:0xFEa755D5523F3A78c0945141AD396d4E970D2fab'),
            balance=Balance(amount=FVal(return_amt)),
            location_label=user_address,
            counterparty=CPT_BALANCER_V1,
            notes=f'Return {return_amt} BCoW-50USDC-50wstETH to a Balancer v1 pool',
            address=pool_address,
            extra_data={'withdrawal_events_num': 2},
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831'),
            balance=Balance(amount=FVal(withdrawn_usdc_amt)),
            location_label=user_address,
            notes=f'Receive {withdrawn_usdc_amt} USDC after removing liquidity from a Balancer v1 pool',  # noqa: E501
            counterparty=CPT_BALANCER_V1,
            address=pool_address,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:42161/erc20:0x5979D7b546E38E414F7E9822514be443A4800529'),
            balance=Balance(amount=FVal(withdrawn_wsteth_amt)),
            location_label=user_address,
            notes=f'Receive {withdrawn_wsteth_amt} wstETH after removing liquidity from a Balancer v1 pool',  # noqa: E501
            counterparty=CPT_BALANCER_V1,
            address=pool_address,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x87A04752E516548B0d5d4DF97384C0b22B649179']])
def test_balancer_v1_join_gnosis(gnosis_inquirer, gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0xa6ac19c551667fe71ea66de2c1d28b6b048673b28baf6d4dd1ed7cd8bae96406')  # noqa: E501
    balancer_gno_cow_pool_token = get_or_create_evm_token(
        userdb=gnosis_inquirer.database,
        evm_address=string_to_evm_address('0x71663f74490673706D7b8860B7D02b7c76160bAe'),
        chain_id=ChainID.GNOSIS,
        token_kind=EvmTokenKind.ERC20,
        symbol='BCoW-50GNO-50COW',
        name='BCoW AMM 50GNO-50COW',
        decimals=18,
        protocol=CPT_BALANCER_V1,
        underlying_tokens=[
            UnderlyingToken(
                address=string_to_evm_address('0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb'),
                token_kind=EvmTokenKind.ERC20,
                weight=FVal('0.5'),
            ),
            UnderlyingToken(
                address=string_to_evm_address('0x177127622c4A00F3d409B75571e12cB3c8973d3c'),
                token_kind=EvmTokenKind.ERC20,
                weight=FVal('0.5'),
            ),
        ],
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_str, receive_amt, deposit_gno_amt, deposit_cow_amt = gnosis_accounts[0], TimestampMS(1731355510000), '0.0002310674', '68.63749617341156454', '0.048302073768085864', '30.933559190570998685'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            balance=Balance(amount=FVal(gas_str)),
            location_label=user_address,
            notes=f'Burn {gas_str} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:100/erc20:0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb'),
            balance=Balance(amount=FVal(deposit_gno_amt)),
            location_label=user_address,
            notes=f'Deposit {deposit_gno_amt} GNO to a Balancer v1 pool',
            counterparty=CPT_BALANCER_V1,
            address=balancer_gno_cow_pool_token.evm_address,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:100/erc20:0x177127622c4A00F3d409B75571e12cB3c8973d3c'),
            balance=Balance(amount=FVal(deposit_cow_amt)),
            location_label=user_address,
            notes=f'Deposit {deposit_cow_amt} COW to a Balancer v1 pool',
            counterparty=CPT_BALANCER_V1,
            address=balancer_gno_cow_pool_token.evm_address,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:100/erc20:0x71663f74490673706D7b8860B7D02b7c76160bAe'),
            balance=Balance(amount=FVal(receive_amt)),
            location_label=user_address,
            counterparty=CPT_BALANCER_V1,
            notes=f'Receive {receive_amt} BCoW-50GNO-50COW from a Balancer v1 pool',
            address=balancer_gno_cow_pool_token.evm_address,
            extra_data={'deposit_events_num': 2},
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x2E1336f7710B89153aFE979cD14644AfcFb32212']])
def test_balancer_v2_exit_ethereum(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xcc1636487bd419892133c0e1245e2f427819193fbaef68270111580291c0b285')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_str, return_amt, withdrawn_rsweth_amt = ethereum_accounts[0], TimestampMS(1731642119000), '0.003934656379000305', '14.957821596922618203', '14.953427656474271108'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(FVal(gas_str)),
            location_label=user_address,
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0x848a5564158d84b8A8fb68ab5D004Fae11619A54'),
            balance=Balance(FVal(return_amt)),
            location_label=user_address,
            counterparty=CPT_BALANCER_V2,
            notes=f'Return {return_amt} weETH/ezETH/rswETH to a Balancer v2 pool',
            address=ZERO_ADDRESS,
            extra_data={'withdrawal_events_num': 1},
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:1/erc20:0xFAe103DC9cf190eD75350761e95403b7b8aFa6c0'),
            balance=Balance(FVal(withdrawn_rsweth_amt)),
            location_label=user_address,
            notes=f'Receive {withdrawn_rsweth_amt} rswETH after removing liquidity from a Balancer v2 pool',  # noqa: E501
            counterparty=CPT_BALANCER_V2,
            address=VAULT_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x63A49B0cA8B5B907dd083ada6D9F6853522Bb975']])
def test_balancer_v2_exit_gnosis(gnosis_inquirer, gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0x1a9e201fcec608a49dd6b106c46818f2f898401f6439dc5e619869ad48167a3a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_str, return_amt, withdrawn_sdai_amt = gnosis_accounts[0], TimestampMS(1731923340000), '0.0003807456', '2403.555042425564723735', '2215.645258238073851336'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            balance=Balance(FVal(gas_str)),
            location_label=user_address,
            notes=f'Burn {gas_str} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:100/erc20:0xc9F00C3a713008DDf69b768d90d4978549bFDF94'),
            balance=Balance(FVal(return_amt)),
            location_label=user_address,
            counterparty=CPT_BALANCER_V2,
            notes=f'Return {return_amt} crvUSD/sDAI to a Balancer v2 pool',
            address=ZERO_ADDRESS,
            extra_data={'withdrawal_events_num': 1},
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:100/erc20:0xaf204776c7245bF4147c2612BF6e5972Ee483701'),
            balance=Balance(FVal(withdrawn_sdai_amt)),
            location_label=user_address,
            notes=f'Receive {withdrawn_sdai_amt} sDAI after removing liquidity from a Balancer v2 pool',  # noqa: E501
            counterparty=CPT_BALANCER_V2,
            address=VAULT_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x63A49B0cA8B5B907dd083ada6D9F6853522Bb975']])
def test_balancer_v2_join_gnosis(gnosis_inquirer, gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0x1915189b0ad23d6c8e6f23df298e92504ec7537dfa8d52571c60193bc598a8b8')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_str, receive_amt, deposit_sdai_amt = gnosis_accounts[0], TimestampMS(1729441770000), '0.0003671558', '2403.555042425564723735', '2229.291979360811376949'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            balance=Balance(FVal(gas_str)),
            location_label=user_address,
            notes=f'Burn {gas_str} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:100/erc20:0xaf204776c7245bF4147c2612BF6e5972Ee483701'),
            balance=Balance(FVal(deposit_sdai_amt)),
            location_label=user_address,
            notes=f'Deposit {deposit_sdai_amt} sDAI to a Balancer v2 pool',
            counterparty=CPT_BALANCER_V2,
            address=VAULT_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:100/erc20:0xc9F00C3a713008DDf69b768d90d4978549bFDF94'),
            balance=Balance(FVal(receive_amt)),
            location_label=user_address,
            counterparty=CPT_BALANCER_V2,
            notes=f'Receive {receive_amt} crvUSD/sDAI from a Balancer v2 pool',
            address=ZERO_ADDRESS,
            extra_data={'deposit_events_num': 1},
        ),
    ]
    assert events == expected_events
