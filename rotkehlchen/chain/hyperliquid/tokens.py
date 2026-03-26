import logging
from collections import defaultdict
from collections.abc import Sequence

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.tokens import EvmTokens
from rotkehlchen.chain.evm.types import WeightedNode
from rotkehlchen.chain.structures import EvmTokenDetectionData
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class HyperliquidTokens(EvmTokens):
    """Token manager for Hyperliquid L1 (HyperEVM).

    Overrides get_token_balances because the MyCrypto BalanceScanner contract
    is not deployed on Hyperliquid.  Uses individual balanceOf calls via
    call_contract instead.
    """

    def get_token_balances(
            self,
            address: ChecksumEvmAddress,
            tokens: list[EvmTokenDetectionData],
            call_order: Sequence[WeightedNode] | None,
    ) -> dict[Asset, FVal]:
        """Query ERC-20 token balances via individual balanceOf contract calls.

        May raise:
        - RemoteError if an external service is queried and there is a problem
        """
        log.debug(
            f'Querying {self.evm_inquirer.chain_name} for token balances (individual calls)',
            address=address,
            tokens_num=len(tokens),
        )
        balances: dict[Asset, FVal] = defaultdict(FVal)
        for token in tokens:
            try:
                raw_balance = self.evm_inquirer.call_contract(
                    contract_address=token.address,
                    abi=self.evm_inquirer.contracts.erc20_abi,
                    method_name='balanceOf',
                    arguments=[address],
                    call_order=call_order,
                )
            except RemoteError as e:
                log.error(
                    f'{self.evm_inquirer.chain_name} balanceOf call failed for '
                    f'{token.identifier} at {token.address}: {e}',
                )
                continue

            if raw_balance == 0:
                continue

            normalized_balance = token_normalized_value_decimals(
                token_amount=raw_balance,
                token_decimals=token.decimals,
            )
            log.debug(
                f'Found {self.evm_inquirer.chain_name} {token.identifier} '
                f'token balance for {address} and balance {normalized_balance}',
            )
            balances[Asset(token.identifier)] += normalized_balance

        return balances
