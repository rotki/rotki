from __future__ import annotations

from collections import defaultdict
from http import HTTPStatus
from typing import TYPE_CHECKING, overload

from rotkehlchen.api.result import ApiResult, FailResult, OkResult
from rotkehlchen.balances.manual import (
    ManuallyTrackedBalance,
    add_manually_tracked_balances,
    edit_manually_tracked_balances,
    get_manually_tracked_balances,
    remove_manually_tracked_balances,
)
from rotkehlchen.chain.bitcoin.xpub import XpubManager
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import EthSyncError, InputError, RemoteError, TagConstraintError
from rotkehlchen.serialization.serialize import process_result
from rotkehlchen.types import (
    SUPPORTED_BITCOIN_CHAINS_TYPE,
    SUPPORTED_EVM_CHAINS_TYPE,
    SUPPORTED_EVM_EVMLIKE_CHAINS,
    SUPPORTED_SUBSTRATE_CHAINS_TYPE,
    BTCAddress,
    ChainType,
    ChecksumEvmAddress,
    ListOfBlockchainAddresses,
    SubstrateAddress,
    SupportedBlockchain,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.chain.accounts import SingleBlockchainAccountData
    from rotkehlchen.chain.bitcoin.xpub import XpubData
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.fval import FVal
    from rotkehlchen.rotkehlchen import Rotkehlchen
    from rotkehlchen.types import Asset


class AccountsService:
    def __init__(self, rotkehlchen: Rotkehlchen) -> None:
        self.rotkehlchen = rotkehlchen

    def add_xpub(self, xpub_data: XpubData) -> ApiResult:
        try:
            XpubManager(self.rotkehlchen.chains_aggregator).add_bitcoin_xpub(
                xpub_data=xpub_data,
            )
        except InputError as e:
            return FailResult(str(e), HTTPStatus.BAD_REQUEST, FailureCause.INVALID_INPUT)
        except TagConstraintError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.CONFLICT)
        except RemoteError as e:
            return FailResult(str(e), HTTPStatus.BAD_GATEWAY, e.cause)

        return OkResult(True)

    def delete_xpub(self, xpub_data: XpubData) -> ApiResult:
        try:
            with self.rotkehlchen.data.db.user_write() as cursor:
                XpubManager(self.rotkehlchen.chains_aggregator).delete_bitcoin_xpub(
                    write_cursor=cursor,
                    xpub_data=xpub_data,
                )
        except InputError as e:
            return FailResult(str(e), HTTPStatus.BAD_REQUEST, FailureCause.INVALID_INPUT)

        return OkResult(True)

    def edit_xpub(self, xpub_data: XpubData) -> ApiResult:
        try:
            with self.rotkehlchen.data.db.user_write() as write_cursor:
                XpubManager(self.rotkehlchen.chains_aggregator).edit_bitcoin_xpub(
                    write_cursor=write_cursor,
                    xpub_data=xpub_data,
                )
            with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
                data = self.rotkehlchen.get_blockchain_account_data(
                    cursor,
                    xpub_data.blockchain,
                )
        except InputError as e:
            return FailResult(str(e), HTTPStatus.BAD_REQUEST, FailureCause.INVALID_INPUT)

        return OkResult(data)

    def add_evm_accounts(
            self,
            account_data: list[SingleBlockchainAccountData[ChecksumEvmAddress]],
    ) -> ApiResult:
        try:
            (
                added_accounts,
                existed_accounts,
                failed_accounts,
                no_activity_accounts,
            ) = self.rotkehlchen.add_evm_accounts(account_data=account_data)
        except (EthSyncError, TagConstraintError) as e:
            return FailResult(
                str(e),
                HTTPStatus.CONFLICT,
                FailureCause.NETWORK if isinstance(e, EthSyncError) else FailureCause.CONFLICT,
            )
        except RemoteError as e:
            return FailResult(str(e), HTTPStatus.BAD_GATEWAY, e.cause)

        result_dicts: dict[str, dict[ChecksumEvmAddress, list[str]]] = defaultdict(
            lambda: defaultdict(list),
        )
        all_key = 'all'
        for response_key, list_of_accounts in (
            ('added', added_accounts),
            ('failed', failed_accounts),
            ('existed', existed_accounts),
            ('no_activity', no_activity_accounts),
        ):
            for chain, address in list_of_accounts:
                result_dicts[response_key][address].append(chain.serialize())
                if len(result_dicts[response_key][address]) == len(SUPPORTED_EVM_EVMLIKE_CHAINS):
                    result_dicts[response_key][address] = [all_key]

        return OkResult(result_dicts)

    def refresh_evm_accounts(self) -> ApiResult:
        chains = self.rotkehlchen.data.db.get_chains_to_detect_evm_accounts()
        try:
            self.rotkehlchen.chains_aggregator.detect_evm_accounts(chains=chains)
        except EthSyncError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.NETWORK)
        except RemoteError as e:
            return FailResult(str(e), HTTPStatus.BAD_GATEWAY, e.cause)

        return OkResult(True)

    def get_blockchain_accounts(self, blockchain: SupportedBlockchain) -> ApiResult:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            data = self.rotkehlchen.get_blockchain_account_data(cursor, blockchain)
        return OkResult(data)

    @overload
    def add_single_blockchain_accounts(
            self,
            chain: SUPPORTED_EVM_CHAINS_TYPE,
            account_data: list[SingleBlockchainAccountData[ChecksumEvmAddress]],
    ) -> ApiResult:
        ...

    @overload
    def add_single_blockchain_accounts(
            self,
            chain: SUPPORTED_SUBSTRATE_CHAINS_TYPE,
            account_data: list[SingleBlockchainAccountData[SubstrateAddress]],
    ) -> ApiResult:
        ...

    @overload
    def add_single_blockchain_accounts(
            self,
            chain: SUPPORTED_BITCOIN_CHAINS_TYPE,
            account_data: list[SingleBlockchainAccountData[BTCAddress]],
    ) -> ApiResult:
        ...

    @overload
    def add_single_blockchain_accounts(
            self,
            chain: SupportedBlockchain,
            account_data: list[SingleBlockchainAccountData],
    ) -> ApiResult:
        ...

    def add_single_blockchain_accounts(
            self,
            chain: SupportedBlockchain,
            account_data: list[SingleBlockchainAccountData],
    ) -> ApiResult:
        try:
            self.rotkehlchen.add_single_blockchain_accounts(chain=chain, account_data=account_data)
        except (EthSyncError, TagConstraintError) as e:
            return FailResult(
                str(e),
                HTTPStatus.CONFLICT,
                FailureCause.NETWORK if isinstance(e, EthSyncError) else FailureCause.CONFLICT,
            )
        except InputError as e:
            return FailResult(str(e), HTTPStatus.BAD_REQUEST, FailureCause.INVALID_INPUT)
        except RemoteError as e:
            return FailResult(str(e), HTTPStatus.BAD_GATEWAY, e.cause)

        added_addresses = [x.address for x in account_data]
        return OkResult(added_addresses)

    def edit_single_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            account_data: list[SingleBlockchainAccountData],
    ) -> ApiResult:
        try:
            with self.rotkehlchen.data.db.user_write() as write_cursor:
                self.rotkehlchen.edit_single_blockchain_accounts(
                    write_cursor=write_cursor,
                    blockchain=blockchain,
                    account_data=account_data,
                )
            with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
                data = self.rotkehlchen.get_blockchain_account_data(cursor, blockchain)
        except TagConstraintError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.CONFLICT)
        except InputError as e:
            return FailResult(str(e), HTTPStatus.BAD_REQUEST, FailureCause.INVALID_INPUT)

        return OkResult(data)

    def edit_chain_type_accounts_labels(
            self,
            accounts: list[SingleBlockchainAccountData],
    ) -> ApiResult:
        try:
            with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
                self.rotkehlchen.edit_chain_type_accounts_labels(
                    cursor=cursor,
                    account_data=accounts,
                )
        except TagConstraintError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.CONFLICT)
        except InputError as e:
            return FailResult(str(e), HTTPStatus.BAD_REQUEST, FailureCause.INVALID_INPUT)

        return OkResult(True)

    def remove_single_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
    ) -> ApiResult:
        try:
            self.rotkehlchen.remove_single_blockchain_accounts(
                blockchain=blockchain,
                accounts=accounts,
            )
            balances_update = self.rotkehlchen.chains_aggregator.get_balances_update(
                chain=None,
            )
        except EthSyncError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.NETWORK)
        except InputError as e:
            return FailResult(str(e), HTTPStatus.BAD_REQUEST, FailureCause.INVALID_INPUT)
        except RemoteError as e:
            return FailResult(str(e), HTTPStatus.BAD_GATEWAY, e.cause)

        return OkResult(balances_update.serialize())

    def remove_chain_type_accounts(
            self,
            chain_type: ChainType,
            accounts: ListOfBlockchainAddresses,
    ) -> ApiResult:
        try:
            self.rotkehlchen.remove_chain_type_accounts(
                chain_type=chain_type,
                accounts=accounts,
            )
        except InputError as e:
            return FailResult(str(e), HTTPStatus.BAD_REQUEST, FailureCause.INVALID_INPUT)

        return OkResult(True)

    def _get_manually_tracked_balances(self, value_threshold: FVal | None) -> ApiResult:
        db_entries = get_manually_tracked_balances(
            db=self.rotkehlchen.data.db,
            balance_type=None,
            include_entries_with_missing_assets=True,
        )
        if value_threshold is not None:
            db_entries = [
                entry for entry in db_entries
                if entry.value.value > value_threshold
            ]

        balances = process_result({'balances': db_entries})
        return OkResult(balances)

    def get_manually_tracked_balances(self, value_threshold: FVal | None) -> ApiResult:
        return self._get_manually_tracked_balances(value_threshold=value_threshold)

    @overload
    def _modify_manually_tracked_balances(
            self,
            function: Callable[[DBHandler, list[ManuallyTrackedBalance]], None],
            data_or_ids: list[ManuallyTrackedBalance],
    ) -> ApiResult:
        ...

    @overload
    def _modify_manually_tracked_balances(
            self,
            function: Callable[[DBHandler, list[int]], None],
            data_or_ids: list[int],
    ) -> ApiResult:
        ...

    def _modify_manually_tracked_balances(
            self,
            function: (
                Callable[[DBHandler, list[ManuallyTrackedBalance]], None] |
                Callable[[DBHandler, list[int]], None]
            ),
            data_or_ids: list[ManuallyTrackedBalance] | list[int],
    ) -> ApiResult:
        try:
            function(self.rotkehlchen.data.db, data_or_ids)  # type: ignore[arg-type]
        except InputError as e:
            return FailResult(str(e), HTTPStatus.BAD_REQUEST, FailureCause.INVALID_INPUT)
        except TagConstraintError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.CONFLICT)

        return self._get_manually_tracked_balances(value_threshold=None)

    def add_manually_tracked_balances(
            self,
            data: list[ManuallyTrackedBalance],
    ) -> ApiResult:
        return self._modify_manually_tracked_balances(
            function=add_manually_tracked_balances,
            data_or_ids=data,
        )

    def edit_manually_tracked_balances(
            self,
            data: list[ManuallyTrackedBalance],
    ) -> ApiResult:
        return self._modify_manually_tracked_balances(
            function=edit_manually_tracked_balances,
            data_or_ids=data,
        )

    def remove_manually_tracked_balances(self, ids: list[int]) -> ApiResult:
        return self._modify_manually_tracked_balances(
            function=remove_manually_tracked_balances,
            data_or_ids=ids,
        )

    def get_ignored_assets(self) -> ApiResult:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            result = self.rotkehlchen.data.db.get_ignored_asset_ids(cursor)
        return OkResult(list(result))

    def add_ignored_assets(self, assets_to_ignore: list[Asset]) -> ApiResult:
        newly_ignored, already_ignored = self.rotkehlchen.data.add_ignored_assets(
            assets=assets_to_ignore,
        )
        result = {'successful': list(newly_ignored), 'no_action': list(already_ignored)}
        return OkResult(process_result(result))

    def remove_ignored_assets(self, assets: list[Asset]) -> ApiResult:
        succeeded, no_action = self.rotkehlchen.data.remove_ignored_assets(assets=assets)
        result = {'successful': list(succeeded), 'no_action': list(no_action)}
        return OkResult(process_result(result))

    def get_xpub_balances(self, xpub_data: XpubData, ignore_cache: bool) -> ApiResult:
        try:
            if ignore_cache:
                XpubManager(
                    chains_aggregator=self.rotkehlchen.chains_aggregator,
                ).check_for_new_xpub_addresses(
                    blockchain=xpub_data.blockchain,
                    xpub_data=xpub_data,
                )

            with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
                addresses = self.rotkehlchen.data.db.get_xpub_derived_addresses(
                    cursor=cursor,
                    xpub_data=xpub_data,
                )

            result = self.rotkehlchen.chains_aggregator.query_balances(
                blockchain=xpub_data.blockchain,
                ignore_cache=ignore_cache,
                addresses=addresses,
            ).serialize()
        except RemoteError as e:
            return FailResult(str(e), HTTPStatus.BAD_GATEWAY, e.cause)

        return OkResult(result)
