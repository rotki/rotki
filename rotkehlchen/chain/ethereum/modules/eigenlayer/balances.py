import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Final

from eth_typing.abi import ABI

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.utils import asset_normalized_value, get_or_create_evm_token
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.ethereum.modules.eigenlayer.utils import get_eigenpods_to_owners_mapping
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.errors.misc import NotERC20Conformant, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Location
from rotkehlchen.utils.misc import ts_now

from .constants import (
    CPT_EIGENLAYER,
)

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


UNDERLYING_BALANCES_ABI: Final[ABI] = [{'inputs': [], 'name': 'underlyingToken', 'outputs': [{'name': '', 'type': 'address'}], 'stateMutability': 'view', 'type': 'function'}, {'inputs': [{'name': 'user', 'type': 'address'}], 'name': 'userUnderlyingView', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _read_underlying_assets(
        evm_inquirer: 'EthereumInquirer',
        strategy_address: ChecksumEvmAddress,
        depositor: ChecksumEvmAddress,
) -> tuple['FVal', 'EvmToken']:
    """
    Query the amount deposited in an eigenlayer strategy and the token of the strategy
    May raise:
    - RemoteError
    - NotERC20Conformant
    """
    contract = EvmContract(
        address=strategy_address,
        abi=UNDERLYING_BALANCES_ABI,
        deployed_block=0,
    )
    deposited_amount_raw = contract.call(
        node_inquirer=evm_inquirer,
        method_name='userUnderlyingView',
        arguments=[depositor],
    )
    underlying_token_address = contract.call(
        node_inquirer=evm_inquirer,
        method_name='underlyingToken',
    )
    token = get_or_create_evm_token(
        userdb=evm_inquirer.database,
        evm_address=underlying_token_address,
        chain_id=evm_inquirer.chain_id,
    )
    amount = asset_normalized_value(
        amount=deposited_amount_raw,
        asset=token,
    )
    return amount, token


class EigenlayerBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            tx_decoder: 'EthereumTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_EIGENLAYER,
            deposit_event_types={(HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET)},
        )
        self.evm_inquirer: EthereumInquirer

    def _query_lst_deposits(self, balances: 'BalancesSheetType') -> 'BalancesSheetType':
        addresses_with_deposits = self.addresses_with_deposits()
        # remap all events into a list that will contain all pairs (depositor, strategy)
        deposits = set()
        for depositor, event_list in addresses_with_deposits.items():
            for event in event_list:
                if event.extra_data is None:
                    continue
                if (strategy := event.extra_data.get('strategy')) is not None:
                    deposits.add((depositor, strategy))

        if len(deposits) == 0:  # user had no related events
            return balances

        for depositor, strategy in deposits:
            try:
                amount, token = _read_underlying_assets(
                    evm_inquirer=self.evm_inquirer,
                    strategy_address=strategy,
                    depositor=depositor,
                )
            except (RemoteError, NotERC20Conformant) as e:
                log.error(
                    f'Failed to query eigenlayer balances for {depositor} due to {e}. Skipping',
                )
                continue

            token_price = Inquirer.find_main_currency_price(token)
            balances[depositor].assets[token][self.counterparty] += Balance(
                amount=amount,
                value=token_price * amount,
            )

        return balances

    def _query_token_pending_withdrawals(self, balances: 'BalancesSheetType') -> 'BalancesSheetType':  # noqa: E501
        """Query any balances that are being withdrawn from Eigenlayer and are on the fly"""
        # First find if there is any completed withdrawals unmatched,
        # as that would lead to double counting of balances
        db_filter = EvmEventFilterQuery.make(
            counterparties=[CPT_EIGENLAYER],
            location=Location.ETHEREUM,
            to_ts=ts_now(),
            event_types=[HistoryEventType.INFORMATIONAL],
            event_subtypes=[HistoryEventSubType.NONE],
        )
        with self.event_db.db.conn.read_ctx() as cursor:
            completed_withdrawal_events = self.event_db.get_history_events_internal(
                cursor=cursor,
                filter_query=db_filter,
            )

        for completed_withdrawal in completed_withdrawal_events:
            if not completed_withdrawal.notes or 'Complete eigenlayer withdrawal' not in completed_withdrawal.notes:  # noqa: E501
                continue  # not a completed withdrawal. Dirty way but we use INFORMATIONAL/NONE for multiple things in eigenlayer. TODO: Maybe improve this?  # noqa: E501

            if completed_withdrawal.extra_data and completed_withdrawal.extra_data.get('matched', False):  # noqa: E501
                continue

            # here we are with a completed withdrawal that has not been matched, so redecode to try and match  # noqa: E501
            self.tx_decoder.decode_transaction_hashes(
                tx_hashes=[completed_withdrawal.tx_ref],
                ignore_cache=True,
            )

        # proceed with the counting of all pending withdrawals as balances
        addresses_with_withdrawals = self.addresses_with_activity(
            event_types={(HistoryEventType.INFORMATIONAL, HistoryEventSubType.REMOVE_ASSET)},
        )
        for address, event_list in addresses_with_withdrawals.items():
            for event in event_list:
                if event.asset == A_ETH:
                    continue  # For native ETH restaking's pending ETH we count from the eigenpod. Doing it here again would double count  # noqa: E501

                if event.extra_data is None:
                    log.error(f'Unexpected eigenlayer withdrawal queueing event {event}. Missing extra data. Skipping')  # noqa: E501
                    continue

                if event.extra_data.get('completed', False):
                    continue

                if (withdrawer := event.extra_data.get('withdrawer')) is None:
                    log.error(f'Unexpected eigenlayer withdrawal queueing event {event}. Missing withdrawer from extra data. Using event sender instead.')  # noqa: E501
                    withdrawer = address

                if (str_amount := event.extra_data.get('amount')) is None:
                    log.error(f'Unexpected eigenlayer withdrawal queueing event {event}. Missing amount from extra data. Skipping.')  # noqa: E501
                    continue

                token_price = Inquirer.find_main_currency_price(event.asset)
                balances[withdrawer].assets[event.asset][self.counterparty] += Balance(
                    amount=(amount := FVal(str_amount)),
                    value=token_price * amount,
                )

        return balances

    def _query_eigenpod_balances(self, balances: 'BalancesSheetType') -> 'BalancesSheetType':
        """Queries the balance of ETH in the eigenpod and in the Delayed Withdrawal router"""
        if len(eigenpod_to_owner := get_eigenpods_to_owners_mapping(self.event_db.db)) == 0:
            return balances

        eth_price = Inquirer.find_main_currency_price(A_ETH)  # now query all eigenpod balances and add it  # noqa: E501
        for eigenpod_address, amount in self.evm_inquirer.get_multi_balance(accounts=list(eigenpod_to_owner.keys())).items():  # noqa: E501
            if amount > ZERO:
                balances[eigenpod_to_owner[eigenpod_address]].assets[A_ETH][self.counterparty] += Balance(  # noqa: E501
                    amount=amount,
                    value=eth_price * amount,
                )

        return balances

    def query_balances(self) -> 'BalancesSheetType':
        """
        Query underlying balances for deposits in eigenlayer. Also for eigenpod
        owners and funds deposited in eigenpods. Also for any pending withdrawals
        of LSTs or other tokens.

        May raise:
        - RemoteError: Querying price of the deposited token
        """
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        balances = self._query_lst_deposits(balances)
        balances = self._query_eigenpod_balances(balances)
        return self._query_token_pending_withdrawals(balances)
