import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.optimism_bridge.decoder import (
    OPTIMISM_L1_ESCROW,
    OPTIMISM_PORTAL_ADDRESS,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.constants import CPT_OPTIMISM
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_OPTIMISM_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x4bBa290826C253BD854121346c370a9886d1bC26']])
def test_deposit_erc20(ethereum_inquirer, ethereum_accounts):
    """Data is taken from
    https://etherscan.io/tx/0x0297cc824348e477007dfea9b8a1e6a1ff9ddce3c4b35f170b4429bee5a8a00b
    """
    evmhash = deserialize_evm_tx_hash('0x0297cc824348e477007dfea9b8a1e6a1ff9ddce3c4b35f170b4429bee5a8a00b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1674055295000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('0.00465973024452012')),
            location_label=user_address,
            notes='Burned 0.00465973024452012 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=202,
            timestamp=TimestampMS(1674055295000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            balance=Balance(amount=FVal('10')),
            location_label=user_address,
            notes='Bridge 10 USDC from Ethereum to Optimism via Optimism bridge',
            counterparty=CPT_OPTIMISM,
            address=string_to_evm_address('0x99C9fc46f92E8a1c0deC1b1747d010903E884bE1'),
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x18C22c88146B24a2c96E65c82666d976A4ba5a94']])
def test_deposit_eth(ethereum_inquirer, ethereum_accounts):
    """Data is taken from
    https://etherscan.io/tx/0x4ccfa0fa8bf0a75030357c1ea0aa9040df4167785523e557beb640c00e039fb6
    """
    evmhash = deserialize_evm_tx_hash('0x4ccfa0fa8bf0a75030357c1ea0aa9040df4167785523e557beb640c00e039fb6')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1674057215000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.006541751818933373')),
            location_label=user_address,
            notes='Burned 0.006541751818933373 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1674057215000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.1')),
            location_label=user_address,
            notes='Bridge 0.1 ETH from Ethereum to Optimism via Optimism bridge',
            counterparty=CPT_OPTIMISM,
            address=string_to_evm_address('0x99C9fc46f92E8a1c0deC1b1747d010903E884bE1'),
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0x4bBa290826C253BD854121346c370a9886d1bC26']])
def test_receive_erc20_on_optimism_legacy(optimism_inquirer, optimism_accounts):
    """Legacy bridge deposit to optimism. Where l1fee exists in receipt data"""
    evmhash = deserialize_evm_tx_hash('0x1d47c8026bfc63ed0af553bd240430978cb43efba00864d597a747c90464074f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=evmhash)
    user_address = optimism_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1674055897000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
            balance=Balance(amount=FVal('10')),
            location_label=user_address,
            notes='Bridge 10 USDC.e from Ethereum to Optimism via Optimism bridge',
            counterparty=CPT_OPTIMISM,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_receive_erc20_on_optimism(optimism_inquirer, optimism_accounts):
    """Newer bridge deposit to optimism. Where l1fee is 0 and missing from receipt data"""
    evmhash = deserialize_evm_tx_hash('0x0c0515e562917f86c8895765058df1d3df5aaf98aff00813c6f7d22c62a9b7d4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=evmhash)
    user_address = optimism_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1691959569000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
            balance=Balance(amount=FVal('10000')),
            location_label=user_address,
            notes='Bridge 10000 USDC.e from Ethereum to Optimism via Optimism bridge',
            counterparty=CPT_OPTIMISM,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0xfc399B17D1Ddf01a518DcaeE557ef776bf288f63']])
def test_receive_eth_on_optimism(optimism_inquirer, optimism_accounts):
    """Data is taken from
    https://optimistic.etherscan.io/tx/0x6a93d5aaa075c9c044d2591370cd5b9e83259370ddd618267c4757715da000c2
    """
    evmhash = deserialize_evm_tx_hash('0x6a93d5aaa075c9c044d2591370cd5b9e83259370ddd618267c4757715da000c2')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=evmhash)
    user_address = optimism_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1674120410000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_OPTIMISM_ETH,
            balance=Balance(amount=FVal('0.009')),
            location_label=user_address,
            notes='Bridge 0.009 ETH from Ethereum to Optimism via Optimism bridge',
            counterparty=CPT_OPTIMISM,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0x261FD12AF4c4bAbb30F44c1B0FE20a718A39b04C']])
def test_withdraw_erc20(optimism_inquirer, optimism_accounts):
    """Data is taken from
    https://optimistic.etherscan.io/tx/0x5798c5d91658e6a3722f8507ca25ac9b21d7df555d364f5cd1f5578c92329412
    """
    evmhash = deserialize_evm_tx_hash('0x5798c5d91658e6a3722f8507ca25ac9b21d7df555d364f5cd1f5578c92329412')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=evmhash)
    user_address = optimism_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1673522839000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.000063967090470944')),
            location_label=user_address,
            notes='Burned 0.000063967090470944 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1673522839000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
            balance=Balance(amount=FVal('2718.857536')),
            location_label=user_address,
            notes='Bridge 2718.857536 USDC.e from Optimism to Ethereum via Optimism bridge',
            counterparty=CPT_OPTIMISM,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0xE232E72983E329757F02292322296f5B96dAfC8F']])
def test_withdraw_eth(optimism_inquirer, optimism_accounts):
    """Data is taken from
    https://optimistic.etherscan.io/tx/0xe2111cddcd42c8214770c7a3270490c31663cd8b4b20b3fc27018ca3ce7a3979
    """
    evmhash = deserialize_evm_tx_hash('0xe2111cddcd42c8214770c7a3270490c31663cd8b4b20b3fc27018ca3ce7a3979')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=evmhash)
    user_address = optimism_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1673253269000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.000062680826296456')),
            location_label=user_address,
            notes='Burned 0.000062680826296456 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1673253269000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:10/erc20:0xDeadDeAddeAddEAddeadDEaDDEAdDeaDDeAD0000'),
            balance=Balance(amount=FVal('0.435796826762301485')),
            location_label=user_address,
            notes='Bridge 0.435796826762301485 ETH from Optimism to Ethereum via Optimism bridge',
            counterparty=CPT_OPTIMISM,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x261FD12AF4c4bAbb30F44c1B0FE20a718A39b04C']])
def test_claim_erc20_on_ethereum(ethereum_inquirer, ethereum_accounts):
    """Data is taken from
    https://etherscan.io/tx/0xa577a47e439cc95d3f2b90f7c10a305c0c648c8f8b8a055872e622f341ab969e
    """
    evmhash = deserialize_evm_tx_hash('0xa577a47e439cc95d3f2b90f7c10a305c0c648c8f8b8a055872e622f341ab969e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1674128075000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.01405791999714114')),
            location_label=user_address,
            notes='Burned 0.01405791999714114 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=121,
            timestamp=TimestampMS(1674128075000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            balance=Balance(amount=FVal('2718.857536')),
            location_label=user_address,
            notes='Bridge 2718.857536 USDC from Optimism to Ethereum via Optimism bridge',
            counterparty=CPT_OPTIMISM,
            address=string_to_evm_address('0x99C9fc46f92E8a1c0deC1b1747d010903E884bE1'),
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xE232E72983E329757F02292322296f5B96dAfC8F']])
def test_claim_eth_on_ethereum(ethereum_inquirer, ethereum_accounts):
    """Data is taken from
    https://etherscan.io/tx/0x785df1d7f2cb08ba956792393a2d947f1c18b39bd924e238811e4a14da10b0c4
    """
    evmhash = deserialize_evm_tx_hash('0x785df1d7f2cb08ba956792393a2d947f1c18b39bd924e238811e4a14da10b0c4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1674127139000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.012214330132870492')),
            location_label=user_address,
            notes='Burned 0.012214330132870492 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1674127139000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.435796826762301485')),
            location_label=user_address,
            notes='Bridge 0.435796826762301485 ETH from Optimism to Ethereum via Optimism bridge',
            counterparty=CPT_OPTIMISM,
            address=string_to_evm_address('0x99C9fc46f92E8a1c0deC1b1747d010903E884bE1'),
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xC02ad7b9a9121fc849196E844DC869D2250DF3A6']])
def test_prove_withdrawal(ethereum_inquirer, ethereum_accounts):
    """Test that withdrawal proving of the 2-step withdrawal is recognized properly
    https://blog.oplabs.co/two-step-withdrawals/
    """
    evmhash = deserialize_evm_tx_hash('0xc68e09838d421ea4cdde39a30917579943a29d74e3d93266b52ee8ebdc841f78')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash)
    timestamp = TimestampMS(1694198291000)
    user_address = ethereum_accounts[0]
    gas_str = '0.015525942536120381'
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
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
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=user_address,
            notes='Prove optimism bridge withdrawal 0xa030ef121ef8a49271b3201cc277c919063e740cc2fefe9b50d2f7327359710b',  # noqa: E501
            counterparty=CPT_OPTIMISM,
            address=OPTIMISM_PORTAL_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x74eEFF1A4D24C9Cd48FF9D8Dabd9Db0120b9Caf6']])
def test_deposit_dai_on_ethereum(ethereum_inquirer, ethereum_accounts):
    evmhash = deserialize_evm_tx_hash('0xad659c207e54b3fdb2124e38b8cfa673851c49feb97115f45ba396f80a4fd35b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash)
    user_address, timestamp, gas_amount, deposit_amount = ethereum_accounts[0], TimestampMS(1723807967000), '0.0006873796276356', '97.27'  # noqa: E501
    assert events == [
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
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=227,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_DAI,
            balance=Balance(amount=FVal(deposit_amount)),
            location_label=user_address,
            notes=f'Bridge {deposit_amount} DAI from Ethereum to Optimism via Optimism bridge',
            counterparty=CPT_OPTIMISM,
            address=OPTIMISM_L1_ESCROW,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_deposit_dai_on_optimism(optimism_inquirer, optimism_accounts):
    evmhash = deserialize_evm_tx_hash('0xd566bc86bdc88cf811fee5bbf5f233cb8add71642fdf547866f4054c4362a922')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=evmhash)
    user_address, timestamp, gas_amount, deposit_amount = optimism_accounts[0], TimestampMS(1670442294000), '0.000073960153367596', '106317.949168317256453804'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_amount)),
            location_label=user_address,
            notes=f'Burned {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:10/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1'),
            balance=Balance(amount=FVal(deposit_amount)),
            location_label=user_address,
            notes=f'Bridge {deposit_amount} DAI from Optimism to Ethereum via Optimism bridge',
            counterparty=CPT_OPTIMISM,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_withdraw_dai_on_ethereum(ethereum_inquirer, ethereum_accounts):
    evmhash = deserialize_evm_tx_hash('0x3e958996b7c4b2466ca9521d4c688ff4817c28d66bb3f52ec1174c6d0f1c44db')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash)
    user_address, timestamp, gas_amount, receive_amount = ethereum_accounts[0], TimestampMS(1671053711000), '0.0097257501', '106317.949168317256453804'  # noqa: E501
    assert events == [
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
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=876,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_DAI,
            balance=Balance(amount=FVal(receive_amount)),
            location_label=user_address,
            notes=f'Bridge {receive_amount} DAI from Optimism to Ethereum via Optimism bridge',
            counterparty=CPT_OPTIMISM,
            address=OPTIMISM_L1_ESCROW,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x301605C95acbED7A1fD9C2c0DeEe964e2AFBd0C3']])
def test_withdraw_dai_on_optimism(optimism_inquirer, optimism_accounts):
    evmhash = deserialize_evm_tx_hash('0x785d75b9a5c93b2ad47b662f8f98f9c63d31cd629497bcbd846c57a70f76366e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=evmhash)
    user_address, timestamp, deposit_amount = optimism_accounts[0], TimestampMS(1724102399000), '309.321'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:10/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1'),
            balance=Balance(amount=FVal(deposit_amount)),
            location_label=user_address,
            notes=f'Bridge {deposit_amount} DAI from Ethereum to Optimism via Optimism bridge',
            counterparty=CPT_OPTIMISM,
            address=ZERO_ADDRESS,
        ),
    ]
