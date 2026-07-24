import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import BalanceSheet
from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType

from .cache import query_yearn_vesting_data, read_yearn_vesting_data_from_cache
from .constants import CPT_YEARN_VESTING, ERC4626_ESCROW_ABI, TOKEN_ESCROW_ABI

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.fval import FVal
    from rotkehlchen.types import ChecksumEvmAddress

    from .structures import VestingEscrowData

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def vested_at(position: VestingEscrowData, timestamp: int) -> int:
    if timestamp < position.start_time + position.cliff_length:
        return 0
    if timestamp >= position.end_time:
        return position.amount
    return (
        position.amount *
        (timestamp - position.start_time) //
        (position.end_time - position.start_time)
    )


def remaining_principal(
        position: VestingEscrowData,
        claimed: int,
        disabled_at: int,
) -> int:
    active_disabled_value = position.end_time if position.version != 'v0.4.0' else 0
    vesting_end = position.end_time if disabled_at == active_disabled_value else disabled_at
    return max(vested_at(position=position, timestamp=vesting_end) - claimed, 0)


class YearnVestingBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: EthereumInquirer,
            tx_decoder: EthereumTransactionDecoder,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_YEARN_VESTING,
            deposit_event_types={
                (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL),
            },
        )
        self.evm_inquirer: EthereumInquirer

    def _query_principal(
            self,
            positions: list[VestingEscrowData],
            balances: BalancesSheetType,
    ) -> None:
        calls: list[tuple[ChecksumEvmAddress, str]] = []
        contracts = []
        for position in positions:
            abi = TOKEN_ESCROW_ABI if position.kind == 'token' else ERC4626_ESCROW_ABI
            contract = EvmContract(address=position.escrow, abi=abi)
            claimed_method = (
                'total_claimed'
                if position.kind == 'token'
                else 'claimed_principal_assets'
            )
            contracts.append((position, contract, claimed_method))
            calls.extend((
                (position.escrow, contract.encode(method_name=claimed_method)),
                (position.escrow, contract.encode(method_name='disabled_at')),
            ))

        try:
            results = self.evm_inquirer.multicall_2(require_success=False, calls=calls)
        except RemoteError as e:
            log.error('Failed to query Yearn vesting principal balances due to %s', e)
            return

        amounts: list[tuple[ChecksumEvmAddress, EvmToken, FVal]] = []
        for idx, (position, contract, claimed_method) in enumerate(contracts):
            claimed_success, claimed_result = results[idx * 2]
            disabled_success, disabled_result = results[idx * 2 + 1]
            if claimed_success is False or disabled_success is False:
                log.error('Failed to query Yearn vesting escrow %s', position.escrow)
                continue

            claimed = contract.decode(
                result=claimed_result,
                method_name=claimed_method,
            )[0]
            disabled_at = contract.decode(
                result=disabled_result,
                method_name='disabled_at',
            )[0]
            remaining = remaining_principal(
                position=position,
                claimed=claimed,
                disabled_at=disabled_at,
            )
            if remaining == 0:
                continue

            token_address = (
                position.token
                if position.kind == 'token'
                else position.asset_token
            )
            if token_address is None:
                log.error('Missing asset token for Yearn vesting escrow %s', position.escrow)
                continue

            token = self.tx_decoder.base.get_or_create_evm_token(token_address)
            amounts.append((
                position.recipient,
                token,
                token_normalized_value(token_amount=remaining, token=token),
            ))

        self._add_priced_balances(balances=balances, amounts=amounts)

    def _query_yield(
            self,
            positions: list[VestingEscrowData],
            balances: BalancesSheetType,
    ) -> None:
        contracts = [
            (position, EvmContract(address=position.escrow, abi=ERC4626_ESCROW_ABI))
            for position in positions
        ]
        try:
            results = self.evm_inquirer.multicall_2(
                require_success=False,
                calls=[(
                    position.escrow,
                    contract.encode(method_name='claimable_yield_shares'),
                ) for position, contract in contracts],
            )
        except RemoteError as e:
            log.error('Failed to query Yearn vesting yield balances due to %s', e)
            return

        amounts: list[tuple[ChecksumEvmAddress, EvmToken, FVal]] = []
        for idx, (position, contract) in enumerate(contracts):
            success, result = results[idx]
            if success is False or position.yield_recipient is None:
                continue
            raw_amount = contract.decode(
                result=result,
                method_name='claimable_yield_shares',
            )[0]
            if raw_amount == 0:
                continue

            vault_token = self.tx_decoder.base.get_or_create_evm_token(position.token)
            amounts.append((
                position.yield_recipient,
                vault_token,
                token_normalized_value(token_amount=raw_amount, token=vault_token),
            ))

        self._add_priced_balances(balances=balances, amounts=amounts)

    def query_balances(self) -> BalancesSheetType:
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        self.evm_inquirer.ensure_cache_data_is_updated(
            cache_type=CacheType.YEARN_VESTING_ESCROWS,
            query_method=query_yearn_vesting_data,
        )
        positions = list(read_yearn_vesting_data_from_cache().values())
        recipient_positions = [
            position for position in positions
            if self.tx_decoder.base.is_tracked(position.recipient)
        ]
        yield_positions = [
            position for position in positions
            if (
                position.kind == 'erc4626' and
                position.yield_recipient is not None and
                self.tx_decoder.base.is_tracked(position.yield_recipient)
            )
        ]
        if len(recipient_positions) != 0:
            self._query_principal(positions=recipient_positions, balances=balances)
        if len(yield_positions) != 0:
            self._query_yield(positions=yield_positions, balances=balances)
        return balances
