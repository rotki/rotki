import logging
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING

from ens.ens import ChecksumAddress
from web3.exceptions import BadFunctionCallOutput

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.aggregator import CHAIN_TO_BALANCE_PROTOCOLS
from rotkehlchen.chain.constants import PROXY_BALANCE_PROTOCOL_TEMPLATE
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
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import EthSyncError, InputError, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress, Price, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.interfaces.balances import ProtocolWithBalance
    from rotkehlchen.chain.evm.proxies_inquirer import ProxyType

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
            balance_result: dict[ChecksumEvmAddress, dict[EvmToken, FVal]],
            token_price: dict[EvmToken, Price],
            balances: defaultdict[ChecksumEvmAddress, BalanceSheet],
            proxies_information: dict[ChecksumAddress, tuple['ProxyType', ChecksumAddress]] | None = None,  # noqa: E501
    ) -> None:
        """
        Update the per account token balance and value using the provided
        balances dict with the provided balances_result and token prices.
        proxies_information contains the mappings of proxy addresses to their type and
        owner address. If provided balances are added instead of replaced in the balances
        mapping.
        """
        for account, token_balances in balance_result.items():
            if (is_proxy_balances := proxies_information is not None):
                proxy_type, proxy_owner_address = proxies_information[account]
                protocol = PROXY_BALANCE_PROTOCOL_TEMPLATE.format(
                    type=proxy_type,
                    address=account,
                )
                owner = proxy_owner_address
            else:
                owner, protocol = account, DEFAULT_BALANCE_LABEL

            for token, token_balance in token_balances.items():
                balance = Balance(
                    amount=token_balance,
                    value=token_balance * token_price[token],
                )

                assets_or_liabilities = balances[owner].liabilities if token.is_liability() else balances[owner].assets  # noqa: E501
                if is_proxy_balances:
                    # Querying happens in two stages: wallet balances first, then proxy balances.
                    # We append rather than assign to avoid overwriting a token balance when both
                    # the wallet address and its proxy hold the same asset.
                    assets_or_liabilities[token][protocol] += balance
                else:
                    # for the protocol check if it can be taken from the token itself
                    # before assigning the default balance label
                    assets_or_liabilities[token][token.protocol or protocol] = balance

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
            balance_result, token_price = self.tokens.query_tokens_for_addresses(
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
            balance_result=balance_result,
            token_price=token_price,
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
        native_token_price = Inquirer.find_price(
            from_asset=self.node_inquirer.native_token,
            to_asset=CachedSettings().main_currency,
        )
        for account, balance in self.node_inquirer.get_multi_balance(accounts).items():
            if balance != ZERO:  # accounts (e.g. multisigs) can have zero balances
                chain_balances[account].assets[self.node_inquirer.native_token][DEFAULT_BALANCE_LABEL] = Balance(  # noqa: E501
                    amount=balance,
                    value=balance * native_token_price,
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
