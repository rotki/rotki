import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.utils import get_token
from rotkehlchen.chain.arbitrum_one.modules.umami.constants import (
    CPT_UMAMI,
    UMAMI_ASSET_VAULT_ABI,
    UMAMI_MASTERCHEF_ABI,
    UMAMI_STAKING_CONTRACT,
)
from rotkehlchen.chain.arbitrum_one.modules.umami.utils import get_umami_vault_token_price
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.tokens import get_chunk_size_call_order
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.arbitrum_one.decoding.decoder import ArbitrumOneTransactionDecoder
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class UmamiBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: 'ArbitrumOneInquirer',
            tx_decoder: 'ArbitrumOneTransactionDecoder',
    ):
        super().__init__(
            tx_decoder=tx_decoder,
            counterparty=CPT_UMAMI,
            evm_inquirer=evm_inquirer,
            deposit_event_types={
                (HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET),
                (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_FOR_WRAPPED),
            },
        )
        self.umami_masterchef_contract = EvmContract(
            address=UMAMI_STAKING_CONTRACT,
            abi=UMAMI_MASTERCHEF_ABI,
            deployed_block=176053511,
        )

    def query_balances(self) -> 'BalancesSheetType':
        """Query both unstaked and staked balances for Umami vaults.

        For each user address with deposits:
        1. Gets unstaked balances via vault.balanceOf()
        2. Gets staked balances via masterchef.userInfo() for indices 0-3:
           - 0: USDC-WETH vault
           - 1: WETH vault
           - 2: WBTC vault
           - 3: USDC-WBTC vault

        Balances are converted to underlying token amounts using the vault's PPS (price per share).
        """
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if len(addresses_with_deposits := list(self.addresses_with_activity(event_types={
            (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_FOR_WRAPPED),
            (HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET),
        }))) == 0:
            return balances

        vault_tokens = GlobalDBHandler().get_evm_tokens(
            protocol=CPT_UMAMI,
            chain_id=self.evm_inquirer.chain_id,
        )
        gm_vault_addresses = [
            string_to_evm_address('0x959f3807f0Aa7921E18c78B00B2819ba91E52FeF'),
            string_to_evm_address('0x4bCA8D73561aaEee2D3a584b9F4665310de1dD69'),
            string_to_evm_address('0xcd8011AaB161A75058eAb24e0965BAb0b918aF29'),
            string_to_evm_address('0x5f851F67D24419982EcD7b7765deFD64fBb50a97'),
        ]
        chunk_size, call_order = get_chunk_size_call_order(self.evm_inquirer)
        for vault_token in vault_tokens:  # get unstaked balances
            try:
                vault_contract = EvmContract(
                    address=vault_token.evm_address,
                    abi=UMAMI_ASSET_VAULT_ABI,
                    deployed_block=0,
                )

                results = self.evm_inquirer.multicall(
                    calls=[
                        (
                            vault_contract.address,
                            vault_contract.encode(
                                method_name='balanceOf',
                                arguments=[address],
                            ),
                        ) for address in addresses_with_deposits
                    ],
                    call_order=call_order,
                    calls_chunk_size=chunk_size,
                )

                if not results:
                    log.error(f'Failed to query umami vault balances for vault {vault_contract.address}')  # noqa: E501
                    continue

                for idx, result in enumerate(results):
                    user_address = addresses_with_deposits[idx]
                    if (balance := vault_contract.decode(
                        result=result,
                        method_name='balanceOf',
                        arguments=[user_address],
                    )[0]) == 0:
                        continue

                    self._process_vault_balance(
                        balance=balance,
                        balances=balances,
                        vault_token=vault_token,
                        user_address=user_address,
                    )
            except RemoteError as e:
                log.error(f'Failed to query umami balances for vault {vault_token.evm_address}: {e!s}')  # noqa: E501
                continue

        for user_address in addresses_with_deposits:  # get staked balances.
            try:
                results = self.evm_inquirer.multicall(
                    calls=[
                        (
                           self.umami_masterchef_contract.address,
                           self.umami_masterchef_contract.encode(
                               method_name='userInfo',
                               arguments=[idx, user_address],
                           ),
                        ) for idx in range(4)
                    ],
                    call_order=call_order,
                    calls_chunk_size=3,  # etherscan throws an error for >3 chunk size.
                )
                if not results:
                    log.error(f'Failed to query umami vault balances for address {user_address}')
                    continue

                for idx, result in enumerate(results):
                    balance, _ = self.umami_masterchef_contract.decode(
                        result=result,
                        method_name='userInfo',
                        arguments=[idx, user_address],
                    )

                    if balance == 0:
                        continue

                    if (gm_vault_token := get_token(
                            evm_address=(gm_vault_token_address := gm_vault_addresses[idx]),
                            chain_id=self.evm_inquirer.chain_id,
                    )) is None:
                        log.error(f'Missing vault {gm_vault_token_address} from DB, cannot process vault balance. Skipping')  # noqa: E501
                        continue

                    self._process_vault_balance(
                        balance=balance,
                        balances=balances,
                        user_address=user_address,
                        vault_token=gm_vault_token,
                    )
            except RemoteError as e:
                log.error(f'Failed to query umami balances for address {user_address}: {e!s}')
                continue

        return balances

    def _process_vault_balance(
            self,
            balance: int,
            vault_token: 'EvmToken',
            balances: 'BalancesSheetType',
            user_address: 'ChecksumEvmAddress',
    ) -> None:
        """Process vault balance and add to user's balance sheet."""
        if (price := get_umami_vault_token_price(
            inquirer=Inquirer(),
            vault_token=vault_token,
            evm_inquirer=self.evm_inquirer,
        )) == ZERO_PRICE:
            log.error(
                f'Failed to request the USD price of {vault_token.evm_address}. '
                f"Balances of the umami vaults that have this token won't be accurate.",
            )

        amount = token_normalized_value_decimals(
            token_amount=balance,
            token_decimals=vault_token.decimals,
        )
        balances[user_address].assets[vault_token] += Balance(
            amount=amount,
            usd_value=amount * price,
        )
