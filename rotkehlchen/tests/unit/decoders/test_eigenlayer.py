import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
from rotkehlchen.chain.ethereum.modules.eigenlayer.balances import EigenlayerBalances
from rotkehlchen.chain.ethereum.modules.eigenlayer.constants import (
    CPT_EIGENLAYER,
    EIGEN_TOKEN_ID,
    EIGENLAYER_AIRDROP_S1_PHASE1_DISTRIBUTOR,
    EIGENLAYER_AIRDROP_S1_PHASE2_DISTRIBUTOR,
    EIGENLAYER_AIRDROP_S2_DISTRIBUTOR,
    EIGENLAYER_DELEGATION,
    EIGENLAYER_STRATEGY_MANAGER,
    EIGENPOD_DELAYED_WITHDRAWAL_ROUTER,
    EIGENPOD_MANAGER,
    REWARDS_COORDINATOR,
)
from rotkehlchen.chain.ethereum.transactions import EthereumTransactions
from rotkehlchen.chain.evm.decoding.safe.constants import CPT_SAFE_MULTISIG
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_STETH, A_WETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.eigenlayer import add_create_eigenpod_event
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xbec0937E0E99425a886B99A3b956C7aC6C39aA12']])
def test_deposit_token(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x716b15f5088ff469d7d31680535d35b085e1c3de25255c7849e5955a59df8d31')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    strategy_addr = string_to_evm_address('0x0Fe4F44beE93503346A3Ac9EE5A26b130a5796d6')
    a_sweth = Asset('eip155:1/erc20:0xf951E335afb289353dc249e82926178EaC7DEd78')
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1702926167000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.049006058268043653'),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=112,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=a_sweth,
        amount=ZERO,
        location_label=ethereum_accounts[0],
        notes=f'Revoke swETH spending approval of {ethereum_accounts[0]} by {EIGENLAYER_STRATEGY_MANAGER}',  # noqa: E501
        address=EIGENLAYER_STRATEGY_MANAGER,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=113,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=a_sweth,
        amount=FVal(deposited_amount := '5.740516176725108094'),
        location_label=ethereum_accounts[0],
        notes=f'Deposit {deposited_amount} swETH in EigenLayer',
        counterparty=CPT_EIGENLAYER,
        extra_data={'strategy': strategy_addr},
        address=strategy_addr,
    )]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x47E50634E32212F43713Bf4e4A86E6275AcD456d']])
def test_withdraw(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x00bdab08d05bd68f8f863e35a8dbe435978481dcbf15faf7276da30a5bfee971')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    strategy_addr = string_to_evm_address('0x0Fe4F44beE93503346A3Ac9EE5A26b130a5796d6')
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1707668387000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.004606768190817408'),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=152,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=Asset('eip155:1/erc20:0xf951E335afb289353dc249e82926178EaC7DEd78'),
        amount=FVal(withdrawn_amount := '0.407049270448991651'),
        location_label=ethereum_accounts[0],
        notes=f'Unstake {withdrawn_amount} swETH from EigenLayer',
        counterparty=CPT_EIGENLAYER,
        address=strategy_addr,
    )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xabe8430e3f0BeCa32915dA84E530f81A01379953']])
def test_airdrop_claim_s1_phase1(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x0a72c7bf0fe1808035f8df466a70453f29c6b57d0bec46913d993a19ef72265c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    claim_amount = '110'
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1715680739000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00074757962836592'),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=253,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.AIRDROP,
        asset=Asset(EIGEN_TOKEN_ID),
        amount=FVal(claim_amount),
        location_label=ethereum_accounts[0],
        notes='Claim 110 EIGEN from the Eigenlayer airdrop season 1 phase 1',
        counterparty=CPT_EIGENLAYER,
        address=EIGENLAYER_AIRDROP_S1_PHASE1_DISTRIBUTOR,
        extra_data={AIRDROP_IDENTIFIER_KEY: 'eigen_s1_phase1'},
    )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xf6d3d6B6cee9991900Bf53261e1bb213A3d54Fec']])
def test_airdrop_claim_s1_phase2(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x7896ca761e9e2fd53dbec28c946d5dbc2e0802a3700641d26d61bc79afaac1a5')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    claim_amount = '110'
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1720527731000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000428532817567424'),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=752,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.AIRDROP,
        asset=Asset(EIGEN_TOKEN_ID),
        amount=FVal(claim_amount),
        location_label=ethereum_accounts[0],
        notes='Claim 110 EIGEN from the Eigenlayer airdrop season 1 phase 2',
        counterparty=CPT_EIGENLAYER,
        address=EIGENLAYER_AIRDROP_S1_PHASE2_DISTRIBUTOR,
        extra_data={AIRDROP_IDENTIFIER_KEY: 'eigen_s1_phase2'},
    )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x65151A6343b16c38286f31fcC93e20246629cF8c']])
def test_stake_eigen(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x4da63226965a8b0584f137efa934106cd0cb7a15b536d6f659945cfd4c260b4e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1715684387000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00141296787957222'),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=206,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=(a_eigen := Asset(EIGEN_TOKEN_ID)),
        amount=ZERO,
        location_label=ethereum_accounts[0],
        notes=f'Revoke EIGEN spending approval of {ethereum_accounts[0]} by {EIGENLAYER_STRATEGY_MANAGER}',  # noqa: E501
        address=EIGENLAYER_STRATEGY_MANAGER,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=207,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=a_eigen,
        amount=FVal(staked_amount := '110'),
        location_label=ethereum_accounts[0],
        notes=f'Deposit {staked_amount} EIGEN in EigenLayer',
        counterparty=CPT_EIGENLAYER,
        extra_data={'strategy': (strategy_addr := '0xaCB55C530Acdb2849e6d4f36992Cd8c9D50ED8F7')},
        address=strategy_addr,
    )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x80B7EDA1Baa2290478205786615F65052c80882f']])
def test_deploy_eigenpod(ethereum_inquirer, ethereum_accounts, database):
    ethereum_transactions = EthereumTransactions(ethereum_inquirer=ethereum_inquirer, database=database)  # noqa: E501
    ethereum_tx_decoder = EthereumTransactionDecoder(database=database, ethereum_inquirer=ethereum_inquirer, transactions=ethereum_transactions)  # noqa: E501
    assert ethereum_tx_decoder.decoders['Eigenlayer'].eigenpod_owner_mapping == {}

    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x910087fb1be44dbf2d89363579c162e70d5666f16182c9015d635c4f81ac07b6')),  # noqa: E501
        transactions=ethereum_transactions,
        evm_decoder=ethereum_tx_decoder,
    )
    eigenpod_address = '0x664BFef14A62F316175d39D355809D04D2Cb7a23'
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1715733143000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00133529055565527'),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=219,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.CREATE,
        asset=A_ETH,
        amount=ZERO,
        location_label=ethereum_accounts[0],
        notes=f'Deploy eigenpod {eigenpod_address}',
        extra_data={'eigenpod_owner': ethereum_accounts[0], 'eigenpod_address': eigenpod_address},
        counterparty=CPT_EIGENLAYER,
        address=EIGENPOD_MANAGER,
    )]
    assert events == expected_events
    assert ethereum_tx_decoder.decoders['Eigenlayer'].eigenpod_owner_mapping == {
        eigenpod_address: ethereum_accounts[0],
    }


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x15646dDb42Ee60B26A0BA727CFeB4E8b1A319cdE', '0x24557b5D264757A3fCe2B55b257709D9f8C5aE94']])  # noqa: E501
def test_deploy_eigenpod_via_safe(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x449447b417019f9d8617e41c735c206d94669e91e066bd3cb0dd609fcd8faff7')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    eigenpod_address = '0x081aC22eb8582eF9f5ae596A5E8Df42b451b28b7'
    user_address = ethereum_accounts[0]
    safe_address = ethereum_accounts[1]
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1715601779000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.002212107522528736'),
        location_label=user_address,
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=120,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.CREATE,
        asset=A_ETH,
        amount=ZERO,
        location_label=safe_address,
        notes=f'Deploy eigenpod {eigenpod_address} with owner {safe_address}',
        extra_data={'eigenpod_owner': safe_address, 'eigenpod_address': eigenpod_address},
        counterparty=CPT_EIGENLAYER,
        address=EIGENPOD_MANAGER,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=121,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ZERO,
        location_label=user_address,
        notes=f'Successfully executed safe transaction 0xd5732b4ea1baa0f37f840270c1da9e9c4175b79f2469909f2df837b05b8a7f71 for multisig {safe_address}',  # noqa: E501
        counterparty=CPT_SAFE_MULTISIG,
        address=safe_address,
    )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd007058e9b58E74C33c6bF6fbCd38BaAB813cBB6']])
def test_create_delayed_withdrawals(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xd054c9f07b880ac8e587c725b0427dde2b4c2633250f6f84a5c803fa665fe307')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    withdrawal_amount = '0.021045998'
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1715768063000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.036853617070145433'),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=243,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ZERO,
        location_label=ethereum_accounts[0],
        notes=f'Start a delayed withdrawal of {withdrawal_amount} ETH from Eigenlayer by processing 20 partial and 0 full beaconchain withdrawals',  # noqa: E501
        counterparty=CPT_EIGENLAYER,
        address=EIGENPOD_DELAYED_WITHDRAWAL_ROUTER,
    )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x02855536652F67cB936851D94c793Fb3Ba27F9bb']])
def test_lst_create_delayed_withdrawals(database, ethereum_inquirer, ethereum_accounts, inquirer):  # pylint: disable=unused-argument
    events, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x8c006f764e9264cd150b2583ba72205bb4575ace76ed3afa83689227e9fe461b')),  # noqa: E501
    )
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1718731823000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.001066996197578511'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=264,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_STETH,
        amount=ZERO,
        location_label=user_address,
        notes=f'Undelegate {(amount := "0.514712311805302523")} restaked stETH from 0x4d7C3fc856AB52753B91A6c9213aDF013309dD25',  # noqa: E501
        counterparty=CPT_EIGENLAYER,
        address=EIGENLAYER_DELEGATION,
        extra_data={'amount': amount},
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=265,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=A_STETH,
        amount=ZERO,
        location_label=user_address,
        notes=f'Queue withdrawal of {amount} stETH from Eigenlayer',
        counterparty=CPT_EIGENLAYER,
        address=EIGENLAYER_DELEGATION,
        extra_data={
            'amount': amount,
            'withdrawer': user_address,
            'withdrawal_root': '0xaa5e010334aa81720474f3625f04109a378cab05e6e6b8c9bcecc2dffab2fb7f',  # noqa: E501
            'strategy': '0x93c4b944D05dfe6df7645A86cd2206016c51564D',
        },
    )]
    assert events == expected_events

    # Also check that the balances are seen by the balance inquirer
    balances_inquirer = EigenlayerBalances(
        evm_inquirer=ethereum_inquirer,
        tx_decoder=tx_decoder,
    )
    balances = balances_inquirer.query_balances(addresses=ethereum_accounts)
    assert balances[ethereum_accounts[0]].assets[A_STETH.resolve_to_evm_token()][balances_inquirer.counterparty] == Balance(  # noqa: E501
        amount=FVal(amount),
        value=FVal('0.7720684677079537845'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x6Ee701145E1F44C9AA9fc8889F80863198838145']])
def test_lst_complete_delayed_withdrawals(database, ethereum_inquirer, ethereum_accounts, inquirer):  # pylint: disable=unused-argument  # noqa: E501
    queue_tx_hash = deserialize_evm_tx_hash('0xeab48010e80d50b7d35fd43a886448ffca1e798b641baf7c8877fc04075d972b')  # noqa: E501
    get_decoded_events_of_transaction(  # just decode the events of the withdrawal queuing
        evm_inquirer=ethereum_inquirer,
        tx_hash=queue_tx_hash,
    )  # and now get the actual withdrawal complete transaction a week later
    tx_hash = deserialize_evm_tx_hash('0x2c9a7caf78126fdfe43760dedbf3648c6a3255ee17a7bc312372dba26e16132b')  # noqa: E501
    events, tx_decoder = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1718879927000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000880395253730733'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=581,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
        asset=(cbeth := Asset('eip155:1/erc20:0xBe9895146f7AF43049ca1c1AE358B0541Ea49704')),
        amount=FVal(amount := '0.108703837292797063'),
        location_label=user_address,
        notes=f'Withdraw {amount} cbETH from Eigenlayer',
        counterparty=CPT_EIGENLAYER,
        address=(cbeth_strategy := string_to_evm_address('0x54945180dB7943c0ed0FEE7EdaB2Bd24620256bc')),  # noqa: E501
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=582,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=cbeth,
        amount=ZERO,
        location_label=user_address,
        notes='Complete eigenlayer withdrawal of cbETH',
        counterparty=CPT_EIGENLAYER,
        address=EIGENLAYER_DELEGATION,
        extra_data={'matched': True},
    )]
    assert events == expected_events

    # also let's get the queueing event and see it has been marked as completed
    dbevents = DBHistoryEvents(database)
    with database.conn.read_ctx() as cursor:
        filter_query = EvmEventFilterQuery.make(
            tx_hashes=[queue_tx_hash],
            event_subtypes=[HistoryEventSubType.REMOVE_ASSET],
        )
        events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=filter_query,
        )
    assert events[0].extra_data == {
        'amount': '0.108703837292797064',
        'completed': True,
        'strategy': cbeth_strategy,
        'withdrawal_root': '0x095056ecfcb92d7b60f2e917be58aad008068ba9e34d882eea9eebf65ce81f77',
        'withdrawer': user_address,
    }

    # Finally check that the balances of this withdrawal are not seen by the balance inquirer
    # since we have completed the withdrawal and marked the event as such
    balances_inquirer = EigenlayerBalances(
        evm_inquirer=ethereum_inquirer,
        tx_decoder=tx_decoder,
    )
    balances = balances_inquirer.query_balances(addresses=ethereum_accounts)
    assert balances[ethereum_accounts[0]].assets[cbeth][balances_inquirer.counterparty] == Balance()  # noqa: E501


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x1DEd04611E3B48F620D42bC97f798cb085403f73']])
def test_complete_withdrawal_post_slashing_token(database, ethereum_inquirer, ethereum_accounts):
    """Test queueing and completing an EIGEN withdrawal emitting the SlashingWithdrawalQueued
    and SlashingWithdrawalCompleted events introduced by the slashing upgrade (ELIP-002).
    Also checks that the EIGEN strategy's bEIGEN underlying token is shown as EIGEN,
    which is what is actually deposited and withdrawn by the user."""
    queue_tx_hash = deserialize_evm_tx_hash('0x75d5947cf192631dd003fcf6fb5112f4f2eaca4d23f79397b72a3cf4d73a481e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=queue_tx_hash,
    )
    assert events == [EvmEvent(
        tx_ref=queue_tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1753875839000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00093321233696448'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=queue_tx_hash,
        sequence_index=625,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=(eigen := Asset(EIGEN_TOKEN_ID)),
        amount=ZERO,
        location_label=user_address,
        notes=f'Undelegate {(amount := "60")} restaked EIGEN from 0x5ACCC90436492F24E6aF278569691e2c942A676d',  # noqa: E501
        counterparty=CPT_EIGENLAYER,
        address=EIGENLAYER_DELEGATION,
        extra_data={'amount': amount},
    ), EvmEvent(
        tx_ref=queue_tx_hash,
        sequence_index=626,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=eigen,
        amount=ZERO,
        location_label=user_address,
        notes=f'Queue withdrawal of {amount} EIGEN from Eigenlayer',
        counterparty=CPT_EIGENLAYER,
        address=EIGENLAYER_DELEGATION,
        extra_data={
            'amount': amount,
            'withdrawer': user_address,
            'withdrawal_root': '0x8e4008a087a4095d217cc2e7996f42e31cbfff67aeead1332d41706de408ec4e',  # noqa: E501
            'strategy': (eigen_strategy := string_to_evm_address('0xaCB55C530Acdb2849e6d4f36992Cd8c9D50ED8F7')),  # noqa: E501
        },
    )]

    tx_hash = deserialize_evm_tx_hash('0x9340fb42391c734caccb46048238ba2579c51e6f8096d2abb6216b509a1c1db6')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1784026463000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000206362625778015'),
        location_label=user_address,
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=446,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=eigen,
        amount=ZERO,
        location_label=user_address,
        notes='Complete eigenlayer withdrawal of EIGEN',
        counterparty=CPT_EIGENLAYER,
        address=EIGENLAYER_DELEGATION,
        extra_data={'matched': True},
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=453,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
        asset=eigen,
        amount=FVal(amount),
        location_label=user_address,
        notes=f'Withdraw {amount} EIGEN from Eigenlayer',
        counterparty=CPT_EIGENLAYER,
        address=eigen_strategy,
    )]

    with database.conn.read_ctx() as cursor:  # check the queueing event is marked as completed
        events = DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(
                tx_hashes=[queue_tx_hash],
                event_subtypes=[HistoryEventSubType.REMOVE_ASSET],
            ),
        )
    assert events[0].extra_data == {
        'amount': amount,
        'completed': True,
        'withdrawer': user_address,
        'withdrawal_root': '0x8e4008a087a4095d217cc2e7996f42e31cbfff67aeead1332d41706de408ec4e',
        'strategy': eigen_strategy,
    }


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x79f4B334c0e290250Dd5b65799310805FD807F0F']])
def test_complete_withdrawal_post_slashing_eth(database, ethereum_inquirer, ethereum_accounts):
    """Test queueing and completing a natively restaked ETH withdrawal emitting the
    events introduced by the slashing upgrade (ELIP-002). The ETH is sent to the
    withdrawer by their eigenpod when the withdrawal is completed."""
    queue_tx_hash = deserialize_evm_tx_hash('0xbc678ee75a2ee4fbbb24a29b614f6b601b9a08765f0b142f2c20b5aec27153a1')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=queue_tx_hash,
    )
    assert events == [EvmEvent(
        tx_ref=queue_tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1782421343000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000073031120801748'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=queue_tx_hash,
        sequence_index=640,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ZERO,
        location_label=user_address,
        notes=f'Undelegate {(amount := "6.24")} restaked ETH from 0xa026265a0F01A6E1A19b04655519429df0a57c4e',  # noqa: E501
        counterparty=CPT_EIGENLAYER,
        address=EIGENLAYER_DELEGATION,
        extra_data={'amount': amount},
    ), EvmEvent(
        tx_ref=queue_tx_hash,
        sequence_index=642,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=A_ETH,
        amount=ZERO,
        location_label=user_address,
        notes=f'Queue withdrawal of {amount} ETH from Eigenlayer',
        counterparty=CPT_EIGENLAYER,
        address=EIGENLAYER_DELEGATION,
        extra_data={
            'amount': amount,
            'withdrawer': user_address,
            'withdrawal_root': '0x359d4e37f59466007a6e5246531c6a46b53775266572072df45ec1a18848d9b6',  # noqa: E501
            'strategy': '0xbeaC0eeEeeeeEEeEeEEEEeeEEeEeeeEeeEEBEaC0',
        },
    )]

    tx_hash = deserialize_evm_tx_hash('0xcc0f01a59a1ce8854106f0a901ed0b272467e868b862fe1d104b97ddd5f630ae')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1784217623000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000300333566183211'),
        location_label=user_address,
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRANSFER,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=FVal(amount),
        location_label=user_address,
        notes=f'Withdraw {amount} ETH from Eigenlayer',
        counterparty=CPT_EIGENLAYER,
        address=string_to_evm_address('0x951C0537b78A92E505a96e19d808ddd3ba76Eb44'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=188,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ZERO,
        location_label=user_address,
        notes='Complete eigenlayer withdrawal of ETH',
        counterparty=CPT_EIGENLAYER,
        address=EIGENLAYER_DELEGATION,
        extra_data={'matched': True},
    )]

    with database.conn.read_ctx() as cursor:  # check the queueing event is marked as completed
        events = DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(
                tx_hashes=[queue_tx_hash],
                event_subtypes=[HistoryEventSubType.REMOVE_ASSET],
            ),
        )
    assert events[0].extra_data == {
        'amount': amount,
        'completed': True,
        'withdrawer': user_address,
        'withdrawal_root': '0x359d4e37f59466007a6e5246531c6a46b53775266572072df45ec1a18848d9b6',
        'strategy': '0xbeaC0eeEeeeeEEeEeEEEEeeEEeEeeeEeeEEBEaC0',
    }


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x1DEd04611E3B48F620D42bC97f798cb085403f73']])
def test_complete_withdrawal_token_without_queue_event(ethereum_inquirer, ethereum_accounts):
    """Test completing a token withdrawal whose queueing event is not in the DB.

    This happens when the withdrawal was queued by a transaction not associated with any
    tracked address, for example when the staker got undelegated by the operator. Simulated
    here by decoding only the completion transaction of the queue/complete pair used in
    test_complete_withdrawal_post_slashing_token."""
    tx_hash = deserialize_evm_tx_hash('0x9340fb42391c734caccb46048238ba2579c51e6f8096d2abb6216b509a1c1db6')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1784026463000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000206362625778015'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=446,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=(eigen := Asset(EIGEN_TOKEN_ID)),
        amount=ZERO,
        location_label=user_address,
        notes='Complete eigenlayer withdrawal of EIGEN',
        counterparty=CPT_EIGENLAYER,
        address=EIGENLAYER_DELEGATION,
        extra_data={'matched': True},
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=453,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
        asset=eigen,
        amount=FVal(amount := '60'),
        location_label=user_address,
        notes=f'Withdraw {amount} EIGEN from Eigenlayer',
        counterparty=CPT_EIGENLAYER,
        address=string_to_evm_address('0xaCB55C530Acdb2849e6d4f36992Cd8c9D50ED8F7'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x79f4B334c0e290250Dd5b65799310805FD807F0F']])
def test_complete_withdrawal_eth_without_queue_event(ethereum_inquirer, ethereum_accounts):
    """Test completing a natively restaked ETH withdrawal whose queueing event is not
    in the DB, same as in test_complete_withdrawal_token_without_queue_event. Simulated
    by decoding only the completion transaction of the queue/complete pair used in
    test_complete_withdrawal_post_slashing_eth."""
    tx_hash = deserialize_evm_tx_hash('0xcc0f01a59a1ce8854106f0a901ed0b272467e868b862fe1d104b97ddd5f630ae')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1784217623000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000300333566183211'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRANSFER,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=FVal(amount := '6.24'),
        location_label=user_address,
        notes=f'Withdraw {amount} ETH from Eigenlayer',
        counterparty=CPT_EIGENLAYER,
        address=string_to_evm_address('0x951C0537b78A92E505a96e19d808ddd3ba76Eb44'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=188,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ZERO,
        location_label=user_address,
        notes='Complete eigenlayer withdrawal of ETH',
        counterparty=CPT_EIGENLAYER,
        address=EIGENLAYER_DELEGATION,
        extra_data={'matched': True},
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xCd2bCdE423F36E1B81a25168D5373f908546c9BE', '0xf17606D3FFbd5B07454542146a74712Eb797Ac0a']])  # noqa: E501
def test_claim_delayed_withdrawals(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xc5d38c05567f5a4d51e686225dfc461ddf177eefa7c531822656b2ed9560ab12')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    safe_address = ethereum_accounts[1]
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1716123995000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000369830372847984'),
        location_label=user_address,
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRANSFER,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=FVal(withdrawal_amount := '0.004538247'),
        location_label=safe_address,
        notes=f'Withdraw {withdrawal_amount} ETH from Eigenlayer delayed withdrawals',
        counterparty=CPT_EIGENLAYER,
        address=EIGENPOD_DELAYED_WITHDRAWAL_ROUTER,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=160,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ZERO,
        location_label=user_address,
        notes=f'Successfully executed safe transaction 0xb0eee93e607b22a214518cadddddd4b34be5da2a9c72bd269333b2b82ee214d1 for multisig {safe_address}',  # noqa: E501
        counterparty=CPT_SAFE_MULTISIG,
        address=safe_address,
    )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x78524bEeAc12368e600457478738c233f436e9f6']])
def test_native_restake_delegate(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xd857a09084c1dfc1d2df83cbeed70e99b79b1e3a74c7385df7dc7065a79e184c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    eth_restaked = '160'
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=373,
            timestamp=(timestamp := TimestampMS(1715866679000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=ethereum_accounts[0],
            notes=f'Delegate {eth_restaked} restaked ETH to 0x5dCdf02a7188257b7c37dD3158756dA9Ccd4A9Cb for {ethereum_accounts[0]}',  # noqa: E501
            counterparty=CPT_EIGENLAYER,
            address=EIGENLAYER_DELEGATION,
            extra_data={'amount': '160'},
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=374,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=ethereum_accounts[0],
            notes=f'Restake {eth_restaked} ETH for {ethereum_accounts[0]}',
            counterparty=CPT_EIGENLAYER,
            address=EIGENPOD_MANAGER,
        )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x574c25d8e5fF25377a5D2E319f4ADeAeDD66539a',  # proof submitter
    '0xefF584E8336dA7A23EE32ea19a937b016D69d589']])  # eigenpod owner
def test_eigenpod_start_checkpoint(ethereum_inquirer, ethereum_accounts):
    """Note: The address we track here is the proof submitter of the eigenpod.
    It's not possible to have multiple. By default pod owner is also submitter but
    this can also be changed."""
    add_create_eigenpod_event(
        database=ethereum_inquirer.database,
        eigenpod_owner=ethereum_accounts[1],
        eigenpod_address=(eigenpod_address := string_to_evm_address('0xA6f93249580EC3F08016cD3d4154AADD70aC3C96')),  # noqa: E501
    )
    tx_hash = deserialize_evm_tx_hash('0xc1f4bf3fc591b7bd116fbccff4985425b4823612a052fe6b9553ce664d10f464')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1725469127000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas := '0.000975571949515495'),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=248,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Start an eigenpod checkpoint of 1 validators at beacon blockroot 0xc806c37b64cf6a791bafd7087f464674d2e1b205e27cedca32017f321c34d558',  # noqa: E501
            counterparty=CPT_EIGENLAYER,
            address=eigenpod_address,
        )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x574c25d8e5fF25377a5D2E319f4ADeAeDD66539a',  # proof submitter
    '0xefF584E8336dA7A23EE32ea19a937b016D69d589']])  # eigenpod owner
def test_eigenpod_verify_checkpoint_proofs(ethereum_inquirer, ethereum_accounts):
    add_create_eigenpod_event(
        database=ethereum_inquirer.database,
        eigenpod_owner=(eigenpod_owner := ethereum_accounts[1]),
        eigenpod_address=(eigenpod_address := string_to_evm_address('0xA6f93249580EC3F08016cD3d4154AADD70aC3C96')),  # noqa: E501
    )
    tx_hash = deserialize_evm_tx_hash('0xdf949beee9e8b8e56f2ed294251800edc0af3c48cfd8e0662ebf9f0a49f61db0')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1725469151000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas := '0.001280636519396161'),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=280,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Update validator 425303 restaking balance to 32.008137863',
            counterparty=CPT_EIGENLAYER,
            address=eigenpod_address,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=282,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=eigenpod_owner,
            notes='Restake 0.000074488 ETH for 0xefF584E8336dA7A23EE32ea19a937b016D69d589',
            counterparty=CPT_EIGENLAYER,
            address=EIGENPOD_MANAGER,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=284,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Finalize an eigenpod checkpoint and add 0.000074488 ETH for restaking across all validators',  # noqa: E501
            counterparty=CPT_EIGENLAYER,
            address=eigenpod_address,
        )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x8ccF35F1A937205fe20353DE42cFAdE8f34cE7E1']])
def test_avs_rewards_claim(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x652b479994529e11f1331864739312e643e912a78cf1dca05403aa1d33c4ac46')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1726209683000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000290353368116672'),
        location_label=user_address,
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=126,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=A_WETH,
        amount=FVal(rewards_amount := '0.000010159378047479'),
        location_label=user_address,
        notes=f'Claim {rewards_amount} WETH as AVS restaking reward',
        counterparty=CPT_EIGENLAYER,
        address=REWARDS_COORDINATOR,
    )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xA8aF03ceEB1F63805c09C8497a877cb4788b115d']])
def test_airdrop_claim_s2(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xc939c3ccdb19a4cdc27d00f2010cd45f652e0553efc663ae6050fa2eed74db8a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1726667207000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00109526054949798'),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=154,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.AIRDROP,
        asset=Asset(EIGEN_TOKEN_ID),
        amount=FVal(claim_amount := '4.556109113437771'),
        location_label=ethereum_accounts[0],
        notes=f'Claim {claim_amount} EIGEN from the Eigenlayer airdrop season 2',
        counterparty=CPT_EIGENLAYER,
        address=EIGENLAYER_AIRDROP_S2_DISTRIBUTOR,
        extra_data={AIRDROP_IDENTIFIER_KEY: 'eigen_s2'},
    )]
    assert events == expected_events
