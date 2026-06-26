import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Final

from eth_typing.abi import ABI

from rotkehlchen.accounting.structures.balance import BalanceSheet
from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.across.constants import CPT_ACROSS
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .constants import LP_STAKING

if TYPE_CHECKING:
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
            evm_inquirer: 'EthereumInquirer',
            tx_decoder: 'EthereumTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_ACROSS,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL)},  # noqa: E501
        )

    def query_balances(self) -> 'BalancesSheetType':
        """Query Across LP tokens staked in the Across accelerating distributor."""
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if len(addresses_with_deposits := self.addresses_with_deposits()) == 0:
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
                token = event.asset.resolve_to_evm_token()
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
