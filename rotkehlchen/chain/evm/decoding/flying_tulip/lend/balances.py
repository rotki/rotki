"""Current Flying Tulip lending positions."""
import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import BalanceSheet
from rotkehlchen.assets.utils import get_or_create_evm_token, token_normalized_value
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.flying_tulip.constants import CPT_FLYING_TULIP
from rotkehlchen.errors.misc import NotERC20Conformant, NotERC721Conformant, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .constants import FLYING_TULIP_LEND_DEPLOYMENTS, LENDING_LENS_ABI, POSITIONS_MANAGER_ABI

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class FlyingTulipLendBalances(ProtocolWithBalance):
    """Query deposited collateral and open debt in the Flying Tulip lending market."""

    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            tx_decoder: EVMTransactionDecoder,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_FLYING_TULIP,
            deposit_event_types={
                (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL),
            },
        )
        self.deployment = FLYING_TULIP_LEND_DEPLOYMENTS[evm_inquirer.chain_id]

    @staticmethod
    def _addresses_at(
            events_by_address: dict[ChecksumEvmAddress, list[EvmEvent]],
            contract: ChecksumEvmAddress,
    ) -> list[ChecksumEvmAddress]:
        """Keep the addresses whose events belong to the given contract.

        Every Flying Tulip product shares one counterparty, so filtering by it
        alone would send ftPUT investors and ftUSD stakers into the lending
        multicalls of a market they never touched.
        """
        return [
            address
            for address, events in events_by_address.items()
            if any(event.address == contract for event in events)
        ]

    def _query_asset_lists(
            self,
            positions_manager: EvmContract,
            addresses: list[ChecksumEvmAddress],
    ) -> tuple[list[tuple[ChecksumEvmAddress, ChecksumEvmAddress]], list[tuple[ChecksumEvmAddress, ChecksumEvmAddress]]]:  # noqa: E501
        """Return the (address, asset) pairs with deposited collateral and with open debt."""
        calls = [
            (
                positions_manager.address,
                positions_manager.encode(method_name=method_name, arguments=[address]),
            )
            for address in addresses
            for method_name in ('userCollateralAssets', 'userDebtAssets')
        ]
        results = self.evm_inquirer.multicall(calls=calls)
        collateral_pairs: list[tuple[ChecksumEvmAddress, ChecksumEvmAddress]] = []
        debt_pairs: list[tuple[ChecksumEvmAddress, ChecksumEvmAddress]] = []
        for address, collateral_result, debt_result in zip(
            addresses,
            results[::2],
            results[1::2],
            strict=True,
        ):
            collateral_pairs.extend(
                (address, asset) for asset in positions_manager.decode(
                    result=collateral_result,
                    method_name='userCollateralAssets',
                    arguments=[address],
                )[0]
            )
            debt_pairs.extend(
                (address, asset) for asset in positions_manager.decode(
                    result=debt_result,
                    method_name='userDebtAssets',
                    arguments=[address],
                )[0]
            )

        return collateral_pairs, debt_pairs

    def query_balances(self, addresses: list[ChecksumEvmAddress]) -> BalancesSheetType:
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        addresses = list(dict.fromkeys(
            self._addresses_at(
                events_by_address=self.addresses_with_activity(
                    location_labels=addresses,
                    event_types={
                        (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL),
                        (HistoryEventType.RECEIVE, HistoryEventSubType.GENERATE_DEBT),
                    },
                ),
                contract=self.deployment.positions_manager,
            ) +
            # Leverage fills move funds inside the protocol, so users whose
            # position was opened engine-side only have informational events.
            self._addresses_at(
                events_by_address=self.addresses_with_activity(
                    location_labels=addresses,
                    event_types={
                        (HistoryEventType.INFORMATIONAL, HistoryEventSubType.NONE),
                    },
                ),
                contract=self.deployment.leverage_engine,
            ) +
            # A deposit made for someone else by an untracked payer leaves the
            # position owner only this discovery event.
            self._addresses_at(
                events_by_address=self.addresses_with_activity(
                    location_labels=addresses,
                    event_types={
                        (HistoryEventType.INFORMATIONAL, HistoryEventSubType.NONE),
                    },
                ),
                contract=self.deployment.positions_manager,
            ),
        ))
        if len(addresses) == 0:
            return balances

        # Built here rather than kept on the instance: a user without a lending
        # position never needs them, and an unused contract is only memory.
        positions_manager = EvmContract(
            address=self.deployment.positions_manager,
            abi=POSITIONS_MANAGER_ABI,
            deployed_block=0,  # not used for calls
        )
        lending_lens = EvmContract(
            address=self.deployment.lending_lens,
            abi=LENDING_LENS_ABI,
            deployed_block=0,  # not used for calls
        )
        try:
            collateral_pairs, debt_pairs = self._query_asset_lists(
                positions_manager=positions_manager,
                addresses=addresses,
            )
            if len(collateral_pairs) + len(debt_pairs) == 0:
                return balances

            results = self.evm_inquirer.multicall(calls=[
                (
                    positions_manager.address,
                    positions_manager.encode(
                        method_name='getBalance',
                        arguments=[address, asset],
                    ),
                )
                for address, asset in collateral_pairs
            ] + [
                (
                    lending_lens.address,
                    lending_lens.encode(method_name='debt', arguments=[address, asset]),
                )
                for address, asset in debt_pairs
            ])
        except (RemoteError, DeserializationError) as e:
            log.error(
                'Failed to query Flying Tulip lending balances on %s due to %s',
                self.evm_inquirer.chain_name,
                e,
            )
            return balances

        collateral_amounts, debt_amounts = [], []
        for idx, ((address, asset_address), result) in enumerate(zip(
            collateral_pairs + debt_pairs,
            results,
            strict=True,
        )):
            is_collateral = idx < len(collateral_pairs)
            try:
                token = get_or_create_evm_token(
                    userdb=self.evm_inquirer.database,
                    evm_address=asset_address,
                    chain_id=self.evm_inquirer.chain_id,
                )
                if is_collateral:
                    avail, hold = positions_manager.decode(
                        result=result,
                        method_name='getBalance',
                        arguments=[address, asset_address],
                    )
                    amount_raw = avail + hold
                else:
                    (amount_raw,) = lending_lens.decode(
                        result=result,
                        method_name='debt',
                        arguments=[address, asset_address],
                    )
            except (DeserializationError, NotERC20Conformant, NotERC721Conformant) as e:
                log.error(
                    'Failed to decode a Flying Tulip lending balance of %s for %s on %s due to %s',
                    asset_address,
                    address,
                    self.evm_inquirer.chain_name,
                    e,
                )
                continue

            if amount_raw == 0:
                continue

            entry = (address, token, token_normalized_value(token_amount=amount_raw, token=token))
            if is_collateral:
                collateral_amounts.append(entry)
            else:
                debt_amounts.append(entry)

        self._add_priced_balances(balances=balances, amounts=collateral_amounts)
        self._add_priced_balances(balances=balances, amounts=debt_amounts, category='liabilities')
        return balances
