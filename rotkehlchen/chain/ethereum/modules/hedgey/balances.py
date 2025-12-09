from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer

from .constants import (
    CPT_HEDGEY,
    VOTING_TOKEN_LOCKUPS,
    VOTING_TOKEN_LOCKUPS_ABI,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


class HedgeyBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            tx_decoder: 'EthereumTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_HEDGEY,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},  # not used  # noqa: E501
        )
        self.evm_inquirer: EthereumInquirer

    def query_balances(self) -> 'BalancesSheetType':
        """
        Query underlying balances for deposits in eigenlayer. Also for eigenpod
        owners and funds deposited in eigenpods. Also for any pending withdrawals
        of LSTs or other tokens.

        May raise:
        - RemoteError: Querying price of the deposited token
        """
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        addresses_to_events = self.addresses_with_activity(
            event_types={
                (HistoryEventType.RECEIVE, HistoryEventSubType.REWARD),
                (HistoryEventType.INFORMATIONAL, HistoryEventSubType.GOVERNANCE),
            },
        )
        # gather the related tokens per address
        addresses_to_tokens = defaultdict(set)
        for address, events in addresses_to_events.items():
            for event in events:
                addresses_to_tokens[address].add(event.asset.resolve_to_evm_token())

        contract = EvmContract(address=VOTING_TOKEN_LOCKUPS, abi=VOTING_TOKEN_LOCKUPS_ABI)
        args, call_args = [], []
        for address, tokens in addresses_to_tokens.items():
            for token in tokens:
                args.append((address, token))  # to keep the full token in the given order
                call_args.append((address, token.evm_address))

        result = self.evm_inquirer.multicall_specific(
            contract=contract,
            method_name='lockedBalances',
            arguments=call_args,
        )
        main_currency = CachedSettings().main_currency
        for idx, entry in enumerate(result):
            token = args[idx][1]
            balances[args[idx][0]].assets[token][self.counterparty] += Balance(
                amount=(amount := token_normalized_value(token_amount=entry[0], token=token)),
                value=amount * Inquirer.find_price(token, main_currency),
            )
        return balances
