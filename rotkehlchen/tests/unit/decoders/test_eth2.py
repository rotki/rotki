
import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.eth2.constants import CPT_ETH2
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xc66962Ff943449C90b457856D448Aa19D60CB033']])
def test_deposit(database, ethereum_inquirer, ethereum_accounts):
    """
    Data is taken from
    https://etherscan.io/tx/0xb3658f940cab23f95273bb7c199eec5c71424a8bf2f111201f5cc2a1491d3471
    """
    evmhash = deserialize_evm_tx_hash('0xb3658f940cab23f95273bb7c199eec5c71424a8bf2f111201f5cc2a1491d3471')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    assert events == [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1674558203000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.000788637337054068')),
            location_label=user_address,
            notes='Burned 0.000788637337054068 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1674558203000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            balance=Balance(amount=FVal('32')),
            location_label=user_address,
            notes='Deposit 32 ETH to validator with pubkey 0xa685b19738ac8d7ee301f434f77fdbca50f7a2b8d287f4ab6f75cae251aa821576262b79ae9d58d9b458ba748968dfda. Deposit index: 519464. Withdrawal credentials: 0x00c5af874f28011e2f559e1214131da5f11b12845921b0d8e436f0cd37d683a8',  # noqa: E501
            counterparty=CPT_ETH2,
            extra_data={'withdrawal_credentials': '0x00c5af874f28011e2f559e1214131da5f11b12845921b0d8e436f0cd37d683a8'},  # noqa: E501
        ),
    ]
