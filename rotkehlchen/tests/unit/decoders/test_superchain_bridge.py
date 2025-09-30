import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.base.constants import CPT_BASE
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.superchain_bridge.op.decoder import OPTIMISM_PORTAL_ADDRESS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.constants import CPT_OPTIMISM
from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
from rotkehlchen.constants.assets import A_ETH, A_OPTIMISM_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChecksumEvmAddress, Location, TimestampMS, deserialize_evm_tx_hash


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
            amount=FVal('0.00465973024452012'),
            location_label=user_address,
            notes='Burn 0.00465973024452012 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=202,
            timestamp=TimestampMS(1674055295000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            amount=FVal('10'),
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
            amount=FVal('0.006541751818933373'),
            location_label=user_address,
            notes='Burn 0.006541751818933373 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1674057215000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal('0.1'),
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
            amount=FVal('10'),
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
            amount=FVal('10000'),
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
            amount=FVal('0.009'),
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
            amount=FVal('0.000063967090470944'),
            location_label=user_address,
            notes='Burn 0.000063967090470944 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1673522839000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
            amount=FVal('2718.857536'),
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
            amount=FVal('0.000062680826296456'),
            location_label=user_address,
            notes='Burn 0.000062680826296456 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1673253269000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:10/erc20:0xDeadDeAddeAddEAddeadDEaDDEAdDeaDDeAD0000'),
            amount=FVal('0.435796826762301485'),
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
            amount=FVal('0.01405791999714114'),
            location_label=user_address,
            notes='Burn 0.01405791999714114 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=121,
            timestamp=TimestampMS(1674128075000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            amount=FVal('2718.857536'),
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
            amount=FVal('0.012214330132870492'),
            location_label=user_address,
            notes='Burn 0.012214330132870492 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1674127139000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal('0.435796826762301485'),
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
            amount=FVal(gas_str),
            location_label=user_address,
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=276,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Prove optimism bridge withdrawal 0xa030ef121ef8a49271b3201cc277c919063e740cc2fefe9b50d2f7327359710b',  # noqa: E501
            counterparty=CPT_OPTIMISM,
            address=OPTIMISM_PORTAL_ADDRESS,
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
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:10/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1'),
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Bridge {deposit_amount} DAI from Optimism to Ethereum via Optimism bridge',
            counterparty=CPT_OPTIMISM,
            address=ZERO_ADDRESS,
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
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Bridge {deposit_amount} DAI from Ethereum to Optimism via Optimism bridge',
            counterparty=CPT_OPTIMISM,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x6D376A5863324489BD65AB2cc8E24d6cE3775848']])
def test_deposit_eth_ethereum_to_base_bridge(ethereum_inquirer, ethereum_accounts):
    evmhash = deserialize_evm_tx_hash('0xe5e26e70a257ca733042d8cbbc4764737d115016892e440ad6cea43933a655d7')  # noqa: E501
    (events, _), user_address, timestamp, deposit_amount = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash), ethereum_accounts[0], TimestampMS(1730128127000), '2'  # noqa: E501
    expected_events = [EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.001994757244065416'),
            location_label=user_address,
            notes='Burn 0.001994757244065416 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Bridge {deposit_amount} ETH from Ethereum to Base via Base bridge',
            counterparty=CPT_BASE,
            address=string_to_evm_address('0x3154Cf16ccdb4C6d922629664174b904d80F2C35'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x150f4a772a640BeD3a33E5919D1E3f4fc8dE2cd0']])
def test_deposit_erc20_ethereum_to_base_bridge(ethereum_inquirer, ethereum_accounts):
    evmhash = deserialize_evm_tx_hash('0x58160ce93b20fa0ec513dd956325ef8e11f9478af21573bb3986b3fb167f475e')  # noqa: E501
    (events, _), gas_amount, deposit_amount, user_address, timestamp = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash), '0.002095833929196665', '15828.918676384591706627', ethereum_accounts[0], TimestampMS(1730111759000)  # noqa: E501
    expected_events = [EvmEvent(
            tx_hash=evmhash,
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
            tx_hash=evmhash,
            sequence_index=148,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:1/erc20:0x44ff8620b8cA30902395A7bD3F2407e1A091BF73'),
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Bridge {deposit_amount} VIRTUAL from Ethereum to Base via Base bridge',
            counterparty=CPT_BASE,
            address=string_to_evm_address('0x3154Cf16ccdb4C6d922629664174b904d80F2C35'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0xd34Ec2202b56261b6d7586a752E37a36818c0538']])
def test_receive_eth_ethereum_to_base_bridge(base_inquirer, base_accounts):
    evmhash = deserialize_evm_tx_hash('0x924167064e29ecb68ea9586811b63799b6154158a6607ac9fcf9530667446a5c')  # noqa: E501
    (events, _), amount, user_address, timestamp = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=evmhash), '0.83', base_accounts[0], TimestampMS(1730133657000)  # noqa: E501
    expected_events = [EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Bridge {amount} ETH from Ethereum to Base via Base bridge',
            counterparty=CPT_BASE,
            address=string_to_evm_address('0x4200000000000000000000000000000000000010'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x1218d6396dC67eC0FFBEBDF049C865B83636EddA']])
def test_receive_erc20_ethereum_to_base_bridge(base_inquirer, base_accounts):
    evmhash = deserialize_evm_tx_hash('0xf731b5c5dc53117413b880d0c65501cebe50c78ba3621eca9344747c95b83357')  # noqa: E501
    (events, _), amount, user_address, timestamp = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=evmhash), '4900031.556715611515583027', base_accounts[0], TimestampMS(1730133393000)  # noqa: E501
    expected_events = [EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:8453/erc20:0x7Cea109FC3516eD1248ae9AA67B5a352cF74075e'),
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Bridge {amount} NOVA from Ethereum to Base via Base bridge',
            counterparty=CPT_BASE,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x6730b1Df17E50217777EeE475E34815964e3BFb2']])
def test_withdraw_eth_base_to_ethereum_bridge(base_inquirer, base_accounts):
    evmhash = deserialize_evm_tx_hash('0xe451ca095dd9d48f6558a226fc6cc9b28d19f39080545db63b8ba9410fe3df3e')  # noqa: E501
    (events, _), gas_amount, deposit_amount, user_address, timestamp = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=evmhash), '0.000000442236014244', '133.00839331231264871', base_accounts[0], TimestampMS(1729279481000)  # noqa: E501
    expected_events = [EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Bridge {deposit_amount} ETH from Base to Ethereum via Base bridge',
            counterparty=CPT_BASE,
            address=string_to_evm_address('0x4200000000000000000000000000000000000010'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x779e4b47c3Dea5689233821dFcf429E0485eF116']])
def test_withdraw_erc20_base_to_ethereum_bridge(base_inquirer, base_accounts):
    evmhash = deserialize_evm_tx_hash('0xbe4e54e77cb700f2755b236d7823295129c4d5e22fdc87df8058274bc0fefab1')  # noqa: E501
    (events, _), gas_amount, deposit_amount, user_address, timestamp = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=evmhash), '0.000029210771559657', '49352.072702', base_accounts[0], TimestampMS(1729293119000)  # noqa: E501
    expected_events = [EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=79,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:8453/erc20:0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA'),
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Bridge {deposit_amount} USDbC from Base to Ethereum via Base bridge',
            counterparty=CPT_BASE,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF']])
def test_new_eth_bridge(
        optimism_inquirer: OptimismInquirer,
        optimism_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xb35a4120ba0a1aadf7fc51e5e0167a4bc8c8b0d59939edd5c2f6ccec4b6612e8')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    expected_events = [EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1738244009000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal('0.1'),
            location_label=optimism_accounts[0],
            notes='Bridge 0.1 ETH from Ethereum to Optimism via Optimism bridge',
            counterparty=CPT_OPTIMISM,
            address=string_to_evm_address('0x4200000000000000000000000000000000000010'),
        ),
    ]
    assert events == expected_events
