import logging
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.interfaces.balances import (
    PROTOCOLS_WITH_BALANCES,
    BalancesSheetType,
    ProtocolWithGauges,
)
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.velodrome.constants import VOTING_ESCROW_ABI
from rotkehlchen.chain.evm.tokens import get_chunk_size_call_order
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.base.decoding.decoder import BaseTransactionDecoder
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.optimism.decoding.decoder import OptimismTransactionDecoder
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class VelodromeLikeBalances(ProtocolWithGauges):
    """
    Query balances in Velodrome-like gauges.
    LP tokens are already queried by the normal token detection.
    """

    def __init__(
            self,
            evm_inquirer: 'OptimismInquirer | BaseInquirer',
            tx_decoder: 'OptimismTransactionDecoder | BaseTransactionDecoder',
            protocol_token: 'EvmToken',
            voting_escrow_address: ChecksumEvmAddress,
            counterparty: PROTOCOLS_WITH_BALANCES,
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=counterparty,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},
            gauge_deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},  # noqa: E501
        )
        self.protocol_token = protocol_token
        self.voting_escrow_address = voting_escrow_address

    def get_gauge_address(self, event: 'EvmEvent') -> ChecksumEvmAddress | None:
        return event.address

    def query_balances(self) -> BalancesSheetType:
        balances = super().query_balances()
        if len(addresses_with_deposits := self.addresses_with_deposits(products=None)) == 0:
            return balances

        addresses_to_token_ids = {
            address: [event.extra_data['token_id'] for event in events if event.extra_data is not None]  # noqa: E501
            for address, events in addresses_with_deposits.items()
        }
        voting_escrow_contract = EvmContract(
            address=self.voting_escrow_address,
            abi=VOTING_ESCROW_ABI,
            deployed_block=0,
        )
        chunk_size, call_order = get_chunk_size_call_order(self.evm_inquirer)
        if (price := Inquirer().find_usd_price(self.protocol_token)) == ZERO_PRICE:
            log.error(
                f'Failed to request the USD price of {self.protocol_token.evm_address}. '
                f"{self.counterparty} locked balances value won't be accurate.",
            )

        for user_address, token_ids in addresses_to_token_ids.items():
            if not (results := self.evm_inquirer.multicall(
                calls=[
                    (
                        voting_escrow_contract.address,
                        voting_escrow_contract.encode(method_name='locked', arguments=[token_id]),
                    )
                    for token_id in token_ids
                ],
                call_order=call_order,
                calls_chunk_size=chunk_size,
            )):
                log.error(f'Failed to query {self.counterparty} locked balances for address {user_address}')  # noqa: E501
                continue

            for idx, result in enumerate(results):
                balance, _, _ = voting_escrow_contract.decode(
                    result=result,
                    method_name='locked',
                    arguments=[token_ids[idx]],
                )[0]
                if balance == 0:
                    continue

                balances[user_address].assets[self.protocol_token] += Balance(
                    amount=(amount := token_normalized_value_decimals(
                        token_amount=balance,
                        token_decimals=DEFAULT_TOKEN_DECIMALS,  # both AERO and VELO have 18 decimals  # noqa: E501
                    )),
                    usd_value=amount * price,
                )

        return balances
