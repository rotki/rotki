import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Final

from rotkehlchen.accounting.structures.balance import BalanceSheet
from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import (
    TokenEncounterInfo,
    get_or_create_evm_token,
    token_normalized_value,
)
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.across.constants import CPT_ACROSS
from rotkehlchen.constants import ONE
from rotkehlchen.errors.misc import NotERC20Conformant, RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import TokenKind

from .constants import ACROSS_LP_TOKEN_UNDERLYING, LP_STAKING

if TYPE_CHECKING:
    from eth_typing.abi import ABI

    from rotkehlchen.assets.asset import Asset, EvmToken
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.fval import FVal
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

ACROSS_LP_STAKING_ABI: Final[ABI] = [{'inputs': [{'name': 'stakedToken', 'type': 'address'}, {'name': 'account', 'type': 'address'}], 'name': 'getUserStake', 'outputs': [{'components': [{'name': 'cumulativeBalance', 'type': 'uint256'}, {'name': 'averageDepositTime', 'type': 'uint256'}, {'name': 'rewardsAccumulatedPerToken', 'type': 'uint256'}, {'name': 'rewardsOutstanding', 'type': 'uint256'}], 'name': '', 'type': 'tuple'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501


class AcrossBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: EthereumInquirer,
            tx_decoder: EthereumTransactionDecoder,
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_ACROSS,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL)},  # noqa: E501
        )

    def _ensure_token_metadata(
            self,
            token: EvmToken,
    ) -> EvmToken:
        """Ensure Across LP tokens have the metadata required by the price inquirer."""
        if token.protocol is not None and token.underlying_tokens is not None:
            return token

        underlying_tokens = token.underlying_tokens
        if underlying_tokens is None:
            if (underlying_address := ACROSS_LP_TOKEN_UNDERLYING.get(token.evm_address)) is None:
                log.error('Could not find the underlying token for Across LP token %s', token)
                return token
            try:
                underlying_token = get_or_create_evm_token(
                    userdb=self.evm_inquirer.database,
                    evm_address=underlying_address,
                    chain_id=token.chain_id,
                    evm_inquirer=self.evm_inquirer,
                    encounter=TokenEncounterInfo(
                        description='Detecting Across LP underlying token',
                        should_notify=False,
                    ),
                )
            except NotERC20Conformant as e:
                log.error(
                    'Failed to add underlying token %s for Across LP token %s due to %s',
                    underlying_address,
                    token,
                    e,
                )
                return token

            underlying_tokens = [UnderlyingToken(
                address=underlying_token.evm_address,
                token_kind=TokenKind.ERC20,
                weight=ONE,
            )]

        return get_or_create_evm_token(
            userdb=self.evm_inquirer.database,
            evm_address=token.evm_address,
            chain_id=token.chain_id,
            protocol=CPT_ACROSS if token.protocol is None else None,
            underlying_tokens=underlying_tokens,
        )

    def query_balances(self, addresses: list[ChecksumEvmAddress]) -> BalancesSheetType:
        """Query Across LP tokens staked in the Across accelerating distributor."""
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if len(addresses_with_deposits := self.addresses_with_deposits(
            location_labels=addresses,
        )) == 0:
            return balances

        staking_contract = EvmContract(
            address=LP_STAKING,
            abi=ACROSS_LP_STAKING_ABI,
            deployed_block=0,
        )
        calls: list[tuple[ChecksumEvmAddress, str]] = []
        call_data: list[tuple[ChecksumEvmAddress, EvmToken]] = []
        seen: set[tuple[ChecksumEvmAddress, Asset]] = set()
        for user_address, events in addresses_with_deposits.items():
            for event in events:
                if (user_address, event.asset) in seen:
                    continue

                seen.add((user_address, event.asset))
                resolved_token = event.asset.resolve_to_evm_token()
                token = self._ensure_token_metadata(token=resolved_token)
                calls.append((
                    LP_STAKING,
                    staking_contract.encode(
                        method_name='getUserStake',
                        arguments=[token.evm_address, user_address],
                    ),
                ))
                call_data.append((user_address, token))

        try:
            results = self.evm_inquirer.multicall(calls=calls)
        except RemoteError as e:
            log.error('Failed to query Across LP staking balances due to %s', e)
            return balances

        entries: list[tuple[ChecksumEvmAddress, Asset, FVal]] = []
        for idx, result in enumerate(results):
            user_address, token = call_data[idx]
            raw_amount = staking_contract.decode(
                result=result,
                method_name='getUserStake',
                arguments=[token.evm_address, user_address],
            )[0][0]
            if raw_amount == 0:
                continue

            entries.append((user_address, token, token_normalized_value(raw_amount, token)))

        self._add_priced_balances(balances=balances, amounts=entries)
        return balances
