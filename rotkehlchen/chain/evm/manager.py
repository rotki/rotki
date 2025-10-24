import logging
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal

from web3.exceptions import BadFunctionCallOutput

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.aggregator import CHAIN_TO_BALANCE_PROTOCOLS
from rotkehlchen.chain.evm.active_management.manager import ActiveManager
from rotkehlchen.chain.evm.decoding.curve.curve_cache import (
    query_curve_data,
)
from rotkehlchen.chain.evm.types import RemoteDataQueryStatus
from rotkehlchen.chain.manager import (
    ChainManagerWithNodesMixin,
    ChainManagerWithTransactions,
    ChainWithEoA,
)
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL, ZERO
from rotkehlchen.errors.misc import EthSyncError, InputError, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress, Price, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.interfaces.balances import ProtocolWithBalance

    from .accounting.aggregator import EVMAccountingAggregator
    from .decoding.decoder import EVMTransactionDecoder
    from .node_inquirer import EvmNodeInquirer
    from .tokens import EvmTokens
    from .transactions import EvmTransactions

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EvmManager(
        ChainManagerWithTransactions[ChecksumEvmAddress],
        ChainManagerWithNodesMixin['EvmNodeInquirer'],
        ChainWithEoA,
):
    """EvmManager defines a basic implementation for EVM chains."""

    def __init__(
            self,
            node_inquirer: 'EvmNodeInquirer',
            transactions: 'EvmTransactions',
            tokens: 'EvmTokens',
            transactions_decoder: 'EVMTransactionDecoder',
            accounting_aggregator: 'EVMAccountingAggregator',
    ) -> None:
        super().__init__(node_inquirer=node_inquirer)
        self.transactions = transactions
        self.tokens = tokens
        self.transactions_decoder = transactions_decoder
        self.accounting_aggregator = accounting_aggregator
        self.active_management = ActiveManager(node_inquirer=node_inquirer)

    def get_historical_balance(
            self,
            address: ChecksumEvmAddress,
            block_number: int,
    ) -> FVal | None:
        """Attempts to get a historical eth balance from the local own node only.
        If there is no node or the node can't query historical balance (not archive) then
        returns None"""
        return self.node_inquirer.get_historical_balance(address, block_number)

    def query_balances(
            self,
            addresses: Sequence[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, BalanceSheet]:
        """Queries all native, token, and protocol balances for the given addresses.

        May raise:
        - RemoteError if an external service such as Etherscan or cryptocompare
        is queried and there is a problem with its query.
        - EthSyncError if querying the token balances through a provided ethereum
        client and the chain is not synced
        """
        return self.query_protocols_with_balance(
            balances=self.query_evm_chain_balances(accounts=addresses),
        )

    def query_transactions(
            self,
            addresses: list[ChecksumEvmAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> None:
        """Queries and saves the transactions for the given addresses in the specified time range.
        May raise:
        - RemoteError if there is a problem with an external query.
        - pysqlcipher3.dbapi2.OperationalError if the SQL query fails due to
        invalid filtering arguments.
        """
        self.transactions.query_chain(
            addresses=addresses,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

    @staticmethod
    def update_balances_after_token_query(
            dsr_proxy_append: bool,
            balance_result: dict[ChecksumEvmAddress, dict[EvmToken, FVal]],
            token_usd_price: dict[EvmToken, Price],
            balances: defaultdict[ChecksumEvmAddress, BalanceSheet],
            balance_label: Literal['address', 'makerdao vault'] = DEFAULT_BALANCE_LABEL,
    ) -> None:
        """Updates the passed balances dict with the provided balances_result and token prices.
        If dsr_proxy_append is True then the balances are appended to the existing ones, otherwise
        existing balances are replaced.
        """
        # Update the per account token balance and usd value
        for account, token_balances in balance_result.items():
            for token, token_balance in token_balances.items():
                balance = Balance(
                    amount=token_balance,
                    usd_value=token_balance * token_usd_price[token],
                )
                protocol = token.protocol or balance_label
                assets_or_liabilities = balances[account].liabilities if token.is_liability() else balances[account].assets  # noqa: E501
                if dsr_proxy_append:
                    assets_or_liabilities[token][protocol] += balance
                else:
                    assets_or_liabilities[token][protocol] = balance

    def query_evm_tokens(
            self,
            accounts: Sequence[ChecksumEvmAddress],
            balances: defaultdict[ChecksumEvmAddress, BalanceSheet],
    ) -> defaultdict[ChecksumEvmAddress, BalanceSheet]:
        """Queries evm token balance via either etherscan or evm node

        Should come here during addition of a new account or querying of all token
        balances.

        May raise:
        - RemoteError if an external service such as Etherscan or cryptocompare
        is queried and there is a problem with its query.
        - EthSyncError if querying the token balances through a provided ethereum
        client and the chain is not synced
        """
        try:
            balance_result, token_usd_price = self.tokens.query_tokens_for_addresses(
                addresses=accounts,
            )
        except BadFunctionCallOutput as e:
            log.error(
                f'Assuming unsynced chain. Got web3 BadFunctionCallOutput '
                f'exception: {e!s}',
            )
            raise EthSyncError(
                f'Tried to use the {self.node_inquirer.blockchain!s} chain of the provided '
                'client to query token balances but the chain is not synced.',
            ) from e

        self.update_balances_after_token_query(
            dsr_proxy_append=False,
            balance_result=balance_result,
            token_usd_price=token_usd_price,
            balances=balances,
        )
        return balances

    def query_evm_chain_balances(
            self,
            accounts: Sequence[ChecksumEvmAddress],
    ) -> defaultdict[ChecksumEvmAddress, BalanceSheet]:
        """Queries all the balances for an evm chain and populates the state

        May raise:
        - RemoteError if an external service such as Etherscan or cryptocompare
        is queried and there is a problem with its query.
        - EthSyncError if querying the token balances through a provided ethereum
        client and the chain is not synced
        """
        chain_balances: defaultdict[ChecksumEvmAddress, BalanceSheet] = defaultdict(BalanceSheet)
        native_token_usd_price = Inquirer.find_usd_price(self.node_inquirer.native_token)
        for account, balance in self.node_inquirer.get_multi_balance(accounts).items():
            if balance != ZERO:  # accounts (e.g. multisigs) can have zero balances
                chain_balances[account].assets[self.node_inquirer.native_token][DEFAULT_BALANCE_LABEL] = Balance(  # noqa: E501
                    amount=balance,
                    usd_value=balance * native_token_usd_price,
                )

        return self.query_evm_tokens(accounts=accounts, balances=chain_balances)

    def query_protocols_with_balance(
            self,
            balances: defaultdict[ChecksumEvmAddress, BalanceSheet],
    ) -> defaultdict[ChecksumEvmAddress, BalanceSheet]:
        """
        Query for balances of protocols in which tokens can be locked without returning a liquid
        version of the locked token. For example staking tokens in an old curve gauge. This balance
        needs to be added to the total balance of the account. Examples of such protocols are
        Legacy Curve gauges in ethereum, Convex and Velodrome.
        """
        for protocol in CHAIN_TO_BALANCE_PROTOCOLS[self.node_inquirer.chain_id]:
            protocol_with_balance: ProtocolWithBalance = protocol(
                evm_inquirer=self.node_inquirer,  # type: ignore  # mypy can't match all possibilities here
                tx_decoder=self.transactions_decoder,  # type: ignore  # mypy can't match all possibilities here
            )
            try:
                protocol_balances = protocol_with_balance.query_balances()
            except RemoteError as e:
                log.error(f'Failed to query balances for {protocol} due to {e}. Skipping')
                continue

            for address, asset_balances in protocol_balances.items():
                balances[address] += asset_balances

        return balances

    def is_safe_proxy_or_eoa(self, address: 'ChecksumEvmAddress') -> bool:
        """Check if an address is a SAFE contract or an EoA"""
        return self.node_inquirer.is_safe_proxy_or_eoa(address)


class CurveManagerMixin:
    """Mixin for EVM chain managers that need to query Curve data"""

    def assure_curve_cache_is_queried_and_decoder_updated(
            self,
            node_inquirer: 'EvmNodeInquirer',
            transactions_decoder: 'EVMTransactionDecoder',
    ) -> None:
        """
        Make sure that information that needs to be queried is queried and if not query it.

        1. Deletes all previous cache values
        2. Queries information about curve pools' addresses, lp tokens and used coins
        3. Saves queried information in the cache in globaldb

        Also updates the curve decoder
        """
        if node_inquirer.ensure_cache_data_is_updated(
            cache_type=CacheType.CURVE_LP_TOKENS,
            query_method=query_curve_data,
            chain_id=node_inquirer.chain_id,
            cache_key_parts=(str(node_inquirer.chain_id.serialize_for_db()),),
        ) != RemoteDataQueryStatus.NEW_DATA:
            return

        try:
            curve_decoder = transactions_decoder.decoders['Curve']
        except KeyError as e:
            raise InputError(
                'Expected to find Curve decoder but it was not loaded. '
                'Please open an issue on github.com/rotki/rotki/issues if you saw this.',
            ) from e
        new_mappings = curve_decoder.reload_data()  # type: ignore  # we know type here
        if new_mappings:
            transactions_decoder.rules.address_mappings.update(new_mappings)
