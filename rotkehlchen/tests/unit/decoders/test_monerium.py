from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.monerium.constants import CPT_MONERIUM
from rotkehlchen.constants.assets import A_ETH_EURE
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.constants import A_GNOSIS_EURE
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChecksumEvmAddress, Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer


A_POLYGON_EURE = Asset('eip155:137/erc20:0x18ec0A6E18E5bc3784fDd3a3634b31245ab704F6')


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xbCCeE6Ff2bCAfA95300D222D316A29140c4746da']])
def test_minting_monerium_on_eth(ethereum_inquirer, ethereum_accounts):
    evmhash = deserialize_evm_tx_hash(val='0x4ed9db44c5ee4ba6a4cf3e8e9b386f0b857afebad8339a92666e175c747bdd74')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash)
    amount_str = '1500'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=113,
            timestamp=TimestampMS(1701773255000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH_EURE,
            amount=FVal(amount_str),
            location_label=ethereum_accounts[0],
            notes=f'Mint {amount_str} EURe',
            counterparty=CPT_MONERIUM,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x99a0618B846D43E29C15ac468Eae06d03C9243C7']])
def test_burning_monerium_on_eth(ethereum_inquirer, ethereum_accounts):
    evmhash = deserialize_evm_tx_hash(val='0x10d953610921f39d9d20722082077e03ec8db8d9c75e4b301d0d552119fd0354')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash)
    amount_str = '1161210.84'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=171,
            timestamp=TimestampMS(1701765059000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH_EURE,
            amount=FVal(amount_str),
            location_label=ethereum_accounts[0],
            notes=f'Burn {amount_str} EURe',
            counterparty=CPT_MONERIUM,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('polygon_pos_accounts', [['0x762e5f511c219823eeC73C743C8245807A53E123']])
def test_minting_monerium_on_matic(polygon_pos_inquirer, polygon_pos_accounts):
    evmhash = deserialize_evm_tx_hash(val='0xb240acc158fb2cdcdebc7321ca4a96f71b371379e2a78a9a7f27d0718a2e3735')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=evmhash,
    )
    amount_str = '95'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=176,
            timestamp=TimestampMS(1701800519000),
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_POLYGON_EURE,
            amount=FVal(amount_str),
            location_label=polygon_pos_accounts[0],
            notes=f'Mint {amount_str} EURe',
            counterparty=CPT_MONERIUM,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('polygon_pos_accounts', [['0x0A251dF99A88A20a93876205Fb7f5Faf2E85A481']])
def test_burning_monerium_on_matic(polygon_pos_inquirer, polygon_pos_accounts):
    evmhash = deserialize_evm_tx_hash(val='0xeaed8e3e862a9b41189e9039c825ee57fb80385801b8ac5c3ed70339baf243e5')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=evmhash,
    )
    amount_str = '208.93'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=418,
            timestamp=TimestampMS(1701794990000),
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_POLYGON_EURE,
            amount=FVal(amount_str),
            location_label=polygon_pos_accounts[0],
            notes=f'Burn {amount_str} EURe',
            counterparty=CPT_MONERIUM,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('gnosis_accounts', [['0x9566E3e6F55D4378243E55DE8e037Ee8E6e4de7E']])
def test_minting_monerium_on_gnosis(gnosis_inquirer, gnosis_accounts):
    evmhash = deserialize_evm_tx_hash(val='0x31183d757f530f799872600e6fe8644e3c20a1f90d02de9e89d0463454b400fa')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=evmhash,
    )
    amount_str = '66'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=371,
            timestamp=TimestampMS(1701802945000),
            location=Location.GNOSIS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_GNOSIS_EURE,
            amount=FVal(amount_str),
            location_label=gnosis_accounts[0],
            notes=f'Mint {amount_str} EURe',
            counterparty=CPT_MONERIUM,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('gnosis_accounts', [['0xAf31992307AcBb6Ad8795261EeA31494e62A8e40']])
def test_burning_monerium_on_gnosis(gnosis_inquirer, gnosis_accounts):
    evmhash = deserialize_evm_tx_hash(val='0xae087f309231e4dc1fa84927888deb6c56b9980e63f9cc049cbe2d7d2bc503e6')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=evmhash)
    amount_str = '1'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=500,
            timestamp=TimestampMS(1701801200000),
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_GNOSIS_EURE,
            amount=FVal(amount_str),
            location_label=gnosis_accounts[0],
            notes=f'Burn {amount_str} EURe',
            counterparty=CPT_MONERIUM,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('gnosis_accounts', [['0x39c185721fbe8b350363e6B49801305d32485A45']])
def test_burnfrom_monerium_on_gnosis(gnosis_inquirer, gnosis_accounts):
    evmhash = deserialize_evm_tx_hash(val='0xf04a5d84e6749828ff63991fb3323944472346c3b2c421e51d9999283d18f1fd')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=evmhash)
    amount_str = '501.04'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=497,
            timestamp=TimestampMS(1709969940000),
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_GNOSIS_EURE,
            amount=FVal(amount_str),
            location_label=gnosis_accounts[0],
            notes=f'Burn {amount_str} EURe',
            counterparty=CPT_MONERIUM,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0xA6Bf663Abd2c749ed479C383457b1a647dAB72E5']])
def test_mint_v2_eure(
        gnosis_inquirer: 'GnosisInquirer',
        gnosis_accounts: list['ChecksumEvmAddress'],
):
    evmhash = deserialize_evm_tx_hash(val='0x859af3a118c2f2503dca9aba17421cfe46bfe1b9e2585988cded6cc3da0dc0f4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=evmhash,
    )
    assert events == [EvmEvent(
        tx_hash=evmhash,
        sequence_index=1,
        timestamp=TimestampMS(1725021845000),
        location=Location.GNOSIS,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=Asset('eip155:100/erc20:0x420CA0f9B9b604cE0fd9C18EF134C705e5Fa3430'),
        amount=FVal(50),
        location_label=gnosis_accounts[0],
        notes='Mint 50 EURe',
        counterparty=CPT_MONERIUM,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x9c6c56700F4952d45896757ac098968E97695A55']])
def test_burn_v2_eure_gnosis(
        gnosis_inquirer: 'GnosisInquirer',
        gnosis_accounts: list['ChecksumEvmAddress'],
):
    evmhash = deserialize_evm_tx_hash(val='0xeaf8521348335bce75863507c48dd48c36ebbd43e2f774524a0d5b3cfa5d594e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=evmhash,
    )
    amount_str = '905.02'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=27,
            timestamp=TimestampMS(1725912575000),
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('eip155:100/erc20:0x420CA0f9B9b604cE0fd9C18EF134C705e5Fa3430'),
            amount=FVal(amount_str),
            location_label=gnosis_accounts[0],
            notes=f'Burn {amount_str} EURe',
            counterparty=CPT_MONERIUM,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xbcBc123312637Be33B36AC49331a9137a784254b']])
def test_mint_eure_on_arbitrum(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
):
    evmhash = deserialize_evm_tx_hash('0x792faaede6cd025d0a630669bf8fde06f51cc16aceebb67a09430536fea25109')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=evmhash,
    )
    assert events == [EvmEvent(
        tx_hash=evmhash,
        sequence_index=8,
        timestamp=TimestampMS(1744902081000),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=Asset('eip155:42161/erc20:0x0c06cCF38114ddfc35e07427B9424adcca9F44F8'),
        amount=FVal(4076),
        location_label=arbitrum_one_accounts[0],
        notes='Mint 4076 EURe',
        counterparty=CPT_MONERIUM,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xfFd0E4eF79c0C7B427D5CA3C455DB0eBCfa2aE4D']])
def test_burn_eure_on_arbitrum(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
):
    evmhash = deserialize_evm_tx_hash('0xd403cb41ddb6ae65fbfea44e1f8be8edb20ac5bc2252d69387b16bae3c5f7694')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=evmhash,
    )
    assert events == [EvmEvent(
        tx_hash=evmhash,
        sequence_index=46,
        timestamp=TimestampMS(1745310374000),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=Asset('eip155:42161/erc20:0x0c06cCF38114ddfc35e07427B9424adcca9F44F8'),
        amount=FVal(500),
        location_label=arbitrum_one_accounts[0],
        notes='Burn 500 EURe',
        counterparty=CPT_MONERIUM,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x4A551b4ADddB4CDBA24612bCbb543c9aD4DAE4B6']])
def test_monerium_token_migration(gnosis_inquirer: 'GnosisInquirer'):
    """Test that mints on the v1 to v2 migration are skipped correctly"""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=deserialize_evm_tx_hash('0x6241b6ef81b50e87585741362247852e6b325eb4401e5bde83e6c52ef9f2f097'),
    )
    assert events == []
