import logging
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.utils import get_or_create_evm_token, token_normalized_value_decimals
from rotkehlchen.chain.ethereum.interfaces.balances import (
    PROTOCOLS_WITH_BALANCES,
    BalancesSheetType,
    ProtocolWithGauges,
)
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.velodrome.constants import (
    CL_GAUGE_ABI,
    SLIPSTREAM_NFPM_ADDRESSES,
    VOTING_ESCROW_ABI,
)
from rotkehlchen.chain.evm.tokens import get_rpc_first_chunk_size_call_order
from rotkehlchen.constants import ONE
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import TokenKind

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.base.decoding.decoder import BaseTransactionDecoder
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.optimism.decoding.decoder import OptimismTransactionDecoder
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class VelodromeLikeBalances(ProtocolWithGauges):
    """
    Query balances in Velodrome-like gauges.
    LP tokens are already queried by the normal token detection.
    """

    def __init__(
            self,
            evm_inquirer: OptimismInquirer | BaseInquirer,
            tx_decoder: OptimismTransactionDecoder | BaseTransactionDecoder,
            protocol_token: EvmToken,
            voting_escrow_address: ChecksumEvmAddress,
            counterparty: PROTOCOLS_WITH_BALANCES,
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=counterparty,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL)},  # noqa: E501
            gauge_deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL)},  # noqa: E501
        )
        self.protocol_token = protocol_token
        self.voting_escrow_address = voting_escrow_address

    def get_gauge_address(self, event: EvmEvent) -> ChecksumEvmAddress | None:
        if (
            event.asset == self.protocol_token or
            event.asset.resolve_to_evm_token().token_kind == TokenKind.ERC721
        ):  # locked protocol token and staked CL positions are not queried via balanceOf
            return None

        return event.address

    def _query_cl_gauge_balances(
            self,
            balances: BalancesSheetType,
            addresses: list[ChecksumEvmAddress],
    ) -> None:
        """Add the positions staked in concentrated liquidity gauges as balances of the
        position NFTs, which are priced from their underlying assets."""
        if (nfpm_address := SLIPSTREAM_NFPM_ADDRESSES.get(self.evm_inquirer.chain_id)) is None:
            return

        chunk_size, call_order = get_rpc_first_chunk_size_call_order(self.evm_inquirer)
        entries = []
        for user_address, events in self.addresses_with_gauge_deposits(location_labels=addresses).items():  # noqa: E501
            if len(gauges := sorted({
                event.address for event in events
                if event.address is not None and event.asset.resolve_to_evm_token().token_kind == TokenKind.ERC721  # noqa: E501
            })) == 0:
                continue

            # the abi is what matters for encoding and decoding, so one contract object is enough
            gauge_contract = EvmContract(address=gauges[0], abi=CL_GAUGE_ABI)
            staked_call = gauge_contract.encode(method_name='stakedValues', arguments=[user_address])  # noqa: E501
            try:
                results = self.evm_inquirer.multicall(
                    calls=[(gauge, staked_call) for gauge in gauges],
                    call_order=call_order,
                    calls_chunk_size=chunk_size,
                )
            except RemoteError as e:
                log.error(
                    'Failed to query CL gauge positions',
                    counterparty=self.counterparty,
                    address=user_address,
                    error=str(e),
                )
                continue

            for gauge, result in zip(gauges, results, strict=True):
                for position_id in gauge_contract.decode(result, 'stakedValues', [user_address])[0]:  # noqa: E501
                    entries.append((user_address, get_or_create_evm_token(
                        userdb=self.evm_inquirer.database,
                        evm_address=nfpm_address,
                        chain_id=self.evm_inquirer.chain_id,
                        token_kind=TokenKind.ERC721,
                        collectible_id=str(position_id),
                        protocol=self.counterparty,
                    ), ONE))
                    log.debug(
                        'Found CL position staked in gauge',
                        counterparty=self.counterparty,
                        position_id=position_id,
                        address=user_address,
                        gauge=gauge,
                    )

        self._add_priced_balances(balances=balances, amounts=entries)

    def query_balances(self, addresses: list[ChecksumEvmAddress]) -> BalancesSheetType:
        balances = super().query_balances(addresses=addresses)
        self._query_cl_gauge_balances(balances=balances, addresses=addresses)
        if (
            len(addresses_with_deposits := self.addresses_with_deposits(
                location_labels=addresses,
            )) == 0 or
            len(addresses_to_token_ids := {
                address: list(token_ids_set) for address, events in addresses_with_deposits.items()
                if len(token_ids_set := {event.extra_data['token_id'] for event in events if event.extra_data is not None}) != 0  # noqa: E501
            }) == 0
        ):  # Skip voting escrow balances if there are no deposits with token ids in the extra data
            return balances

        voting_escrow_contract = EvmContract(
            address=self.voting_escrow_address,
            abi=VOTING_ESCROW_ABI,
            deployed_block=0,
        )
        chunk_size, call_order = get_rpc_first_chunk_size_call_order(self.evm_inquirer)
        if (price := Inquirer.find_price(
                from_asset=self.protocol_token,
                to_asset=CachedSettings().main_currency,
        )) == ZERO_PRICE:
            log.error(
                f'Failed to request the price of {self.protocol_token.evm_address}. '
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

                balances[user_address].assets[self.protocol_token][self.counterparty] += Balance(
                    amount=(amount := token_normalized_value_decimals(
                        token_amount=balance,
                        token_decimals=DEFAULT_TOKEN_DECIMALS,  # both AERO and VELO have 18 decimals  # noqa: E501
                    )),
                    value=amount * price,
                )

        return balances
