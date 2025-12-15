import logging
from typing import TYPE_CHECKING, Final

from eth_typing import ABI

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithGauges
from rotkehlchen.chain.ethereum.modules.curve.constants import VOTING_ESCROW
from rotkehlchen.chain.ethereum.utils import normalized_fval_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_CRV
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Location

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent

VOTE_ESCROW_ABI: Final[ABI] = [{'inputs': [{'name': 'arg0', 'type': 'address'}], 'name': 'locked', 'outputs': [{'name': 'amount', 'type': 'int128'}, {'name': 'end', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CurveBalances(ProtocolWithGauges):
    """
    Query balances in legacy Curve gauges.
    LP tokens are already queried by the normal token detection.

    Note: The new curve gauges don't require this class, because they mint a liquid token in return
    """

    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            tx_decoder: 'EthereumTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_CURVE,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},
            gauge_deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},  # noqa: E501
            excluded_addresses=[VOTING_ESCROW],  # exclude the veCRV from the list of interacted contracts  # noqa: E501
        )

    def get_gauge_address(self, event: 'EvmEvent') -> ChecksumEvmAddress | None:
        return event.address

    def query_balances(self) -> 'BalancesSheetType':
        """Query gauge balances and CRV deposited in the veCRV contract"""
        balances = super().query_balances()  # gauge balances
        db_filter = EvmEventFilterQuery.make(
            assets=(A_CRV,),
            counterparties=[self.counterparty],
            type_and_subtype_combinations=self.deposit_event_types,
            location=Location.from_chain_id(self.evm_inquirer.chain_id),
            addresses=[VOTING_ESCROW],
        )
        with self.event_db.db.conn.read_ctx() as cursor:
            events = self.event_db.get_history_events_internal(
                cursor=cursor,
                filter_query=db_filter,
            )

        if len(events) == 0:
            return balances

        unique_depositors: set[ChecksumEvmAddress] = set()
        unique_depositors.update(
            string_to_evm_address(event.location_label) for event in events
            if event.location_label is not None
        )
        self._query_and_save_vecrv_balances(
            addresses=list(unique_depositors),
            balances=balances,
        )
        return balances

    def _query_and_save_vecrv_balances(
            self,
            addresses: list[ChecksumEvmAddress],
            balances: 'BalancesSheetType',
    ) -> None:
        """
        This logic handles CRV deposits into the escrow contract among
        the decoded events. It queries `locked` instead of `balanceOf` to get the
        deposited CRV via multicall.
        """
        if len(addresses) == 0:
            return

        voting_escrow_contract = EvmContract(
            address=VOTING_ESCROW,
            abi=VOTE_ESCROW_ABI,
            deployed_block=0,
        )
        try:
            results = self.evm_inquirer.multicall(
                calls=[(
                    voting_escrow_contract.address,
                    voting_escrow_contract.encode(method_name='locked', arguments=[address]),
                ) for address in addresses],
            )
        except RemoteError as e:
            log.error(f'Failed to query locked CRV balances via multicall due to {e!s}')
            return

        price = Inquirer.find_usd_price(A_CRV)
        for idx, result in enumerate(results):
            address = addresses[idx]
            locked_raw = voting_escrow_contract.decode(
                result=result,
                method_name='locked',
                arguments=[address],
            )[0]
            try:
                if (locked_amount := normalized_fval_value_decimals(
                    amount=locked_raw,
                    decimals=DEFAULT_TOKEN_DECIMALS,
                )) == 0:
                    continue
            except DeserializationError as e:
                log.error(f'Failed to decode locked CRV balances via multicall due to {e!s}')
                return

            balances[address].assets[A_CRV][self.counterparty] += Balance(
                amount=locked_amount,
                usd_value=price * locked_amount,
            )
