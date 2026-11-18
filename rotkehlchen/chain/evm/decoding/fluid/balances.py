import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.accounting.structures.balance import BalanceSheet
from rotkehlchen.assets.utils import asset_normalized_value, get_or_create_evm_token
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS, ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.fluid.constants import (
    CPT_FLUID,
    DEX_RESOLVER_ABI,
    FLUID_DEX_RESOLVERS,
    FLUID_VAULT_FACTORY,
    FLUID_VAULT_RESOLVERS,
    VAULT_RESOLVER_ABI,
)
from rotkehlchen.errors.misc import (
    NotERC20Conformant,
    NotERC721Conformant,
    RemoteError,
    TokenQueryFailed,
)
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset, CryptoAsset, EvmToken
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.fval import FVal
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DEX_SHARE_PRECISION: Final = 10**18


class FluidBalances(ProtocolWithBalance):
    """Query collateral assets and debt liabilities across Fluid Vaults."""

    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            tx_decoder: EVMTransactionDecoder,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_FLUID,
            deposit_event_types={
                (HistoryEventType.MINT, HistoryEventSubType.NFT),
                (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL),
                (HistoryEventType.RECEIVE, HistoryEventSubType.GENERATE_DEBT),
            },
        )
        self.vault_resolver = EvmContract(address=FLUID_VAULT_RESOLVERS[self.evm_inquirer.chain_id], abi=VAULT_RESOLVER_ABI)  # noqa: E501
        self.dex_resolver = EvmContract(address=FLUID_DEX_RESOLVERS[self.evm_inquirer.chain_id], abi=DEX_RESOLVER_ABI)  # noqa: E501

    def _get_active_addresses(
            self,
            addresses: list[ChecksumEvmAddress],
    ) -> list[ChecksumEvmAddress]:
        """Return tracked addresses that minted, funded, borrowed, or received a vault NFT."""
        nft_prefix = f'eip155:{self.evm_inquirer.chain_id.serialize()}/erc721:{FLUID_VAULT_FACTORY}/'  # noqa: E501
        address_set = set(addresses)
        active_addresses: set[ChecksumEvmAddress] = set()
        for user_address, events in self.addresses_with_activity(
            event_types=self.deposit_event_types | {
                (HistoryEventType.RECEIVE, HistoryEventSubType.NONE),
                (HistoryEventType.TRANSFER, HistoryEventSubType.NONE),
            },
            location_labels=addresses,
        ).items():
            for event in events:
                if (
                    (event.event_type, event.event_subtype) in self.deposit_event_types or
                    event.asset.identifier.startswith(nft_prefix)
                ):
                    active_addresses.add(user_address)
                    if (
                        event.event_type == HistoryEventType.TRANSFER and
                        event.address is not None and
                        event.address in address_set
                    ):
                        active_addresses.add(event.address)

        return sorted(active_addresses)

    def _resolve_asset(self, address: ChecksumEvmAddress) -> CryptoAsset | EvmToken | None:
        if address in (ETH_SPECIAL_ADDRESS, ZERO_ADDRESS):
            return self.evm_inquirer.native_token

        try:
            return get_or_create_evm_token(
                userdb=self.evm_inquirer.database,
                evm_address=address,
                chain_id=self.evm_inquirer.chain_id,
                evm_inquirer=self.evm_inquirer,
            )
        except (DeserializationError, NotERC20Conformant, NotERC721Conformant, TokenQueryFailed) as e:  # noqa: E501
            log.error('Failed to resolve Fluid asset %s due to %s', address, e)
            return None

    def _query_positions_and_dex_states(
            self,
            active_addresses: list[ChecksumEvmAddress],
    ) -> tuple[
        list[tuple[ChecksumEvmAddress, Any, Any]],
        dict[ChecksumEvmAddress, tuple[int, int, int, int]],
    ] | None:
        calls = [
            (self.vault_resolver.address, self.vault_resolver.encode('positionsByUser', [user]))
            for user in active_addresses
        ]
        try:
            latest_block = self.evm_inquirer.get_latest_block_number()
            outputs = self.evm_inquirer.multicall(calls=calls, block_identifier=latest_block)
        except (RemoteError, DeserializationError) as e:
            log.error('Failed to query Fluid Vault positions due to %s', e)
            return None

        active_positions: list[tuple[ChecksumEvmAddress, Any, Any]] = []
        dex_addresses: set[ChecksumEvmAddress] = set()
        for user, raw_output in zip(active_addresses, outputs, strict=True):
            try:
                positions, vault_datas = self.vault_resolver.decode(result=raw_output, method_name='positionsByUser', arguments=[user])  # noqa: E501
            except DeserializationError as e:
                log.error('Failed to decode Fluid positions for %s due to %s', user, e)
                continue

            for pos, vault_data in zip(positions, vault_datas, strict=True):
                supply, borrow = pos[9], pos[10]
                if supply == 0 and borrow == 0:
                    continue

                active_positions.append((user, pos, vault_data))
                const_views = vault_data[3]
                if vault_data[1] and supply > 0:
                    dex_addresses.add(const_views[6])
                if vault_data[2] and borrow > 0:
                    dex_addresses.add(const_views[7])

        dex_states: dict[ChecksumEvmAddress, tuple[int, int, int, int]] = {}
        if len(dex_addresses) != 0:
            sorted_dexes = sorted(dex_addresses)
            dex_calls = [
                (self.dex_resolver.address, self.dex_resolver.encode('getDexState', [dex]))
                for dex in sorted_dexes
            ]
            try:
                dex_outputs = self.evm_inquirer.multicall(calls=dex_calls, block_identifier=latest_block)  # noqa: E501
                for dex, raw_dex in zip(sorted_dexes, dex_outputs, strict=True):
                    state = self.dex_resolver.decode(result=raw_dex, method_name='getDexState', arguments=[dex])[0]  # noqa: E501
                    dex_states[dex] = (state[11], state[12], state[13], state[14])
            except (RemoteError, DeserializationError) as e:
                log.error('Failed to query Fluid DEX states due to %s', e)
                return None

        return active_positions, dex_states

    def _accumulate_entries(
            self,
            raw_totals: dict[tuple[ChecksumEvmAddress, ChecksumEvmAddress], int],
            asset_cache: dict[ChecksumEvmAddress, CryptoAsset | EvmToken | None],
    ) -> list[tuple[ChecksumEvmAddress, Asset, FVal]]:
        entries: list[tuple[ChecksumEvmAddress, Asset, FVal]] = []
        for (user, token_addr), raw_amount in raw_totals.items():
            if raw_amount <= 0:
                continue

            if token_addr not in asset_cache:
                asset_cache[token_addr] = self._resolve_asset(token_addr)
            if (asset := asset_cache[token_addr]) is not None:
                entries.append((user, asset, asset_normalized_value(amount=raw_amount, asset=asset)))  # noqa: E501

        return entries

    def query_balances(self, addresses: list[ChecksumEvmAddress]) -> BalancesSheetType:
        """Query Fluid vault collateral and debt balances via VaultResolver and DexResolver."""
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if (
            len(active_addresses := self._get_active_addresses(addresses)) == 0 or
            (queried := self._query_positions_and_dex_states(active_addresses)) is None
        ):
            return balances

        active_positions, dex_states = queried
        raw_assets: dict[tuple[ChecksumEvmAddress, ChecksumEvmAddress], int] = defaultdict(int)
        raw_liabilities: dict[tuple[ChecksumEvmAddress, ChecksumEvmAddress], int] = defaultdict(int)  # noqa: E501
        for user, pos, vault_data in active_positions:
            supply, borrow = pos[9], pos[10]
            is_smart_col, is_smart_debt, const_views = vault_data[1], vault_data[2], vault_data[3]
            for amount, is_smart, dex_addr, (tok0, tok1), raw_map, rate_idx in (
                (supply, is_smart_col, const_views[6], const_views[8], raw_assets, 0),
                (borrow, is_smart_debt, const_views[7], const_views[9], raw_liabilities, 2),
            ):
                if amount <= 0:
                    continue
                if is_smart:
                    rates = dex_states[dex_addr]
                    raw_map[user, tok0] += amount * rates[rate_idx] // DEX_SHARE_PRECISION
                    raw_map[user, tok1] += amount * rates[rate_idx + 1] // DEX_SHARE_PRECISION
                else:
                    raw_map[user, tok0] += amount

        asset_cache: dict[ChecksumEvmAddress, CryptoAsset | EvmToken | None] = {}
        self._add_priced_balances(balances=balances, amounts=self._accumulate_entries(raw_totals=raw_assets, asset_cache=asset_cache), category='assets')  # noqa: E501
        self._add_priced_balances(balances=balances, amounts=self._accumulate_entries(raw_totals=raw_liabilities, asset_cache=asset_cache), category='liabilities')  # noqa: E501
        return balances
