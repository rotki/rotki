import logging
from collections import defaultdict
from typing import TYPE_CHECKING

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
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.modules.extrafi.constants import CPT_EXTRAFI
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


class ExtrafiBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            tx_decoder: 'EVMTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_EXTRAFI,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},
        )
        self.extrafi_token = Asset('eip155:10/erc20:0x2dAD3a13ef0C6366220f989157009e501e7938F8')
        self.lending_contract_address = string_to_evm_address('0xBB505c54D71E9e599cB8435b4F0cEEc05fC71cbD')  # noqa: E501
        self.lock_contract_address = string_to_evm_address('0xe0BeC4F45aEF64CeC9dCB9010d4beFfB13e91466')  # noqa: E501

    def query_balances(self) -> 'BalancesSheetType':
        """Query balances of lending pools and extra locking"""
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        address_to_deposits = self.addresses_with_deposits(products=None)
        if len(address_to_deposits) == 0:
            return balances

        for address, events in address_to_deposits.items():
            unique_reserves = [
                event.extra_data['reserve_index']
                for event in events
                if event.extra_data is not None and 'reserve_index' in event.extra_data
            ]
            lending_reserves = self.query_lending_reserves(address, unique_reserves)
            for reserve_token, balance_amount in lending_reserves.items():
                price = Inquirer.find_usd_price(asset=reserve_token)
                balances[address].assets[reserve_token] += Balance(
                    amount=balance_amount,
                    usd_value=balance_amount * price,
                )

        self._query_locked_extra(
            addresses=list(self.addresses_with_deposits(products=[EvmProduct.STAKING]).keys()),
            balances=balances,
        )

        return balances

    def _query_locked_extra(
            self,
            addresses: list['ChecksumEvmAddress'],
            balances: BalancesSheetType,
    ) -> None:
        """Query the EXTRA balance locked in the platform. This method modifies
        the provided balances to include the EXTRA amount.
        """
        staking_contract = EvmContract(
            address=self.lock_contract_address,
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
            staked_amount_raw = staking_contract.decode(
                result=result,
                method_name='lockedBalances',
                arguments=[user_address],
            )
            amount = token_normalized_value_decimals(
                token_amount=staked_amount_raw[0],
                token_decimals=DEFAULT_TOKEN_DECIMALS,
            )
            balances[user_address].assets[self.extrafi_token] += Balance(
                amount=amount,
                usd_value=amount * extrafi_price,
            )

        return None

    def _reserve_idx_to_underlying(
            self,
            reserve_idx: int,
            lending_contract: EvmContract,
    ) -> EvmToken:
        """Query the cache for the underlying token of the queried reserve id.
        If we don't have the mapping in the cache then query the extrafi contract
        to get it and then store the result in the database.
        """
        globaldb = GlobalDBHandler()
        cache_key = (
            CacheType.EXTRAFI_LENDING_RESERVES,
            str(self.evm_inquirer.chain_id.serialize_for_db()),
        )
        with globaldb.conn.read_ctx() as cursor:
            if (underlying_token_address := globaldb_get_unique_cache_value(
                cursor=cursor,
                key_parts=cache_key,  # type: ignore  # mypy doesnt detect the cache being a tuple here
            )) is None:
                underlying_token_address = lending_contract.call(
                    node_inquirer=self.evm_inquirer,
                    method_name='getUnderlyingTokenAddress',
                    arguments=[reserve_idx],
                )

        with globaldb.conn.write_ctx() as write_cursor:
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=cache_key,  # type: ignore  # mypy doesnt detect the cache being a tuple here
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
            address=self.lending_contract_address,
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

        reserve_to_balance: dict[EvmToken, FVal] = {}
        for idx, result in enumerate(raw_balances):
            reserve_token = self._reserve_idx_to_underlying(
                reserve_idx=reserves[idx],
                lending_contract=lending_contract,
            )
            reserve_to_balance[reserve_token] = token_normalized_value(
                token_amount=result[-1],
                token=reserve_token,
            )

        return reserve_to_balance
