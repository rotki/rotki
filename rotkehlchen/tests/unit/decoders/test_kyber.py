import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.kyber.constants import CPT_KYBER_LEGACY
from rotkehlchen.chain.evm.decoding.kyber.constants import CPT_KYBER
from rotkehlchen.chain.evm.decoding.kyber.decoder import KYBER_AGGREGATOR_CONTRACT
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ARB, A_CRV, A_ETH, A_POLYGON_POS_MATIC, A_USDC
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x6d379cb5BA04c09293b21Bf314E7aba3FfEAaF5b']])
def test_kyber_legacy_old_contract(ethereum_inquirer, ethereum_accounts):
    """
    Data for trade taken from
    https://etherscan.io/tx/0xe9cc9f27ef2a09fe23abc886a0a0f7ae19d9e2eb73663e1e41e07a3e0c011b87
    """
    tx_hash = deserialize_evm_tx_hash('0xe9cc9f27ef2a09fe23abc886a0a0f7ae19d9e2eb73663e1e41e07a3e0c011b87')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)

    assert len(events) == 3
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=1591043988000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(0.01212979988),
            location_label=ethereum_accounts[0],
            notes='Burn 0.01212979988 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=1591043988000,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDC,
            amount=FVal(45),
            location_label=ethereum_accounts[0],
            notes='Swap 45 USDC in kyber',
            counterparty=CPT_KYBER_LEGACY,
            address=string_to_evm_address('0x65bF64Ff5f51272f729BDcD7AcFB00677ced86Cd'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=1591043988000,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal('0.187603293406027635'),
            location_label=ethereum_accounts[0],
            notes='Receive 0.187603293406027635 ETH from kyber swap',
            counterparty=CPT_KYBER_LEGACY,
            address=string_to_evm_address('0x65bF64Ff5f51272f729BDcD7AcFB00677ced86Cd'),
        )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x5340F6faff9BF55F66C16Db6Bf9E020d987F87D0']])
def test_kyber_legacy_new_contract(ethereum_inquirer):
    """Data for trade taken from
    https://etherscan.io/tx/0xe80928d5e21f9628c047af1f8b191cbffbb6b8b9945adb502cfb3af152552f22
    """
    tx_hash = deserialize_evm_tx_hash('0xe80928d5e21f9628c047af1f8b191cbffbb6b8b9945adb502cfb3af152552f22')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)

    assert len(events) == 3
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=1644182638000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(0.066614401),
            location_label='0x5340F6faff9BF55F66C16Db6Bf9E020d987F87D0',
            notes='Burn 0.066614401 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=1644182638000,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDC,
            amount=FVal(8139.77872),
            location_label='0x5340F6faff9BF55F66C16Db6Bf9E020d987F87D0',
            notes='Swap 8139.77872 USDC in kyber',
            counterparty=CPT_KYBER_LEGACY,
            address=string_to_evm_address('0x7C66550C9c730B6fdd4C03bc2e73c5462c5F7ACC'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=1644182638000,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_CRV,
            amount=FVal('2428.33585390706162556'),
            location_label='0x5340F6faff9BF55F66C16Db6Bf9E020d987F87D0',
            notes='Receive 2428.33585390706162556 CRV from kyber swap',
            counterparty=CPT_KYBER_LEGACY,
            address=string_to_evm_address('0x7C66550C9c730B6fdd4C03bc2e73c5462c5F7ACC'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xceD462398bDFBb1B45d75b7F2c61172643a18009']])
def test_kyber_aggregator_swap_ethereum(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x82205817d573da45a2f6da6e5e9623739bd4cdbce5f9b65d48450805bce0bdff')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1714563455000)
    gas, approval_amount = '0.00199568430867988', '20.819823166790499332'
    spend_amount, receive_amount = '20', '21.100486952910759139'
    a_sweth = Asset('eip155:1/erc20:0xf951E335afb289353dc249e82926178EaC7DEd78')
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=258,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=a_sweth,
            amount=FVal(approval_amount),
            location_label=ethereum_accounts[0],
            notes=f'Set swETH spending approval of {ethereum_accounts[0]} by {KYBER_AGGREGATOR_CONTRACT} to {approval_amount}',  # noqa: E501
            address=KYBER_AGGREGATOR_CONTRACT,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=259,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=a_sweth,
            amount=FVal(spend_amount),
            location_label=ethereum_accounts[0],
            notes=f'Swap {spend_amount} swETH in kyber',
            counterparty=CPT_KYBER,
            address=string_to_evm_address('0xf081470f5C6FBCCF48cC4e5B82Dd926409DcdD67'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=260,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal(receive_amount),
            location_label=ethereum_accounts[0],
            notes=f'Receive {receive_amount} ETH from kyber swap',
            counterparty=CPT_KYBER,
            address=string_to_evm_address('0xf081470f5C6FBCCF48cC4e5B82Dd926409DcdD67'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x0e414c1c4780df6c09c2f1070990768D44B70b1D']])
def test_kyber_aggregator_swap_arbitrum_one(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0xbcc690fb11b0a6b0f3b1e5bed6abb5c3e93d5b4855472f94adea824bfa2be6ed')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1714517062000)
    gas, spend_amount, receive_amount = '0.00001237136', '1', '2693482419.136828'
    a_aidoge = Asset('eip155:42161/erc20:0x09E18590E8f76b6Cf471b3cd75fE1A1a9D2B2c2b')
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=arbitrum_one_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ARB,
            amount=FVal(spend_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Swap {spend_amount} ARB in kyber',
            counterparty=CPT_KYBER,
            address=string_to_evm_address('0x11ddD59C33c73C44733b4123a86Ea5ce57F6e854'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=a_aidoge,
            amount=FVal(receive_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Receive {receive_amount} AIDOGE from kyber swap',
            counterparty=CPT_KYBER,
            address=string_to_evm_address('0x11ddD59C33c73C44733b4123a86Ea5ce57F6e854'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x8a8162b86A3179a9F7A2F46FFd7029B669876B75']])
def test_kyber_aggregator_swap_base(base_inquirer, base_accounts):
    tx_hash = deserialize_evm_tx_hash('0x27b040b725caa995343f98ca16fabebfbd2116063488761cbbdc1f99a2bf8619')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1714588063000)
    gas, spend_amount, receive_amount = '0.000057116139238782', '10076.279107426212183073', '19.725836184026980754'  # noqa: E501
    a_dog = Asset('eip155:8453/erc20:0xAfb89a09D82FBDE58f18Ac6437B3fC81724e4dF6')
    a_uni_base = Asset('eip155:8453/erc20:0xc3De830EA07524a0761646a6a4e4be0e114a3C83')
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=base_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=a_dog,
            amount=ZERO,
            location_label=base_accounts[0],
            notes=f'Revoke DOG spending approval of {base_accounts[0]} by {KYBER_AGGREGATOR_CONTRACT}',  # noqa: E501
            address=KYBER_AGGREGATOR_CONTRACT,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=a_dog,
            amount=FVal(spend_amount),
            location_label=base_accounts[0],
            notes=f'Swap {spend_amount} DOG in kyber',
            counterparty=CPT_KYBER,
            address=string_to_evm_address('0x11ddD59C33c73C44733b4123a86Ea5ce57F6e854'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=a_uni_base,
            amount=FVal(receive_amount),
            location_label=base_accounts[0],
            notes=f'Receive {receive_amount} UNI from kyber swap',
            counterparty=CPT_KYBER,
            address=string_to_evm_address('0x11ddD59C33c73C44733b4123a86Ea5ce57F6e854'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x1961425eB7467330380ea268d4b909C7975f79c6']])
def test_kyber_aggregator_swap_optimism(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0xc50282f437bacfbeef00baf4dae0785a259f87294089b96f7a6363ad4928570e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1714589233000)
    gas, spend_amount, receive_amount = '0.000018524563536246', '1.404275039033980017', '1.633943151167508706'  # noqa: E501
    a_wsteth_op = Asset('eip155:10/erc20:0x1F32b1c2345538c0c6f582fCB022739c4A194Ebb')
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=optimism_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=46,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=a_wsteth_op,
            amount=ZERO,
            location_label=optimism_accounts[0],
            notes=f'Revoke wstETH spending approval of {optimism_accounts[0]} by {KYBER_AGGREGATOR_CONTRACT}',  # noqa: E501
            address=KYBER_AGGREGATOR_CONTRACT,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=47,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=a_wsteth_op,
            amount=FVal(spend_amount),
            location_label=optimism_accounts[0],
            notes=f'Swap {spend_amount} wstETH in kyber',
            counterparty=CPT_KYBER,
            address=string_to_evm_address('0x11ddD59C33c73C44733b4123a86Ea5ce57F6e854'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=48,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal(receive_amount),
            location_label=optimism_accounts[0],
            notes=f'Receive {receive_amount} ETH from kyber swap',
            counterparty=CPT_KYBER,
            address=string_to_evm_address('0x11ddD59C33c73C44733b4123a86Ea5ce57F6e854'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x686e14AFb1AB9eb5aB89593ddE9fCe9389cA8C35']])
def test_kyber_aggregator_swap_polygon(polygon_pos_inquirer, polygon_pos_accounts):
    tx_hash = deserialize_evm_tx_hash('0xfd32220a3dfad3a74b0e172b88f0052670cd60b72f4b0cf19ded4a4145ba4a2b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1714589685000)
    gas, spend_amount, receive_amount = '0.029364910546207', '11.419216', '3.214374219088998048'
    a_bal_poly = Asset('eip155:137/erc20:0x9a71012b13ca4d3d0cdc72a177df3ef03b0e76a3')
    a_usdc_poly = Asset('eip155:137/erc20:0x3c499c542cef5e3811e1192ce70d8cc03d5c3359')
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_POLYGON_POS_MATIC,
            amount=FVal(gas),
            location_label=polygon_pos_accounts[0],
            notes=f'Burn {gas} POL for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_subtype=HistoryEventSubType.SPEND,
            asset=a_usdc_poly,
            amount=FVal(spend_amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Swap {spend_amount} USDC in kyber',
            counterparty=CPT_KYBER,
            address=string_to_evm_address('0x7bAF833f82BB1971f99A5a5d84bED1d5D0dEDD70'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=a_bal_poly,
            amount=FVal(receive_amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Receive {receive_amount} BAL from kyber swap',
            counterparty=CPT_KYBER,
            address=string_to_evm_address('0x7bAF833f82BB1971f99A5a5d84bED1d5D0dEDD70'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('scroll_accounts', [['0x8C6270BB0D3d95Dad8581D6e9795Bb7089A34123']])
def test_kyber_aggregator_swap_scroll(scroll_inquirer, scroll_accounts):
    tx_hash = deserialize_evm_tx_hash('0xd5c9011e2edd8b724eb3f0a691f5657eb7adb0d943be01b54b52a22b82df7062')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=scroll_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1714590811000)
    gas, spend_amount, receive_amount = '0.00014495886763554', '327.431697', '0.109956490224557286'
    a_usdc_scroll = Asset('eip155:534352/erc20:0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4')
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=scroll_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_subtype=HistoryEventSubType.SPEND,
            asset=a_usdc_scroll,
            amount=FVal(spend_amount),
            location_label=scroll_accounts[0],
            notes=f'Swap {spend_amount} USDC in kyber',
            counterparty=CPT_KYBER,
            address=string_to_evm_address('0xf40442E1Cb0BdFb496E8B7405d0c1c48a81BC897'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal(receive_amount),
            location_label=scroll_accounts[0],
            notes=f'Receive {receive_amount} ETH from kyber swap',
            counterparty=CPT_KYBER,
            address=string_to_evm_address('0xf40442E1Cb0BdFb496E8B7405d0c1c48a81BC897'),
        ),
    ]
    assert events == expected_events
