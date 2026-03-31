import logging
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING

from solders.pubkey import Pubkey

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import (
    TokenEncounterInfo,
    get_or_create_solana_token,
    token_normalized_value,
)
from rotkehlchen.chain.manager import ChainManagerWithNodesMixin, ChainManagerWithTransactions
from rotkehlchen.chain.solana.utils import deserialize_token_account, lamports_to_sol
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL
from rotkehlchen.constants.assets import A_SOL
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.misc import NotSPLConformant, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SolanaAddress, Timestamp

from .decoding.decoder import SolanaTransactionDecoder
from .decoding.tools import SolanaDecoderTools
from .node_inquirer import SolanaInquirer
from .transactions import SolanaTransactions

if TYPE_CHECKING:
    from rotkehlchen.premium.premium import Premium

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SolanaManager(ChainManagerWithTransactions[SolanaAddress], ChainManagerWithNodesMixin[SolanaInquirer]):  # noqa: E501

    def __init__(
            self,
            node_inquirer: SolanaInquirer,
            premium: 'Premium | None' = None,
    ) -> None:
        super().__init__(node_inquirer=node_inquirer)
        self.database = node_inquirer.database
        self.transactions = SolanaTransactions(
            node_inquirer=self.node_inquirer,
            database=node_inquirer.database,
            helius=node_inquirer.helius,
        )
        self.transactions_decoder = SolanaTransactionDecoder(
            database=node_inquirer.database,
            node_inquirer=self.node_inquirer,
            transactions=self.transactions,
            base_tools=SolanaDecoderTools(
                database=self.database,
                node_inquirer=self.node_inquirer,
            ),
            premium=premium,
        )

    def get_multi_balance(self, accounts: Sequence[SolanaAddress]) -> dict[SolanaAddress, FVal]:
        """Returns a dict with keys being accounts and balances in the chain native token.

        May raise:
        - RemoteError if an external service is queried and there is a problem with its query.
        """
        result = {}
        for account, entry in self.node_inquirer.get_raw_accounts_info(
            pubkeys=[Pubkey.from_string(addr) for addr in accounts],
        ).items():
            if entry.lamports == 0:
                log.debug(f'Found no account entry in balances for solana account {account}. Skipping')  # noqa: E501
                result[account] = ZERO
            else:
                result[account] = lamports_to_sol(entry.lamports)

        return result

    def get_staked_balance(self, account: SolanaAddress) -> FVal:
        """Query the total staked SOL balance for the given account by summing
        all stake accounts where the account is the withdrawer authority.
        May raise RemoteError if there is a problem with querying the external service.
        """
        if not (stake_accounts := self.node_inquirer.get_stake_accounts(owner=account)):
            return ZERO

        total_lamports = sum(sa.lamports for sa in stake_accounts)
        staked_balance = lamports_to_sol(total_lamports)
        log.debug(f'Found {len(stake_accounts)} stake accounts for {account} with total staked balance {staked_balance} SOL')  # noqa: E501
        return staked_balance

    def get_token_balances(self, account: SolanaAddress) -> dict[Asset, FVal]:
        """Query the token balances of the given account.
        May raise RemoteError if there is a problem with querying the external service.
        """
        balances: defaultdict[Asset, FVal] = defaultdict(lambda: ZERO)
        log.debug(f'Querying solana token balances for {account}')
        for account_info in self.node_inquirer.query_token_accounts_by_owner(account=account):
            try:
                token_account_info = deserialize_token_account(account_info.account.data)
            except DeserializationError as e:
                log.error(f'Failed to parse solana token account data for {account} due to {e}')
                continue

            if token_account_info.amount == ZERO:
                log.debug(f'Found solana token {token_account_info.mint} with zero balance for {account}. Skipping.')  # noqa: E501
                continue

            try:
                token = get_or_create_solana_token(
                    userdb=self.database,
                    address=token_account_info.mint,
                    solana_inquirer=self.node_inquirer,
                    encounter=TokenEncounterInfo(should_notify=False),
                )
            except NotSPLConformant as e:
                log.error(f'Failed to create solana token with address {token_account_info.mint} due to {e}')  # noqa: E501
                continue

            # Add to existing balances since there may be multiple ATAs
            # (Associated Token Account) for the same token.
            balances[token] += (amount := token_normalized_value(
                token=token,
                token_amount=token_account_info.amount,
            ))
            log.debug(f'Found {token} token balance for solana account {account} with balance {amount}')  # noqa: E501

        return balances

    def query_balances(
            self,
            addresses: Sequence[SolanaAddress],
    ) -> dict[SolanaAddress, BalanceSheet]:
        """Query the balances of the given addresses.
        May raise RemoteError if there is a problem with querying the external service.
        """
        chain_balances: defaultdict[SolanaAddress, BalanceSheet] = defaultdict(BalanceSheet)
        native_token_price = Inquirer.find_main_currency_price(A_SOL)
        for account, balance in self.get_multi_balance(addresses).items():
            if balance != ZERO:
                chain_balances[account].assets[A_SOL][DEFAULT_BALANCE_LABEL] = Balance(
                    amount=balance,
                    value=balance * native_token_price,
                )

        for account in addresses:
            token_balances = self.get_token_balances(account)
            token_prices = Inquirer.find_main_currency_prices(list(token_balances))
            for token, balance in token_balances.items():
                chain_balances[account].assets[token][DEFAULT_BALANCE_LABEL] = Balance(
                    amount=balance,
                    value=balance * token_prices[token],
                )

            try:
                if (staked_balance := self.get_staked_balance(account)) != ZERO:
                    chain_balances[account].assets[A_SOL]['staking'] = Balance(
                        amount=staked_balance,
                        value=staked_balance * native_token_price,
                    )
            except RemoteError as e:
                log.error(f'Failed to query staked SOL balance for {account} due to {e}')

        return dict(chain_balances)

    def query_transactions(
            self,
            addresses: list[SolanaAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> None:
        """Query the transactions for the given addresses and save them to the DB.
        Only queries new transactions if there are already transactions in the DB.
        May raise RemoteError if there is a problem with querying the external service.
        """
        for address in addresses:
            self.transactions.query_transactions_for_address(address=address)
