
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
            sequence_index=2,
            timestamp=TimestampMS(1674558203000),
            balance=Balance(amount=FVal('32')),
            depositor=user_address,
        ),
    ]


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x3e5fd0244e13d82fC230f3Fc610bcd76b3c8217C']])
def test_multiple_deposits(database, ethereum_inquirer, ethereum_accounts):
    evmhash = deserialize_evm_tx_hash('0x819fe4a07894cf044f5d8c63e5c1e2294e068d05bf91d9cfc3e7ae3e60528ae5')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    dbeth2 = DBEth2(database)
    validators = [
        Eth2Validator(
            index=55750,
            public_key=Eth2PubKey('0x91108c07526641ad22e91b1038c640b9efce236e9aa8c1c355676a6862e4c082454ceaa599b305ceca9c15984fdbf1a8'),  # noqa: E501
            ownership_proportion=ONE,
        ), Eth2Validator(
            index=55751,
            public_key=Eth2PubKey('0x8e31e6d9771094182a70b75882f7d186986d726f7b4da95f542d18a1cb7fa38cd31b450a9fc62867d81dfc9ad9cbd641'),  # noqa: E501
            ownership_proportion=ONE,
        ), Eth2Validator(
            index=55752,
            public_key=Eth2PubKey('0xa01b86a30e5e349dccc04aee560502dd49ba87342c22ea88e462ab2c843c92eed08407150a8eaa849dc9de909c59679a'),  # noqa: E501
            ownership_proportion=ONE,
        ),
    ]
    with database.user_write() as write_cursor:
        dbeth2.add_validators(  # add validator in DB so decoder can map pubkey -> index
            write_cursor,
            validators=validators,
        )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1608594280000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.010956672')),
            location_label=user_address,
            notes='Burned 0.010956672 ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EthDepositEvent(
            tx_hash=evmhash,
            validator_index=55750,
            sequence_index=2,
            timestamp=TimestampMS(1608594280000),
            balance=Balance(amount=FVal('32')),
            depositor=user_address,
        ), EthDepositEvent(
            tx_hash=evmhash,
            validator_index=55751,
            sequence_index=3,
            timestamp=TimestampMS(1608594280000),
            balance=Balance(amount=FVal('32')),
            depositor=user_address,
        ), EthDepositEvent(
            tx_hash=evmhash,
            validator_index=55752,
            sequence_index=4,
            timestamp=TimestampMS(1608594280000),
            balance=Balance(amount=FVal('32')),
            depositor=user_address,
        ),
    ]
    assert events == expected_events
