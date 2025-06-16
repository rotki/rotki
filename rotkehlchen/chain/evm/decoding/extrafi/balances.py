import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Final, Literal

from eth_utils import to_checksum_address

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.ethereum.utils import (
    token_normalized_value,
    token_normalized_value_decimals,
)
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.extrafi.constants import (
    CPT_EXTRAFI,
    EXTRAFI_FARMING_CONTRACT,
    EXTRAFI_POOL_CONTRACT,
    VOTE_ESCROW,
)
from rotkehlchen.chain.evm.decoding.extrafi.utils import maybe_query_farm_data
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ExtrafiCommonBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            tx_decoder: 'EVMTransactionDecoder',
            extrafi_token: Asset,
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_EXTRAFI,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},
        )
        self.extrafi_token = extrafi_token

    def query_balances(self) -> 'BalancesSheetType':
        """Query balances of lending pools and extra locking"""
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        address_to_deposits = self.addresses_with_deposits(products=None)
        for address, events in address_to_deposits.items():
            unique_reserves = set()
            farm_positions: set[tuple[int, int]] = set()
            for event in events:
                if event.extra_data is None:
                    continue
                if 'reserve_index' in event.extra_data:
                    unique_reserves.add(event.extra_data['reserve_index'])
                elif 'vault_position' in event.extra_data:
                    farm_positions.add(
                        (event.extra_data['vault_id'], event.extra_data['vault_position']),
                    )

            if len(unique_reserves) != 0:
                lending_reserves = self.query_lending_reserves(address, list(unique_reserves))
                for reserve_token, balance_amount in lending_reserves.items():
                    price = Inquirer.find_usd_price(asset=reserve_token)
                    balances[address].assets[reserve_token][self.counterparty] += Balance(
                        amount=balance_amount,
                        usd_value=balance_amount * price,
                    )

            if len(farm_positions) != 0:
                self._query_farm_positions(
                    address=address,
                    farm_positions=list(farm_positions),
                    balances=balances,
                )

        if len(locked_extra_addresses := list(self.addresses_with_deposits(
            products=[EvmProduct.STAKING],
        ).keys())) != 0:
            self._query_locked_extra(addresses=locked_extra_addresses, balances=balances)

        return balances

    def _query_farm_positions(
            self,
            address: 'ChecksumEvmAddress',
            farm_positions: list[tuple[int, int]],
            balances: BalancesSheetType,
    ) -> None:
        """Query balances for farms on extrafi for the given addresses"""
        farm_contract = EvmContract(
            address=EXTRAFI_FARMING_CONTRACT,
            abi=self.evm_inquirer.contracts.abi('EXTRAFI_FARM'),
            deployed_block=0,  # is not used here
        )
        calls = [(
            farm_contract.address,
            farm_contract.encode(method_name='getVaultPosition', arguments=list(position_info)),
        ) for position_info in farm_positions]

        try:
            results = self.evm_inquirer.multicall(calls=calls)
        except RemoteError as e:
            log.error(f'Failed to query {self.evm_inquirer.chain_name} extrafi locked balances due to {e!s}')  # noqa: E501
            return

        for idx, result in enumerate(results):
            staked_amount_raw = farm_contract.decode(
                result=result,
                method_name='getVaultPosition',
                arguments=list(farm_positions[idx]),
            )[0]

            debt_0_amount = staked_amount_raw[13]
            debt_1_amount = staked_amount_raw[14]
            if (lp_amount_raw := staked_amount_raw[12]) == 0:
                continue

            lp_token, token_0, token_1 = maybe_query_farm_data(
                vault_id=farm_positions[idx][0],
                farm_contract=farm_contract,
                evm_inquirer=self.evm_inquirer,
            )

            lp_amount = token_normalized_value(lp_amount_raw, lp_token)
            lp_price = Inquirer.find_usd_price(lp_token)
            balances[address].assets[lp_token][self.counterparty] += Balance(
                amount=lp_amount,
                usd_value=lp_amount * lp_price,
            )

            for debt_token, debt_amount in ((token_0, debt_0_amount), (token_1, debt_1_amount)):
                if debt_amount == 0:
                    continue

                amount = token_normalized_value(debt_amount, debt_token)
                price = Inquirer.find_usd_price(debt_token)
                balances[address].liabilities[debt_token][self.counterparty] += Balance(
                    amount=amount,
                    usd_value=amount * price,
                )

    def _query_locked_extra(
            self,
            addresses: list['ChecksumEvmAddress'],
            balances: BalancesSheetType,
    ) -> None:
        """Query the EXTRA balance locked in the platform for the given address. This
        method modifies the provided balances to include the EXTRA amount.
        """
        staking_contract = EvmContract(
            address=VOTE_ESCROW,
            abi=self.evm_inquirer.contracts.abi('EXTRAFI_LOCK'),
            deployed_block=0,  # is not used here
        )
        calls = [
            (
                staking_contract.address,
                staking_contract.encode(method_name='lockedBalances', arguments=[user_address]),
            )
            for user_address in addresses
        ]

        try:
            results = self.evm_inquirer.multicall(calls=calls)
        except RemoteError as e:
            log.error(f'Failed to query {self.evm_inquirer.chain_name} extrafi locked balances due to {e!s}')  # noqa: E501
            return

        extrafi_price = Inquirer.find_usd_price(self.extrafi_token)
        for idx, result in enumerate(results):
            user_address = addresses[idx]
            if (staked_amount_raw := staking_contract.decode(
                result=result,
                method_name='lockedBalances',
                arguments=[user_address],
            )[0]) == 0:
                continue

            amount = token_normalized_value_decimals(
                token_amount=staked_amount_raw,
                token_decimals=DEFAULT_TOKEN_DECIMALS,
            )
            balances[user_address].assets[self.extrafi_token][self.counterparty] += Balance(
                amount=amount,
                usd_value=amount * extrafi_price,
            )

    def _maybe_query_reserve_idx_to_underlying(
            self,
            reserve_idx: int,
            lending_contract: EvmContract,
    ) -> EvmToken:
        """Query the cache for the underlying token of the queried reserve id.
        If we don't have the mapping in the cache then query the extrafi contract
        to get it and then store the result in the database.

        May raise RemoteError
        """
        globaldb = GlobalDBHandler()
        cache_key: Final[tuple[Literal[CacheType.EXTRAFI_LENDING_RESERVES], str, str]] = (
            CacheType.EXTRAFI_LENDING_RESERVES,
            str(self.evm_inquirer.chain_id.serialize_for_db()),
            str(reserve_idx),
        )
        with globaldb.conn.read_ctx() as cursor:
            if (underlying_token_address := globaldb_get_unique_cache_value(
                cursor=cursor,
                key_parts=cache_key,
            )) is None:
                underlying_token_address = lending_contract.call(
                    node_inquirer=self.evm_inquirer,
                    method_name='getUnderlyingTokenAddress',
                    arguments=[reserve_idx],
                )

                with globaldb.conn.write_ctx() as write_cursor:
                    globaldb_set_unique_cache_value(
                        write_cursor=write_cursor,
                        key_parts=cache_key,
                        value=to_checksum_address(underlying_token_address),
                    )

        return get_or_create_evm_token(
            userdb=self.evm_inquirer.database,
            evm_address=string_to_evm_address(underlying_token_address),
            chain_id=self.evm_inquirer.chain_id,
        )

    def query_lending_reserves(
            self,
            address: 'ChecksumEvmAddress',
            reserves: list[int],
    ) -> dict[EvmToken, FVal]:
        """Query the balances on the given reserves ids for a single address.
        Returns a mapping of token to its balance.
        """
        lending_contract = EvmContract(
            address=EXTRAFI_POOL_CONTRACT,
            abi=self.evm_inquirer.contracts.abi('EXTRAFI_LENDING'),
            deployed_block=96265067,
        )

        try:
            raw_balances = lending_contract.call(
                node_inquirer=self.evm_inquirer,
                method_name='getPositionStatus',
                arguments=[reserves, address],
            )
        except RemoteError:
            log.error(
                f'Failed to query {self.evm_inquirer.chain_name} extrafi lending reserves for '
                f'{address} with reserves {reserves=}. Skipping',
            )
            return {}

        reserve_to_balance: dict[EvmToken, FVal] = defaultdict(FVal)
        for idx, result in enumerate(raw_balances):
            if result[-1] <= 0:
                continue

            try:
                reserve_token = self._maybe_query_reserve_idx_to_underlying(
                    reserve_idx=reserves[idx],
                    lending_contract=lending_contract,
                )
            except RemoteError as e:
                log.error(
                    f'Failed to query reserve {reserves[idx]} for extrafi at '
                    f'{self.evm_inquirer.chain_id} for {address}. {e}',
                )
                continue

            reserve_to_balance[reserve_token] += token_normalized_value(
                token_amount=result[-1],
                token=reserve_token,
            )

        return reserve_to_balance
