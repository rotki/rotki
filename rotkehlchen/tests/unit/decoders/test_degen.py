import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.base.modules.degen.constants import CPT_DEGEN
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChecksumEvmAddress, Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr()
@pytest.mark.parametrize('base_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_claim_airdrop_1(
        base_accounts: list[ChecksumEvmAddress],
        base_transaction_decoder: EVMTransactionDecoder,
):
    evmhash = deserialize_evm_tx_hash('0x885722ab252530e687212799080d5d158d767536b62e0d45a700091a5424bcaa ')  # noqa: E501
    user_address = base_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        database=base_transaction_decoder.database,
        tx_hash=evmhash,
    )
    degen_token = Asset('eip155:8453/erc20:0x4ed4E862860beD51a9570b96d89aF5E1B0Efefed')
    timestamp = TimestampMS(1709555247000)
    gas_amount, claimed_amount = '0.000443147649294366', '100'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(FVal(gas_amount)),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes=f'Burned {gas_amount} ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=9,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=degen_token,
            balance=Balance(FVal(claimed_amount)),
            location_label=user_address,
            counterparty=CPT_DEGEN,
            address=string_to_evm_address('0x88d42b6DBc10D2494A0c6c189CeFC7573a6dCE62'),
            notes=f'Claim {claimed_amount} DEGEN from Degen airdrop 2',
        ),
    ]
    assert events == expected_events
