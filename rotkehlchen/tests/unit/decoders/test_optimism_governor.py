import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.optimism.constants import CPT_OPTIMISM
from rotkehlchen.chain.optimism.modules.optimism_governor.decoder import GOVERNOR_ADDRESS
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_vote_cast(optimism_inquirer, optimism_accounts):
    evmhash = deserialize_evm_tx_hash('0xeb9fb7b5047a30c4bb7e68343c6657ba4b0f0bcaf3d64972dcc01ccc3c10608b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=evmhash)
    user_address = optimism_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1683666539000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            amount=FVal('0.000656986283649328'),
            location_label=user_address,
            notes='Burn 0.000656986283649328 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1683666539000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=Asset('ETH'),
            amount=ZERO,
            location_label=user_address,
            notes='Vote FOR optimism governance proposal https://vote.optimism.io/proposals/51738314696473345172141808043782330430064117614433447104828853768775712054864',
            counterparty=CPT_OPTIMISM,
            address=GOVERNOR_ADDRESS,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_vote_cast_with_params(optimism_inquirer, optimism_accounts):
    """Data is taken from
    https://optimistic.etherscan.io/tx/0x7f54f0d15d1790ca2dd3c4870d9421f09a52f5bbe7f09472f864dc248f90f412
    """
    evmhash = deserialize_evm_tx_hash('0x7f54f0d15d1790ca2dd3c4870d9421f09a52f5bbe7f09472f864dc248f90f412')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=evmhash)
    user_address = optimism_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1688979323000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            amount=FVal('0.000033338918413158'),
            location_label=user_address,
            notes='Burn 0.000033338918413158 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=20,
            timestamp=TimestampMS(1688979323000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=Asset('ETH'),
            amount=ZERO,
            location_label=user_address,
            notes='Vote AGAINST optimism governance proposal https://vote.optimism.io/proposals/16633367863894036056841722161407059007904922838583677995599242776177398115322',
            counterparty=CPT_OPTIMISM,
            address=GOVERNOR_ADDRESS,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_vote_cast_with_reason(optimism_inquirer, optimism_accounts):
    evmhash = deserialize_evm_tx_hash('0xced69de2a81814554b9f69a19240737f0728f94bd67d94c73f960d24f99343bd')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=evmhash)
    user_address = optimism_accounts[0]
    timestamp = TimestampMS(1706051703000)
    gas_amount = '0.000022621225472652'
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=122,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=Asset('ETH'),
            amount=ZERO,
            location_label=user_address,
            notes='Vote AGAINST optimism governance proposal https://vote.optimism.io/proposals/10572947036210533292634221606922807092762967787561796032397523909369599512554 with reasoning: https://shorturl.at/abHS4',  # noqa: E501
            counterparty=CPT_OPTIMISM,
            address=GOVERNOR_ADDRESS,
        ),
    ]
