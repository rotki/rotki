from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.modules.yearn_vesting.balances import (
    YearnVestingBalances,
    remaining_principal,
    vested_at,
)
from rotkehlchen.chain.ethereum.modules.yearn_vesting.cache import parse_creation_log
from rotkehlchen.chain.ethereum.modules.yearn_vesting.constants import (
    CLAIM,
    CPT_YEARN_VESTING,
    ERC4626_VESTING_ESCROW_CREATED,
    FACTORY_DEPLOYMENTS,
    PRINCIPAL_CLAIM,
    REVOKED_V4_TOKEN,
    TOKEN_VESTING_ESCROW_CREATED,
    V4_FACTORY,
    YIELD_CLAIM,
)
from rotkehlchen.chain.ethereum.modules.yearn_vesting.decoder import YearnVestingDecoder
from rotkehlchen.chain.ethereum.modules.yearn_vesting.structures import VestingEscrowData
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import ChainID, EvmTransaction, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder

DAI_ADDRESS = deserialize_evm_address('0x6B175474E89094C44Da98b954EedeAC495271d0F')


def _address_word(address: str) -> bytes:
    return bytes.fromhex('00' * 12 + address.removeprefix('0x'))


def _uint_word(value: int) -> bytes:
    return value.to_bytes(32, byteorder='big')


def _deployment(version: str, kind: str):
    return next(
        deployment for deployment in FACTORY_DEPLOYMENTS
        if deployment.version == version and deployment.kind == kind
    )


def _decode_logs(
        database,
        tx_decoder: EthereumTransactionDecoder,
        from_address: str,
        to_address: str,
        logs: list[EvmTxReceiptLog],
):
    transaction = EvmTransaction(
        tx_hash=(tx_hash := make_evm_tx_hash()),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(0),
        block_number=0,
        from_address=deserialize_evm_address(from_address),
        to_address=deserialize_evm_address(to_address),
        value=0,
        gas=0,
        gas_price=0,
        gas_used=0,
        input_data=b'',
        nonce=0,
    )
    receipt = EvmTxReceipt(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=logs,
    )
    with database.user_write() as cursor:
        DBEvmTx(database).add_transactions(cursor, [transaction], relevant_address=None)

    return tx_decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)


def _register_escrow(
        tx_decoder: EthereumTransactionDecoder,
        position: VestingEscrowData,
) -> None:
    decoder = tx_decoder.decoders['YearnVesting']
    assert isinstance(decoder, YearnVestingDecoder)
    decoder.escrows[position.escrow] = position
    tx_decoder.rules.address_mappings[position.escrow] = (
        decoder._decode_escrow_event,  # pylint: disable=protected-access
        position,
    )
    tx_decoder.rules.addresses_to_counterparties[position.escrow] = CPT_YEARN_VESTING


def test_parse_historical_creation_log() -> None:
    """Parse the first v0.3.0 factory deployment from mainnet block 18,370,588."""
    topics = [
        '0x99fd02dbc65944923f77d3e5d3e77e8c4c1b4026201be5445a8e827183e993e2',
        '0x000000000000000000000000feb4acf3df3cdea7399794d0869ef76a6efaff52',
        '0x0000000000000000000000006b175474e89094c44da98b954eedeac495271d0f',
        '0x000000000000000000000000b1d693b77232d88a3c9467ed5619ffe79e80bccc',
    ]
    data = '0x000000000000000000000000fdd74f49bdfee0af70ffc6a556a2182380b40d320000000000000000000000000000000000000000000003cfc82e37e9a7400000000000000000000000000000000000000000000000000000000000006518a870000000000000000000000000000000000000000000000000000000000076a70000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001'  # noqa: E501

    position = parse_creation_log(
        deployment=_deployment(version='v0.3.0', kind='token'),
        topics=topics,
        data=data,
    )

    assert position == VestingEscrowData(
        escrow=deserialize_evm_address('0xfdd74f49bdfee0af70ffc6a556a2182380b40d32'),
        factory=deserialize_evm_address('0x200C92Dd85730872Ab6A1e7d5E40A067066257cF'),
        version='v0.3.0',
        kind='token',
        token=deserialize_evm_address('0x6b175474e89094c44da98b954eedeac495271d0f'),
        recipient=deserialize_evm_address('0xb1d693b77232d88a3c9467ed5619ffe79e80bccc'),
        funder=deserialize_evm_address('0xfeb4acf3df3cdea7399794d0869ef76a6efaff52'),
        amount=18_000 * 10**18,
        funded_amount=18_000 * 10**18,
        start_time=int('6518a870', 16),
        end_time=int('6518a870', 16) + 7_776_000,
        cliff_length=0,
    )
    assert VestingEscrowData.deserialize(position.serialize()) == position


def test_parse_erc4626_creation_log() -> None:
    escrow = '0x1111111111111111111111111111111111111111'
    vault = '0x2222222222222222222222222222222222222222'
    recipient = '0x3333333333333333333333333333333333333333'
    funder = '0x4444444444444444444444444444444444444444'
    revoker = '0x5555555555555555555555555555555555555555'
    yield_recipient = '0x6666666666666666666666666666666666666666'
    asset = '0x7777777777777777777777777777777777777777'
    data = b''.join((
        _address_word(funder),
        _address_word(revoker),
        _address_word(yield_recipient),
        _address_word(asset),
        _uint_word(90),
        _uint_word(100),
        _uint_word(1_000),
        _uint_word(400),
        _uint_word(50),
        _uint_word(1),
    ))

    position = parse_creation_log(
        deployment=_deployment(version='v0.4.0', kind='erc4626'),
        topics=[
            ERC4626_VESTING_ESCROW_CREATED,
            _address_word(escrow),
            _address_word(vault),
            _address_word(recipient),
        ],
        data=data,
    )

    assert position.escrow == deserialize_evm_address(escrow)
    assert position.token == deserialize_evm_address(vault)
    assert position.recipient == deserialize_evm_address(recipient)
    assert position.funder == deserialize_evm_address(funder)
    assert position.revoker == deserialize_evm_address(revoker)
    assert position.yield_recipient == deserialize_evm_address(yield_recipient)
    assert position.asset_token == deserialize_evm_address(asset)
    assert position.funded_amount == 90
    assert position.amount == 100
    assert position.start_time == 1_000
    assert position.end_time == 1_400
    assert position.cliff_length == 50


def test_parse_creation_log_rejects_malformed_data() -> None:
    with pytest.raises(ValueError, match='Malformed'):
        parse_creation_log(
            deployment=_deployment(version='v0.4.0', kind='token'),
            topics=[b''],
            data=b'',
        )


@pytest.mark.parametrize(('timestamp', 'expected'), [
    (999, 0),
    (1_049, 0),
    (1_050, 12),
    (1_200, 50),
    (1_400, 100),
    (1_500, 100),
])
def test_vested_at(timestamp: int, expected: int) -> None:
    position = VestingEscrowData(
        escrow=deserialize_evm_address('0x1111111111111111111111111111111111111111'),
        factory=deserialize_evm_address('0x2222222222222222222222222222222222222222'),
        version='v0.4.0',
        kind='token',
        token=deserialize_evm_address('0x3333333333333333333333333333333333333333'),
        recipient=deserialize_evm_address('0x4444444444444444444444444444444444444444'),
        funder=deserialize_evm_address('0x5555555555555555555555555555555555555555'),
        amount=100,
        funded_amount=100,
        start_time=1_000,
        end_time=1_400,
        cliff_length=50,
    )
    assert vested_at(position=position, timestamp=timestamp) == expected


@pytest.mark.parametrize(('version', 'disabled_at', 'claimed', 'expected'), [
    ('v0.3.0', 1_400, 20, 80),  # historical active sentinel is end_time
    ('v0.3.0', 1_200, 20, 30),  # historical revoked halfway through
    ('v0.4.0', 0, 20, 80),  # v0.4 active sentinel is zero
    ('v0.4.0', 1_200, 20, 30),  # v0.4 revoked halfway through
    ('v0.4.0', 1_050, 20, 0),  # claims cannot make the remaining balance negative
])
def test_remaining_principal(
        version: str,
        disabled_at: int,
        claimed: int,
        expected: int,
) -> None:
    position = VestingEscrowData(
        escrow=deserialize_evm_address('0x1111111111111111111111111111111111111111'),
        factory=deserialize_evm_address('0x2222222222222222222222222222222222222222'),
        version=version,  # type: ignore[arg-type]
        kind='token',
        token=deserialize_evm_address('0x3333333333333333333333333333333333333333'),
        recipient=deserialize_evm_address('0x4444444444444444444444444444444444444444'),
        funder=deserialize_evm_address('0x5555555555555555555555555555555555555555'),
        amount=100,
        funded_amount=100,
        start_time=1_000,
        end_time=1_400,
        cliff_length=50,
    )
    assert remaining_principal(
        position=position,
        claimed=claimed,
        disabled_at=disabled_at,
    ) == expected


@pytest.mark.parametrize('ethereum_accounts', [[
    '0x1111111111111111111111111111111111111111',
    '0x2222222222222222222222222222222222222222',
]])
def test_decode_factory_funding_and_grant(
        database,
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        ethereum_accounts,
) -> None:
    funder, recipient = ethereum_accounts
    escrow = deserialize_evm_address('0x3333333333333333333333333333333333333333')
    revoker = deserialize_evm_address('0x4444444444444444444444444444444444444444')
    raw_amount = 100 * 10**18
    events, _, reload_decoders = _decode_logs(
        database=database,
        tx_decoder=ethereum_transaction_decoder,
        from_address=funder,
        to_address=V4_FACTORY,
        logs=[
            EvmTxReceiptLog(
                log_index=0,
                data=_uint_word(raw_amount),
                address=DAI_ADDRESS,
                topics=[
                    ERC20_OR_ERC721_TRANSFER,
                    _address_word(funder),
                    _address_word(escrow),
                ],
            ), EvmTxReceiptLog(
                log_index=1,
                data=b''.join((
                    _address_word(funder),
                    _address_word(revoker),
                    _uint_word(raw_amount),
                    _uint_word(1_000),
                    _uint_word(400),
                    _uint_word(50),
                    _uint_word(1),
                )),
                address=V4_FACTORY,
                topics=[
                    TOKEN_VESTING_ESCROW_CREATED,
                    _address_word(escrow),
                    _address_word(DAI_ADDRESS),
                    _address_word(recipient),
                ],
            ),
        ],
    )

    protocol_events = [event for event in events if event.counterparty == CPT_YEARN_VESTING]
    assert len(protocol_events) == 2
    deposit, grant = protocol_events
    assert deposit.event_type == HistoryEventType.DEPOSIT
    assert deposit.event_subtype == HistoryEventSubType.DEPOSIT_TO_PROTOCOL
    assert deposit.asset == A_DAI
    assert deposit.amount == FVal(100)
    assert deposit.location_label == funder
    assert deposit.address == escrow
    assert grant.event_type == HistoryEventType.RECEIVE
    assert grant.event_subtype == HistoryEventSubType.GRANT
    assert grant.asset == A_DAI
    assert grant.amount == FVal(100)
    assert grant.location_label == recipient
    assert grant.address == escrow
    assert reload_decoders == {'YearnVesting'}


@pytest.mark.parametrize(
    'ethereum_accounts',
    [['0x2222222222222222222222222222222222222222']],
)
def test_decode_token_claim(
        database,
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        ethereum_accounts,
) -> None:
    recipient = ethereum_accounts[0]
    escrow = deserialize_evm_address('0x3333333333333333333333333333333333333333')
    raw_amount = 25 * 10**18
    position = VestingEscrowData(
        escrow=escrow,
        factory=V4_FACTORY,
        version='v0.4.0',
        kind='token',
        token=DAI_ADDRESS,
        recipient=recipient,
        funder=deserialize_evm_address('0x1111111111111111111111111111111111111111'),
        amount=100 * 10**18,
        funded_amount=100 * 10**18,
        start_time=1_000,
        end_time=1_400,
        cliff_length=0,
    )
    _register_escrow(tx_decoder=ethereum_transaction_decoder, position=position)

    events, _, _ = _decode_logs(
        database=database,
        tx_decoder=ethereum_transaction_decoder,
        from_address=recipient,
        to_address=escrow,
        logs=[
            EvmTxReceiptLog(
                log_index=0,
                data=_uint_word(raw_amount),
                address=DAI_ADDRESS,
                topics=[
                    ERC20_OR_ERC721_TRANSFER,
                    _address_word(escrow),
                    _address_word(recipient),
                ],
            ), EvmTxReceiptLog(
                log_index=1,
                data=_uint_word(raw_amount),
                address=escrow,
                topics=[CLAIM, _address_word(recipient)],
            ),
        ],
    )

    event = next(event for event in events if event.counterparty == CPT_YEARN_VESTING)
    assert event.event_type == HistoryEventType.WITHDRAWAL
    assert event.event_subtype == HistoryEventSubType.WITHDRAW_FROM_PROTOCOL
    assert event.asset == A_DAI
    assert event.amount == FVal(25)
    assert event.location_label == recipient
    assert event.address == escrow


@pytest.mark.parametrize('ethereum_accounts', [[
    '0x2222222222222222222222222222222222222222',
    '0x3333333333333333333333333333333333333333',
]])
def test_decode_erc4626_principal_and_yield(
        database,
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        ethereum_accounts,
) -> None:
    recipient, yield_recipient = ethereum_accounts
    escrow = deserialize_evm_address('0x4444444444444444444444444444444444444444')
    position = VestingEscrowData(
        escrow=escrow,
        factory=V4_FACTORY,
        version='v0.4.0',
        kind='erc4626',
        token=DAI_ADDRESS,
        recipient=recipient,
        funder=deserialize_evm_address('0x1111111111111111111111111111111111111111'),
        revoker=deserialize_evm_address('0x5555555555555555555555555555555555555555'),
        yield_recipient=yield_recipient,
        asset_token=DAI_ADDRESS,
        amount=100 * 10**18,
        funded_amount=90 * 10**18,
        start_time=1_000,
        end_time=1_400,
        cliff_length=0,
    )
    _register_escrow(tx_decoder=ethereum_transaction_decoder, position=position)
    raw_principal = 25 * 10**18
    raw_principal_shares = 20 * 10**18
    raw_yield_shares = 5 * 10**18

    events, _, _ = _decode_logs(
        database=database,
        tx_decoder=ethereum_transaction_decoder,
        from_address=recipient,
        to_address=escrow,
        logs=[
            EvmTxReceiptLog(
                log_index=0,
                data=_uint_word(raw_principal_shares),
                address=DAI_ADDRESS,
                topics=[
                    ERC20_OR_ERC721_TRANSFER,
                    _address_word(escrow),
                    _address_word(recipient),
                ],
            ), EvmTxReceiptLog(
                log_index=1,
                data=_uint_word(raw_principal) + _uint_word(raw_principal_shares),
                address=escrow,
                topics=[PRINCIPAL_CLAIM, _address_word(recipient)],
            ), EvmTxReceiptLog(
                log_index=2,
                data=_uint_word(raw_yield_shares),
                address=DAI_ADDRESS,
                topics=[
                    ERC20_OR_ERC721_TRANSFER,
                    _address_word(escrow),
                    _address_word(yield_recipient),
                ],
            ), EvmTxReceiptLog(
                log_index=3,
                data=_uint_word(raw_yield_shares),
                address=escrow,
                topics=[YIELD_CLAIM, _address_word(yield_recipient)],
            ),
        ],
    )

    protocol_events = [event for event in events if event.counterparty == CPT_YEARN_VESTING]
    assert len(protocol_events) == 2
    principal, yield_event = protocol_events
    assert principal.event_type == HistoryEventType.WITHDRAWAL
    assert principal.event_subtype == HistoryEventSubType.WITHDRAW_FROM_PROTOCOL
    assert principal.amount == FVal(20)
    assert principal.location_label == recipient
    assert principal.extra_data == {
        'principal_asset': A_DAI.identifier,
        'principal_amount': '25',
    }
    assert yield_event.event_type == HistoryEventType.RECEIVE
    assert yield_event.event_subtype == HistoryEventSubType.INTEREST
    assert yield_event.amount == FVal(5)
    assert yield_event.location_label == yield_recipient


@pytest.mark.parametrize('ethereum_accounts', [[
    '0x2222222222222222222222222222222222222222',
    '0x3333333333333333333333333333333333333333',
]])
def test_decode_revocation_and_clawback(
        database,
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        ethereum_accounts,
) -> None:
    recipient, receiver = ethereum_accounts
    escrow = deserialize_evm_address('0x4444444444444444444444444444444444444444')
    revoker = deserialize_evm_address('0x5555555555555555555555555555555555555555')
    position = VestingEscrowData(
        escrow=escrow,
        factory=V4_FACTORY,
        version='v0.4.0',
        kind='token',
        token=DAI_ADDRESS,
        recipient=recipient,
        funder=deserialize_evm_address('0x1111111111111111111111111111111111111111'),
        revoker=revoker,
        amount=100 * 10**18,
        funded_amount=100 * 10**18,
        start_time=1_000,
        end_time=1_400,
        cliff_length=0,
    )
    _register_escrow(tx_decoder=ethereum_transaction_decoder, position=position)
    raw_unvested = 40 * 10**18

    events, _, _ = _decode_logs(
        database=database,
        tx_decoder=ethereum_transaction_decoder,
        from_address=revoker,
        to_address=escrow,
        logs=[
            EvmTxReceiptLog(
                log_index=0,
                data=_uint_word(raw_unvested),
                address=DAI_ADDRESS,
                topics=[
                    ERC20_OR_ERC721_TRANSFER,
                    _address_word(escrow),
                    _address_word(receiver),
                ],
            ), EvmTxReceiptLog(
                log_index=1,
                data=_uint_word(raw_unvested) + _uint_word(1_200),
                address=escrow,
                topics=[
                    REVOKED_V4_TOKEN,
                    _address_word(recipient),
                    _address_word(revoker),
                    _address_word(receiver),
                ],
            ),
        ],
    )

    protocol_events = [event for event in events if event.counterparty == CPT_YEARN_VESTING]
    assert len(protocol_events) == 2
    withdrawal, clawback = protocol_events
    assert withdrawal.event_type == HistoryEventType.WITHDRAWAL
    assert withdrawal.event_subtype == HistoryEventSubType.WITHDRAW_FROM_PROTOCOL
    assert withdrawal.amount == FVal(40)
    assert withdrawal.location_label == receiver
    assert clawback.event_type == HistoryEventType.SPEND
    assert clawback.event_subtype == HistoryEventSubType.CLAWBACK
    assert clawback.amount == FVal(40)
    assert clawback.location_label == recipient


@pytest.mark.parametrize('ethereum_accounts', [[
    '0x2222222222222222222222222222222222222222',
    '0x3333333333333333333333333333333333333333',
]])
def test_vesting_balances(
        ethereum_inquirer,
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        ethereum_accounts,
) -> None:
    recipient, yield_recipient = ethereum_accounts
    token_position = VestingEscrowData(
        escrow=deserialize_evm_address('0x4444444444444444444444444444444444444444'),
        factory=V4_FACTORY,
        version='v0.4.0',
        kind='token',
        token=DAI_ADDRESS,
        recipient=recipient,
        funder=deserialize_evm_address('0x1111111111111111111111111111111111111111'),
        amount=100 * 10**18,
        funded_amount=100 * 10**18,
        start_time=1_000,
        end_time=1_400,
        cliff_length=0,
    )
    vault_position = VestingEscrowData(
        escrow=deserialize_evm_address('0x5555555555555555555555555555555555555555'),
        factory=V4_FACTORY,
        version='v0.4.0',
        kind='erc4626',
        token=DAI_ADDRESS,
        recipient=recipient,
        funder=deserialize_evm_address('0x1111111111111111111111111111111111111111'),
        yield_recipient=yield_recipient,
        asset_token=DAI_ADDRESS,
        amount=100 * 10**18,
        funded_amount=90 * 10**18,
        start_time=1_000,
        end_time=1_400,
        cliff_length=0,
    )
    with (
        patch.object(ethereum_inquirer, 'ensure_cache_data_is_updated'),
        patch.object(
            ethereum_inquirer,
            'multicall_2',
            side_effect=[
                [
                    (True, _uint_word(20 * 10**18)),  # token claimed
                    (True, _uint_word(0)),  # active v0.4 token escrow
                    (True, _uint_word(25 * 10**18)),  # vault principal claimed
                    (True, _uint_word(1_200)),  # vault revoked halfway through
                ],
                [(True, _uint_word(5 * 10**18))],  # claimable vault yield
            ],
        ),
        patch(
            'rotkehlchen.chain.ethereum.modules.yearn_vesting.balances.'
            'read_yearn_vesting_data_from_cache',
            return_value={
                token_position.escrow: token_position,
                vault_position.escrow: vault_position,
            },
        ),
        patch(
            'rotkehlchen.chain.ethereum.interfaces.balances.'
            'Inquirer.find_main_currency_prices',
            return_value={A_DAI: FVal(1)},
        ),
    ):
        balances = YearnVestingBalances(
            evm_inquirer=ethereum_inquirer,
            tx_decoder=ethereum_transaction_decoder,
        ).query_balances()

    assert balances[recipient].assets[A_DAI][CPT_YEARN_VESTING] == Balance(
        amount=FVal(105),
        value=FVal(105),
    )
    assert balances[yield_recipient].assets[A_DAI][CPT_YEARN_VESTING] == Balance(
        amount=FVal(5),
        value=FVal(5),
    )
