import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE_V3
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.pendle.constants import CPT_PENDLE
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xFd83CCCecef02a334e6A86e7eA8D0aa0F61f1Faf']])
def test_lock_pendle(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xc8b252de1a62daa57d4fe294f371e67550e087fdeffe972261e1acc890d84bd5')  # noqa: E501
    events, decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    user_address, timestamp, gas_amount, approval_amount, out_amount, locked_amount, lock_timestamp = ethereum_accounts[0], TimestampMS(1742478515000), '0.00118595784570676', '11.106239093069566243', '0.003254870108208791', '1110.62390930695662426', 1747267200  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(out_amount),
            location_label=user_address,
            notes=f'Pay {out_amount} ETH as vePendle state broadcast fee',
            counterparty=CPT_PENDLE,
            address=string_to_evm_address('0x4f30A9D41B80ecC5B94306AB4364951AE3170210'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=213,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:1/erc20:0x808507121B80c02388fAd14726482e061B8da827'),
            amount=FVal(locked_amount),
            location_label=user_address,
            notes=f'Lock {locked_amount} PENDLE in voting escrow until {decoder.decoders["Pendle"].timestamp_to_date(lock_timestamp)}',  # noqa: E501
            counterparty=CPT_PENDLE,
            extra_data={'lock_time': 1747267200},
            address=string_to_evm_address('0x4f30A9D41B80ecC5B94306AB4364951AE3170210'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=214,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0x808507121B80c02388fAd14726482e061B8da827'),
            amount=FVal(approval_amount),
            location_label=user_address,
            notes=f'Set PENDLE spending approval of {user_address} by 0x4f30A9D41B80ecC5B94306AB4364951AE3170210 to {approval_amount}',  # noqa: E501
            address=string_to_evm_address('0x4f30A9D41B80ecC5B94306AB4364951AE3170210'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xe0eAa41BdaF0F0126c75bD0a4F07a325dE842dd6']])
def test_unlock_pendle(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x5bbfd3175156e347edb917f02311cbc7723d6f61d5bed532e7cfb947fe5b4d72')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, withdrawn_amount = ethereum_accounts[0], TimestampMS(1742472839000), '0.000059142779024945', '4497.51803084'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=411,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:1/erc20:0x808507121B80c02388fAd14726482e061B8da827'),
            amount=FVal(withdrawn_amount),
            location_label=user_address,
            notes=f'Withdraw {withdrawn_amount} PENDLE from vote escrow',
            counterparty=CPT_PENDLE,
            address=string_to_evm_address('0x4f30A9D41B80ecC5B94306AB4364951AE3170210'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x4aCAeaD5249770F268F18284Ef7e71039DC127Fb']])
def test_buy_pt(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x4374352cb86470cc895b7ad433a5ea6e8c62a7d0016434600fa1446ebaea857b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    user_address, timestamp, gas_amount, approval_amount, out_amount, in_amount, interest_amount = ethereum_accounts[0], TimestampMS(1742355155000), '0.00033753258899598', '50.014942', '5001.535682', '5066.377589', '1.535939'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=230,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c'),
            amount=FVal(approval_amount),
            location_label=user_address,
            notes=f'Set aEthUSDC spending approval of {user_address} by 0x888888888889758F76e7103c6CbF23ABbF58F946 to {approval_amount}',  # noqa: E501
            address=string_to_evm_address('0x888888888889758F76e7103c6CbF23ABbF58F946'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=231,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.INTEREST,
            asset=Asset('eip155:1/erc20:0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c'),
            amount=FVal(interest_amount),
            location_label=user_address,
            notes=f'Receive {interest_amount} aEthUSDC as interest earned from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=233,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:1/erc20:0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c'),
            amount=FVal(out_amount),
            location_label=user_address,
            notes=f'Deposit {out_amount} aEthUSDC to Pendle',
            counterparty=CPT_PENDLE,
            extra_data={'market': '0x8539B41CA14148d1F7400d399723827a80579414'},
            address=string_to_evm_address('0x888888888889758F76e7103c6CbF23ABbF58F946'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=245,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xeA1180804bDBA8aC04E2a4406B11fb7970c474f1'),
            amount=FVal(in_amount),
            location_label=user_address,
            notes=f'Receive {in_amount} PT-aUSDC-26JUN2025 from depositing into Pendle',
            counterparty=CPT_PENDLE,
            address=string_to_evm_address('0x8539B41CA14148d1F7400d399723827a80579414'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xAeF32637DbE2cC1ed4e8b04bE1363bE583724947']])
def test_buy_yt(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x08cb3b86393593946047da9fd672278820815e884b199ed913a9f95fa2280cff')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    user_address, timestamp, gas_amount, out_amount, in_amount = ethereum_accounts[0], TimestampMS(1741190135000), '0.000361416310494255', '0.016', '0.11143761'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal(out_amount),
            location_label=user_address,
            notes=f'Deposit {out_amount} ETH to Pendle',
            counterparty=CPT_PENDLE,
            extra_data={'market': '0x70B70Ac0445C3eF04E314DFdA6caafd825428221'},
            address=string_to_evm_address('0x888888888889758F76e7103c6CbF23ABbF58F946'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=355,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0x1e30afeB27C0544F335f8aa21e0A9599c273823A'),
            amount=FVal(in_amount),
            location_label=user_address,
            notes=f'Receive {in_amount} YT-LBTC-27MAR2025 from depositing into Pendle',
            counterparty=CPT_PENDLE,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xC1466a0a0e2a8BB9304823087643Fec98957a73B']])
def test_sell_yt(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xfde90002b389234406d1f3a600166d9023c12263047007ddc7886ca99e23e15e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    user_address, timestamp, gas_amount, revoke_amount, out_amount, in_amount = ethereum_accounts[0], TimestampMS(1742901911000), '0.00024787188908118', '0', '5.98230108', '0.00114182'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=252,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0x1e30afeB27C0544F335f8aa21e0A9599c273823A'),
            amount=FVal(revoke_amount),
            location_label=user_address,
            notes=f'Revoke YT-LBTC-27MAR2025 spending approval of {user_address} by 0x888888888889758F76e7103c6CbF23ABbF58F946',  # noqa: E501
            address=string_to_evm_address('0x888888888889758F76e7103c6CbF23ABbF58F946'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=254,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0x1e30afeB27C0544F335f8aa21e0A9599c273823A'),
            amount=FVal(out_amount),
            location_label=user_address,
            notes=f'Return {out_amount} YT-LBTC-27MAR2025 to Pendle',
            counterparty=CPT_PENDLE,
            address=string_to_evm_address('0x888888888889758F76e7103c6CbF23ABbF58F946'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=273,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:1/erc20:0x8236a87084f8B84306f72007F36F2618A5634494'),
            amount=FVal(in_amount),
            location_label=user_address,
            notes=f'Withdraw {in_amount} LBTC from Pendle',
            counterparty=CPT_PENDLE,
            address=string_to_evm_address('0xC781c0cC527CB8C351bE3A64c690216c535C6F36'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0xCA9CE67D4E2d19a5aa9C1c3EB5BfDaec71c271C7']])
def test_add_liquidity(base_inquirer, base_accounts):
    tx_hash = deserialize_evm_tx_hash('0x04ca9cb81658c528c2a026d8aa9df5798b473d3a8be8e0215ed3efd444a89456')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_inquirer,
        tx_hash=tx_hash,
    )
    user_address, timestamp, gas_amount, out_amount, in_amount = base_accounts[0], TimestampMS(1743007437000), '0.000000641175932399', '222', '113.156787685931457114'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=797,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:8453/erc20:0x35E5dB674D8e93a03d814FA0ADa70731efe8a4b9'),
            amount=FVal(out_amount),
            location_label=user_address,
            notes=f'Deposit {out_amount} USR in a Pendle pool',
            counterparty=CPT_PENDLE,
            address=string_to_evm_address('0x888888888889758F76e7103c6CbF23ABbF58F946'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=809,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:8453/erc20:0xE15578523937ed7F08E8F7a1Fa8a021E07025a08'),
            amount=FVal(in_amount),
            location_label=user_address,
            notes=f'Receive {in_amount} PENDLE-LPT for depositing in a Pendle pool',
            counterparty=CPT_PENDLE,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xe1685a3D1aE79B7C85829fcCe57D62a02eac61a5']])
def test_swap_using_kyber(ethereum_inquirer, ethereum_accounts):
    """This checks for swaps where the receive event comes after the swap event."""
    tx_hash = deserialize_evm_tx_hash('0xf0c60f4d2a87716bb4f3a7a62ed2d196448fe8435da7413edeaf20120b7d618a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    user_address, timestamp, gas_amount, revoke_amount, out_amount, in_amount = ethereum_accounts[0], TimestampMS(1743012491000), '0.00020274888980646', '0', '6.453525486228687704', '7.457926'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=958,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0xec53bF9167f50cDEB3Ae105f56099aaaB9061F83'),
            amount=FVal(revoke_amount),
            location_label=user_address,
            notes=f'Revoke EIGEN spending approval of {user_address} by 0x888888888889758F76e7103c6CbF23ABbF58F946',  # noqa: E501
            address=string_to_evm_address('0x888888888889758F76e7103c6CbF23ABbF58F946'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=959,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0xec53bF9167f50cDEB3Ae105f56099aaaB9061F83'),
            amount=FVal(out_amount),
            location_label=user_address,
            notes=f'Swap {out_amount} EIGEN in Pendle',
            counterparty=CPT_PENDLE,
            address=string_to_evm_address('0x888888888889758F76e7103c6CbF23ABbF58F946'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=960,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            amount=FVal(in_amount),
            location_label=user_address,
            notes=f'Receive {in_amount} USDC from Pendle swap',
            counterparty=CPT_PENDLE,
            address=string_to_evm_address('0x888888888889758F76e7103c6CbF23ABbF58F946'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x21f2a9b5F420245d86E8Faa753022dA01946B13F']])
def test_swap_using_kyber_2(ethereum_inquirer, ethereum_accounts):
    """This checks for swaps where the receive event comes before the swap event."""
    tx_hash = deserialize_evm_tx_hash('0xe3e3b9467890b233007917900fb7b9282d2c14c3381e1db0de2850523ba24359')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    user_address, timestamp, gas_amount, out_amount, in_amount = ethereum_accounts[0], TimestampMS(1743064667000), '0.00010481829185758', '5.634264087233128405', '0.00424279429101785'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0x58D97B57BB95320F9a05dC918Aef65434969c2B2'),
            amount=FVal(out_amount),
            location_label=user_address,
            notes=f'Swap {out_amount} MORPHO in Pendle',
            counterparty=CPT_PENDLE,
            address=string_to_evm_address('0x888888888889758F76e7103c6CbF23ABbF58F946'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal(in_amount),
            location_label=user_address,
            notes=f'Receive {in_amount} ETH from Pendle swap',
            counterparty=CPT_PENDLE,
            address=string_to_evm_address('0x888888888889758F76e7103c6CbF23ABbF58F946'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xc68Ca8A21AAcF167E234F8d08F5d9d115fae2F8d']])
def test_swap_using_odos(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x55fdb8d8f9b8968904e022798049f5c56103f06854c5575e9c09cee1aa2314f9')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    user_address, timestamp, gas_amount, out_amount, in_amount = ethereum_accounts[0], TimestampMS(1743083231000), '0.000421634677180424', '307.491735', '307.738865329882018479'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            amount=FVal(out_amount),
            location_label=user_address,
            notes=f'Swap {out_amount} USDC in Pendle',
            counterparty=CPT_PENDLE,
            address=string_to_evm_address('0x888888888889758F76e7103c6CbF23ABbF58F946'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0x4c9EDD5852cd905f086C759E8383e09bff1E68B3'),
            amount=FVal(in_amount),
            location_label=user_address,
            notes=f'Receive {in_amount} USDe from Pendle swap',
            counterparty=CPT_PENDLE,
            address=string_to_evm_address('0x888888888889758F76e7103c6CbF23ABbF58F946'),
        ),
    ]
    assert events == expected_events
