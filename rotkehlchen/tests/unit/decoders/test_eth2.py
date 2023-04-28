
import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.eth2 import EthDepositEvent
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.eth2.structures import Eth2Validator
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Eth2PubKey, Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xc66962Ff943449C90b457856D448Aa19D60CB033']])
def test_deposit(database, ethereum_inquirer, ethereum_accounts):
    """
    Data is taken from
    https://etherscan.io/tx/0xb3658f940cab23f95273bb7c199eec5c71424a8bf2f111201f5cc2a1491d3471
    """
    dbeth2 = DBEth2(database)
    validator = Eth2Validator(index=507258, public_key=Eth2PubKey('0xa685b19738ac8d7ee301f434f77fdbca50f7a2b8d287f4ab6f75cae251aa821576262b79ae9d58d9b458ba748968dfda'), ownership_proportion=ONE)  # noqa: E501
    with database.user_write() as write_cursor:
        dbeth2.add_validators(  # add validator in DB so decoder can map pubkey -> index
            write_cursor,
            validators=[validator],
        )

    evmhash = deserialize_evm_tx_hash('0xb3658f940cab23f95273bb7c199eec5c71424a8bf2f111201f5cc2a1491d3471')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1674558203000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.000788637337054068')),
            location_label=user_address,
            notes='Burned 0.000788637337054068 ETH for gas',
            counterparty=CPT_GAS,
        ), EthDepositEvent(
            tx_hash=evmhash,
            validator_index=validator.index,
            sequence_index=1,
            timestamp=TimestampMS(1674558203000),
            balance=Balance(amount=FVal('32')),
            depositor=user_address,
        ),
    ]
