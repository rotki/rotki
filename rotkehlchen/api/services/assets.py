from __future__ import annotations

import tempfile
from collections import defaultdict
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from zipfile import BadZipFile, ZipFile

from flask import Response, make_response, send_file
from marshmallow.exceptions import ValidationError
from web3.exceptions import BadFunctionCallOutput

from rotkehlchen.accounting.constants import (
    ACCOUNTING_EVENTS_ICONS,
    EVENT_CATEGORY_DETAILS,
    EVENT_CATEGORY_MAPPINGS,
)
from rotkehlchen.accounting.entry_type_mappings import ENTRY_TYPE_MAPPINGS
from rotkehlchen.api.rest_helpers.downloads import register_post_download_cleanup
from rotkehlchen.assets.asset import (
    Asset,
    AssetWithNameAndType,
    AssetWithOracles,
    CustomAsset,
    EvmToken,
)
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.types import ASSET_TYPES_EXCLUDED_FOR_USERS, AssetType
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.airdrops import fetch_airdrops_metadata
from rotkehlchen.chain.ethereum.defi.protocols import DEFI_PROTOCOLS
from rotkehlchen.chain.ethereum.modules.convex.convex_cache import query_convex_data
from rotkehlchen.chain.ethereum.modules.makerdao.cache import (
    query_ilk_registry_and_maybe_update_cache,
)
from rotkehlchen.chain.ethereum.modules.yearn.utils import query_yearn_vaults
from rotkehlchen.chain.ethereum.utils import try_download_ens_avatar
from rotkehlchen.chain.evm.decoding.balancer.balancer_cache import (
    query_balancer_data,
)
from rotkehlchen.chain.evm.decoding.curve.curve_cache import (
    query_curve_data,
)
from rotkehlchen.chain.evm.decoding.gearbox.gearbox_cache import (
    query_gearbox_data,
)
from rotkehlchen.chain.evm.decoding.velodrome.velodrome_cache import (
    query_velodrome_like_data,
)
from rotkehlchen.chain.evm.types import ChainID, RemoteDataQueryStatus
from rotkehlchen.constants.location_details import LOCATION_DETAILS
from rotkehlchen.constants.misc import AVATARIMAGESDIR_NAME, IMAGESDIR_NAME
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.timing import ENS_AVATARS_REFRESH
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.custom_assets import DBCustomAssets
from rotkehlchen.db.ens import DBEns
from rotkehlchen.db.search_assets import search_assets_levenshtein
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import EthSyncError, InputError, NotERC20Conformant, RemoteError
from rotkehlchen.exchanges.constants import ALL_SUPPORTED_EXCHANGES
from rotkehlchen.globaldb.assets_management import export_assets_from_file, import_assets_from_file
from rotkehlchen.globaldb.cache import (
    globaldb_delete_general_cache_values,
    globaldb_get_general_cache_values,
    globaldb_set_general_cache_values,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.globaldb.utils import set_token_spam_protocol
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.types import NOT_EXPOSED_SOURCES, HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.icons import check_if_image_is_cached, maybe_create_image_response
from rotkehlchen.inquirer import CurrentPriceOracle, Inquirer
from rotkehlchen.serialization.serialize import process_result, process_result_list
from rotkehlchen.tasks.assets import (
    update_aave_v3_underlying_assets,
    update_spark_underlying_assets,
)
from rotkehlchen.types import (
    SPAM_PROTOCOL,
    CacheType,
    Price,
    ProtocolsWithCache,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from rotkehlchen.chain.ethereum.modules.nft.structures import NftLpHandling
    from rotkehlchen.chain.evm.manager import EvmManager
    from rotkehlchen.db.filtering import (
        AssetsFilterQuery,
        CounterpartyAssetMappingsFilterQuery,
        CustomAssetsFilterQuery,
        LevenshteinFilterQuery,
        LocationAssetMappingsFilterQuery,
        NFTFilterQuery,
    )
    from rotkehlchen.rotkehlchen import Rotkehlchen
    from rotkehlchen.types import (
        SUPPORTED_CHAIN_IDS,
        ChecksumEvmAddress,
        CounterpartyAssetMappingDeleteEntry,
        CounterpartyAssetMappingUpdateEntry,
        LocationAssetMappingDeleteEntry,
        LocationAssetMappingUpdateEntry,
        ModuleName,
    )


class AssetsService:
    def __init__(self, rotkehlchen: Rotkehlchen) -> None:
        self.rotkehlchen = rotkehlchen

    def _eth_module_query(
            self,
            module_name: ModuleName,
            method: str,
            query_specific_balances_before: list[str] | None,
            **kwargs: Any,
    ) -> dict[str, Any]:
        """A function abstracting away calls to ethereum modules."""
        result = None
        msg = ''
        status_code = HTTPStatus.OK

        if query_specific_balances_before and 'defi' in query_specific_balances_before:
            try:
                self.rotkehlchen.chains_aggregator.query_balances(
                    blockchain=SupportedBlockchain.ETHEREUM,
                )
            except (RemoteError, EthSyncError) as e:
                return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        module_obj = self.rotkehlchen.chains_aggregator.get_module(module_name)
        if module_obj is None:
            return {
                'result': None,
                'status_code': HTTPStatus.CONFLICT,
                'message': f'{module_name} module is not activated',
            }

        try:
            result = getattr(module_obj, method)(**kwargs)
        except RemoteError as e:
            msg = str(e)
            status_code = HTTPStatus.BAD_GATEWAY
        except InputError as e:
            msg = str(e)
            status_code = HTTPStatus.CONFLICT

        return {'result': result, 'message': msg, 'status_code': status_code}

    def query_list_of_all_assets(self, filter_query: AssetsFilterQuery) -> dict[str, Any]:
        assets, assets_found = GlobalDBHandler.retrieve_assets(
            userdb=self.rotkehlchen.data.db,
            filter_query=filter_query,
        )
        with GlobalDBHandler().conn.read_ctx() as cursor:
            assets_total = self.rotkehlchen.data.db.get_entries_count(
                cursor=cursor,
                entries_table='assets',
            )

        result = {
            'entries': assets,
            'entries_found': assets_found,
            'entries_total': assets_total,
            'entries_limit': -1,
        }
        return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}

    def get_assets_mappings(self, identifiers: list[str]) -> dict[str, Any]:
        try:
            asset_mappings, asset_collections = GlobalDBHandler.get_assets_mappings(identifiers)
            nft_mappings = self.rotkehlchen.data.db.get_nft_mappings(identifiers)
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_REQUEST}

        data_dict = {
            'assets': asset_mappings | nft_mappings,
            'asset_collections': asset_collections,
        }
        return {'result': data_dict, 'message': '', 'status_code': HTTPStatus.OK}

    def search_assets(self, filter_query: AssetsFilterQuery) -> dict[str, Any]:
        result = GlobalDBHandler.search_assets(
            db=self.rotkehlchen.data.db,
            filter_query=filter_query,
        )
        return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}

    def search_assets_levenshtein(
            self,
            filter_query: LevenshteinFilterQuery,
            limit: int | None,
            search_nfts: bool,
    ) -> dict[str, Any]:
        result = search_assets_levenshtein(
            db=self.rotkehlchen.data.db,
            filter_query=filter_query,
            limit=limit,
            search_nfts=search_nfts,
        )
        return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}

    def query_owned_assets(self) -> dict[str, Any]:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            result = process_result_list(self.rotkehlchen.data.db.query_owned_assets(cursor))
        return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}

    def get_asset_types(self) -> dict[str, Any]:
        types = [str(x) for x in AssetType if x not in ASSET_TYPES_EXCLUDED_FOR_USERS]
        return {'result': types, 'message': '', 'status_code': HTTPStatus.OK}

    def add_user_asset(self, asset: AssetWithOracles) -> dict[str, Any]:
        if isinstance(asset, EvmToken):
            try:
                asset.check_existence()
                identifiers = [asset.identifier]
            except UnknownAsset:
                identifiers = None
        else:
            identifiers = GlobalDBHandler.check_asset_exists(asset)

        if identifiers is not None:
            return {
                'result': None,
                'message': (
                    f'Failed to add {asset.asset_type!s} {asset.name} '
                    f'since it already exists. Existing ids: {",".join(identifiers)}'
                ),
                'status_code': HTTPStatus.CONFLICT,
            }
        try:
            GlobalDBHandler.add_asset(asset)
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        with self.rotkehlchen.data.db.user_write() as cursor:
            self.rotkehlchen.data.db.add_asset_identifiers(cursor, [asset.identifier])
        return {
            'result': {'identifier': asset.identifier},
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def edit_user_asset(self, asset: AssetWithOracles) -> dict[str, Any]:
        try:
            GlobalDBHandler.edit_user_asset(asset)
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        AssetResolver().assets_cache.remove(asset.identifier)
        self.rotkehlchen.icon_manager.failed_asset_ids.remove(asset.identifier)
        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def delete_asset(self, identifier: str) -> dict[str, Any]:
        try:
            with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
                self.rotkehlchen.data.db.update_owned_assets_in_globaldb(cursor)
            with self.rotkehlchen.data.db.user_write() as write_cursor:
                self.rotkehlchen.data.db.delete_asset_identifier(write_cursor, identifier)

            GlobalDBHandler.delete_asset_by_identifier(identifier)
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        AssetResolver().assets_cache.remove(identifier)
        self.rotkehlchen.icon_manager.failed_asset_ids.remove(identifier)
        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def replace_asset(self, source_identifier: str, target_asset: Asset) -> dict[str, Any]:
        try:
            self.rotkehlchen.data.db.replace_asset_identifier(source_identifier, target_asset)
        except (UnknownAsset, InputError) as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        AssetResolver().assets_cache.remove(source_identifier)
        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def get_custom_assets(self, filter_query: CustomAssetsFilterQuery) -> dict[str, Any]:
        db_custom_assets = DBCustomAssets(db_handler=self.rotkehlchen.data.db)
        custom_assets_result, entries_found, entries_total = db_custom_assets.get_custom_assets_and_limit_info(  # noqa: E501
            filter_query=filter_query,
        )
        entries = [entry.to_dict(export_with_type=False) for entry in custom_assets_result]
        result = {
            'entries': entries,
            'entries_found': entries_found,
            'entries_total': entries_total,
        }
        return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}

    def add_custom_asset(self, custom_asset: CustomAsset) -> dict[str, Any]:
        db_custom_assets = DBCustomAssets(db_handler=self.rotkehlchen.data.db)
        try:
            identifier = db_custom_assets.add_custom_asset(custom_asset=custom_asset)
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}
        return {'result': identifier, 'message': '', 'status_code': HTTPStatus.OK}

    def edit_custom_asset(self, custom_asset: CustomAsset) -> dict[str, Any]:
        db_custom_assets = DBCustomAssets(db_handler=self.rotkehlchen.data.db)
        try:
            db_custom_assets.edit_custom_asset(custom_asset=custom_asset)
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        AssetResolver().assets_cache.remove(custom_asset.identifier)
        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def get_custom_asset_types(self) -> dict[str, Any]:
        db_custom_assets = DBCustomAssets(db_handler=self.rotkehlchen.data.db)
        custom_asset_types = db_custom_assets.get_custom_asset_types()
        return {'result': custom_asset_types, 'message': '', 'status_code': HTTPStatus.OK}

    def export_user_assets(self, path: Path | None) -> dict[str, Any]:
        try:
            zip_path = export_assets_from_file(
                dirpath=path,
                db_handler=self.rotkehlchen.data.db,
            )
        except PermissionError as e:
            return {
                'result': None,
                'message': f'Failed to create asset export file. {e!s}',
                'status_code': HTTPStatus.INSUFFICIENT_STORAGE,
            }

        if path is None:
            # For web case, return the file path for later download
            return {
                'result': {'file_path': str(zip_path)},
                'message': '',
                'status_code': HTTPStatus.OK,
            }

        return {
            'result': True,
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def download_user_assets(self, file_path: str) -> Response:
        register_post_download_cleanup(path := Path(file_path))
        return send_file(
            path_or_file=file_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=path.name,
        )

    def import_user_assets(self, path: Path) -> dict[str, Any]:
        try:
            if path.suffix == '.json':
                import_assets_from_file(
                    path=path,
                    msg_aggregator=self.rotkehlchen.msg_aggregator,
                    db_handler=self.rotkehlchen.data.db,
                )
            else:
                try:
                    zip_file = ZipFile(path)
                except BadZipFile as e:
                    raise ValidationError('Provided file could not be unzipped') from e

                if 'assets.json' not in zip_file.namelist():
                    raise ValidationError(
                        'assets.json could not be found in the provided zip file.',
                    )

                with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tempdir:
                    zip_file.extract('assets.json', tempdir)
                    import_assets_from_file(
                        path=Path(tempdir) / 'assets.json',
                        msg_aggregator=self.rotkehlchen.msg_aggregator,
                        db_handler=self.rotkehlchen.data.db,
                    )
        except ValidationError as e:
            return {
                'result': None,
                'message': f'Provided file does not have the expected format. {e!s}',
                'status_code': HTTPStatus.CONFLICT,
            }
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def upload_asset_icon(self, asset: Asset, filepath: Path) -> dict[str, Any]:
        self.rotkehlchen.icon_manager.add_icon(asset=asset, icon_path=filepath)
        return {
            'result': {'identifier': asset.identifier},
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def refresh_asset_icon(self, asset: AssetWithOracles) -> dict[str, Any]:
        self.rotkehlchen.icon_manager.delete_icon(asset)
        try:
            is_success = self.rotkehlchen.icon_manager.query_coingecko_for_icon(
                asset=asset,
                coingecko_id=asset.to_coingecko(),
            )
        except UnsupportedAsset:
            is_success = False

        if is_success is False:
            return {
                'result': None,
                'message': f'Unable to refresh icon for {asset} at the moment',
                'status_code': HTTPStatus.NOT_FOUND,
            }
        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def get_ens_avatar(self, ens_name: str, match_header: str | None) -> Response:
        avatars_dir = self.rotkehlchen.data_dir / IMAGESDIR_NAME / AVATARIMAGESDIR_NAME
        avatar_path = avatars_dir / f'{ens_name}.png'
        if avatar_path.is_file():
            response = check_if_image_is_cached(image_path=avatar_path, match_header=match_header)
            if response is not None:
                return response

        dbens = DBEns(self.rotkehlchen.data.db)
        try:
            last_update = dbens.get_last_avatar_update(ens_name)
        except InputError:
            return make_response(
                (
                    b'',
                    HTTPStatus.CONFLICT,
                    {'mimetype': 'image/png', 'Content-Type': 'image/png'},
                ),
            )

        if ts_now() - last_update > ENS_AVATARS_REFRESH:
            try:
                nft_module = self.rotkehlchen.chains_aggregator.get_module('nfts')
                try_download_ens_avatar(
                    eth_inquirer=self.rotkehlchen.chains_aggregator.ethereum.node_inquirer,
                    opensea=nft_module.opensea if nft_module is not None else None,
                    avatars_dir=avatars_dir,
                    ens_name=ens_name,
                )
            except RemoteError:
                return make_response(
                    (
                        b'',
                        HTTPStatus.CONFLICT,
                        {'mimetype': 'image/png', 'Content-Type': 'image/png'},
                    ),
                )

        return maybe_create_image_response(image_path=avatar_path)

    def clear_icons_cache(self, icons: list[AssetWithNameAndType] | None) -> dict[str, Any]:
        icons_dir = self.rotkehlchen.icon_manager.icons_dir
        if icons is None:
            for entry in icons_dir.iterdir():
                if entry.is_file():
                    entry.unlink()

            return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

        for icon in icons:
            self.rotkehlchen.icon_manager.delete_icon(icon)

        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def clear_avatars_cache(self, avatars: list[str] | None) -> dict[str, Any]:
        avatars_dir = self.rotkehlchen.data_dir / IMAGESDIR_NAME / AVATARIMAGESDIR_NAME
        if avatars is None:
            for entry in avatars_dir.iterdir():
                if entry.is_file():
                    entry.unlink()

            with self.rotkehlchen.data.db.user_write() as delete_cursor:
                delete_cursor.execute(
                    'UPDATE ens_mappings SET last_avatar_update=?',
                    (Timestamp(0),),
                )

            return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

        avatars_to_delete = [avatars_dir / f'{avatar_name}.png' for avatar_name in avatars]
        for avatar in avatars_to_delete:
            if avatar.is_file():
                avatar.unlink()

        with self.rotkehlchen.data.db.user_write() as delete_cursor:
            delete_cursor.executemany(
                'UPDATE ens_mappings SET last_avatar_update=? WHERE ens_name=?',
                [(Timestamp(0), avatar_name) for avatar_name in avatars],
            )

        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def get_current_assets_price(
            self,
            assets: list[AssetWithNameAndType],
            target_asset: Asset,
            ignore_cache: bool,
    ) -> dict[str, Any]:
        assets_price: dict[Asset, list[Price | (int | None)]] = {}
        non_nft_assets = []
        for asset in assets:
            if asset.asset_type == AssetType.NFT:
                nft_price_data = self._eth_module_query(
                    module_name='nfts',
                    method='get_nfts_with_price',
                    query_specific_balances_before=None,
                )
                oracle = (
                    CurrentPriceOracle.MANUALCURRENT
                    if nft_price_data['manually_input'] is True
                    else CurrentPriceOracle.BLOCKCHAIN
                )
                assets_price[asset] = [Price(nft_price_data['price']), oracle.value]
            else:
                non_nft_assets.append(asset)

        if len(non_nft_assets) != 0:
            found_prices = Inquirer.find_prices_and_oracles(
                from_assets=non_nft_assets,
                to_asset=target_asset,
                ignore_cache=ignore_cache,
            )
            assets_price.update({
                asset: [price_and_oracle[0], price_and_oracle[1].value]
                for asset, price_and_oracle in found_prices.items()
            })

        result = {
            'assets': assets_price,
            'target_asset': target_asset,
            'oracles': {str(oracle): oracle.value for oracle in CurrentPriceOracle},
        }
        return {'result': process_result(result), 'message': '', 'status_code': HTTPStatus.OK}

    def query_asset_mappings_by_type(
            self,
            dict_keys: tuple[str, str, str],
            mapping_type: Literal['location', 'counterparty'],
            location_or_counterparty_reader_callback: Callable,
            filter_query: LocationAssetMappingsFilterQuery | CounterpartyAssetMappingsFilterQuery,
            query_columns: Literal[
                'local_id, location, exchange_symbol',
                'local_id, counterparty, symbol',
            ],
    ) -> dict[str, Any]:
        mappings, mappings_found, mappings_total = GlobalDBHandler.query_asset_mappings_by_type(
            mapping_type=mapping_type,
            filter_query=filter_query,
            dict_keys=dict_keys,
            query_columns=query_columns,
            location_or_counterparty_reader_callback=location_or_counterparty_reader_callback,
        )

        result = {
            'entries': mappings,
            'entries_found': mappings_found,
            'entries_total': mappings_total,
        }
        return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}

    def perform_asset_mapping_operation(
            self,
            mapping_fn: Callable,
            entries: Sequence[
                LocationAssetMappingUpdateEntry
                | LocationAssetMappingDeleteEntry
                | CounterpartyAssetMappingUpdateEntry
                | CounterpartyAssetMappingDeleteEntry
            ],
    ) -> dict[str, Any]:
        try:
            mapping_fn(entries=entries)
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def get_historical_assets_price(
            self,
            assets_timestamp: list[tuple[Asset, Timestamp]],
            target_asset: Asset,
            only_cache_period: int | None = None,
    ) -> dict[str, Any]:
        if only_cache_period is not None:
            result: dict[str, Any] = {
                'assets': defaultdict(lambda: defaultdict(lambda: ZERO_PRICE)),
                'target_asset': target_asset.identifier,
            }
            for price_result in GlobalDBHandler.get_historical_prices(
                query_data=[(entry[0], target_asset, entry[1]) for entry in assets_timestamp],
                max_seconds_distance=only_cache_period,
            ):
                if price_result is not None:
                    result['assets'][price_result.from_asset.identifier][price_result.timestamp] = str(price_result.price)  # noqa: E501

            return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}

        assets_price = PriceHistorian.query_multiple_prices(
            assets_timestamp=assets_timestamp,
            target_asset=target_asset,
            msg_aggregator=self.rotkehlchen.msg_aggregator,
        )
        result = {
            'assets': {k: dict(v) for k, v in assets_price.items()},
            'target_asset': target_asset,
        }
        return {'result': process_result(result), 'message': '', 'status_code': HTTPStatus.OK}

    def create_oracle_cache(
            self,
            oracle: HistoricalPriceOracle,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
            purge_old: bool,
    ) -> dict[str, Any]:
        try:
            self.rotkehlchen.create_oracle_cache(oracle, from_asset, to_asset, purge_old)
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}
        except UnsupportedAsset as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def delete_oracle_cache(
            self,
            oracle: HistoricalPriceOracle,
            from_asset: Asset,
            to_asset: Asset,
    ) -> dict[str, Any]:
        GlobalDBHandler.delete_historical_prices(
            from_asset=from_asset,
            to_asset=to_asset,
            source=oracle,
        )
        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def _get_oracle_cache(self, oracle: HistoricalPriceOracle) -> dict[str, Any]:
        cache_data = GlobalDBHandler.get_historical_price_data(oracle)
        return {'result': cache_data, 'message': '', 'status_code': HTTPStatus.OK}

    def get_oracle_cache(self, oracle: HistoricalPriceOracle) -> dict[str, Any]:
        return self._get_oracle_cache(oracle)

    def get_supported_oracles(self) -> dict[str, Any]:
        data = {
            'history': [
                {'id': str(x), 'name': str(x).capitalize()}
                for x in HistoricalPriceOracle
                if x not in NOT_EXPOSED_SOURCES
            ],
            'current': [{'id': str(x), 'name': str(x).capitalize()} for x in CurrentPriceOracle],
        }
        return {'result': data, 'message': '', 'status_code': HTTPStatus.OK}

    def get_token_info(
            self,
            address: ChecksumEvmAddress,
            chain_id: SUPPORTED_CHAIN_IDS,
    ) -> dict[str, Any]:
        evm_manager: EvmManager = self.rotkehlchen.chains_aggregator.get_evm_manager(chain_id)
        try:
            info = evm_manager.node_inquirer.get_erc20_contract_info(address=address)
        except (BadFunctionCallOutput, NotERC20Conformant):
            return {
                'result': None,
                'message': (
                    f'{chain_id!s} address {address} seems to not be a deployed contract '
                    'or not a valid erc20 token'
                ),
                'status_code': HTTPStatus.CONFLICT,
            }
        return {'result': info, 'message': '', 'status_code': HTTPStatus.OK}

    def get_assets_updates(self) -> dict[str, Any]:
        try:
            local, remote, new_changes = self.rotkehlchen.assets_updater.check_for_updates()
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        return {
            'result': {'local': local, 'remote': remote, 'new_changes': new_changes},
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def perform_assets_updates(
            self,
            up_to_version: int | None,
            conflicts: dict[Asset, Literal['remote', 'local']] | None,
    ) -> dict[str, Any]:
        try:
            result = self.rotkehlchen.assets_updater.perform_update(up_to_version, conflicts)
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        if result is None:
            return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

        return {
            'result': result,
            'message': 'Found conflicts during assets upgrade',
            'status_code': HTTPStatus.CONFLICT,
        }

    def add_manual_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            price: Price,
            timestamp: Timestamp,
    ) -> dict[str, Any]:
        historical_price = HistoricalPrice(
            from_asset=from_asset,
            to_asset=to_asset,
            source=HistoricalPriceOracle.MANUAL,
            timestamp=timestamp,
            price=price,
        )
        added = GlobalDBHandler.add_single_historical_price(historical_price)
        if added:
            return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}
        return {
            'result': False,
            'message': 'Failed to store manual price',
            'status_code': HTTPStatus.CONFLICT,
        }

    def edit_manual_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            price: Price,
            timestamp: Timestamp,
    ) -> dict[str, Any]:
        historical_price = HistoricalPrice(
            from_asset=from_asset,
            to_asset=to_asset,
            source=HistoricalPriceOracle.MANUAL,
            timestamp=timestamp,
            price=price,
        )
        edited = GlobalDBHandler.edit_manual_price(historical_price)
        if edited:
            return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}
        return {
            'result': False,
            'message': 'Failed to edit manual price',
            'status_code': HTTPStatus.CONFLICT,
        }

    def get_manual_prices(
            self,
            from_asset: Asset | None,
            to_asset: Asset | None,
    ) -> dict[str, Any]:
        prices = GlobalDBHandler.get_manual_prices(from_asset, to_asset)
        return {'result': prices, 'message': '', 'status_code': HTTPStatus.OK}

    def delete_manual_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> dict[str, Any]:
        deleted = GlobalDBHandler.delete_manual_price(from_asset, to_asset, timestamp)
        if deleted:
            return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}
        return {
            'result': False,
            'message': 'Failed to delete manual price',
            'status_code': HTTPStatus.CONFLICT,
        }

    def get_nfts(self, ignore_cache: bool) -> dict[str, Any]:
        return self._eth_module_query(
            module_name='nfts',
            method='get_all_info',
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('nfts'),
            ignore_cache=ignore_cache,
        )

    def get_nfts_balances(
            self,
            filter_query: NFTFilterQuery,
            ignore_cache: bool,
    ) -> dict[str, Any]:
        if ignore_cache is True:
            self._eth_module_query(
                module_name='nfts',
                method='query_balances',
                query_specific_balances_before=None,
                addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('nfts'),
            )

        return self._eth_module_query(
            module_name='nfts',
            method='get_db_nft_balances',
            query_specific_balances_before=None,
            filter_query=filter_query,
        )

    def get_manual_latest_prices(
            self,
            from_asset: Asset | None,
            to_asset: Asset | None,
    ) -> dict[str, Any]:
        prices = GlobalDBHandler.get_all_manual_latest_prices(
            from_asset=from_asset,
            to_asset=to_asset,
        )
        prices_information = [{
            'from_asset': x[0],
            'to_asset': x[1],
            'price': x[2],
        } for x in prices]
        if (nft_module := self.rotkehlchen.chains_aggregator.get_module('nfts')) is not None:
            nft_price_data = nft_module.get_nfts_with_price(
                from_asset=from_asset,
                to_asset=to_asset,
                only_with_manual_prices=True,
            )
            prices_information.extend([{
                'from_asset': nft_data['asset'],
                'to_asset': nft_data['price_asset'],
                'price': nft_data['price_in_asset'],
            } for nft_data in nft_price_data])

        return {'result': prices_information, 'message': '', 'status_code': HTTPStatus.OK}

    def get_nfts_with_price(self, lps_handling: NftLpHandling) -> dict[str, Any]:
        return self._eth_module_query(
            module_name='nfts',
            method='get_nfts_with_price',
            query_specific_balances_before=None,
            lps_handling=lps_handling,
        )

    def add_manual_latest_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            price: Price,
    ) -> dict[str, Any]:
        if from_asset.is_nft():
            return self._eth_module_query(
                module_name='nfts',
                method='add_nft_with_price',
                query_specific_balances_before=None,
                from_asset=from_asset,
                to_asset=to_asset,
                price=price,
            )
        try:
            assets_to_invalidate = GlobalDBHandler.add_manual_latest_price(
                from_asset=from_asset,
                to_asset=to_asset,
                price=price,
            )
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}
        Inquirer.remove_cache_prices_for_asset(assets_to_invalidate)

        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def delete_manual_latest_price(self, asset: Asset) -> dict[str, Any]:
        if asset.is_nft():
            return self._eth_module_query(
                module_name='nfts',
                method='delete_price_for_nft',
                query_specific_balances_before=None,
                asset=asset,
            )
        try:
            assets_to_invalidate = GlobalDBHandler.delete_manual_latest_price(asset=asset)
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}
        Inquirer.remove_cache_prices_for_asset(assets_to_invalidate)

        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def add_to_spam_assets_false_positive(self, token: EvmToken) -> dict[str, Any]:
        globaldb = GlobalDBHandler()
        with globaldb.conn.write_ctx() as write_cursor:
            globaldb_set_general_cache_values(
                write_cursor=write_cursor,
                key_parts=(CacheType.SPAM_ASSET_FALSE_POSITIVE,),
                values=(token.identifier,),
            )

            if token.protocol == SPAM_PROTOCOL:
                set_token_spam_protocol(write_cursor=write_cursor, token=token, is_spam=False)

        with self.rotkehlchen.data.db.user_write() as write_cursor:
            self.rotkehlchen.data.db.remove_from_ignored_assets(
                write_cursor=write_cursor,
                asset=token,
            )

        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def remove_from_spam_assets_false_positives(self, token: EvmToken) -> dict[str, Any]:
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            globaldb_delete_general_cache_values(
                write_cursor=write_cursor,
                key_parts=(CacheType.SPAM_ASSET_FALSE_POSITIVE,),
                values=(token.identifier,),
            )

        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def get_spam_assets_false_positives(self) -> dict[str, Any]:
        with GlobalDBHandler().conn.read_ctx() as cursor:
            whitelisted_tokens = globaldb_get_general_cache_values(
                cursor=cursor,
                key_parts=(CacheType.SPAM_ASSET_FALSE_POSITIVE,),
            )

        return {'result': whitelisted_tokens, 'message': '', 'status_code': HTTPStatus.OK}

    def add_tokens_to_spam(self, tokens: list[EvmToken]) -> dict[str, Any]:
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            for token in tokens:
                if token.protocol != SPAM_PROTOCOL:
                    set_token_spam_protocol(write_cursor=write_cursor, token=token, is_spam=True)

                globaldb_delete_general_cache_values(
                    write_cursor=write_cursor,
                    key_parts=(CacheType.SPAM_ASSET_FALSE_POSITIVE,),
                    values=(token.identifier,),
                )
                AssetResolver.clean_memory_cache(token.identifier)

                for balances in self.rotkehlchen.chains_aggregator.balances.get(
                    chain=(blockchain := token.chain_id.to_blockchain()),
                ).values():
                    in_assets = balances.assets.pop(token, None)  # type: ignore
                    in_liabilities = balances.liabilities.pop(token, None)  # type: ignore

                    if in_assets is not None or in_liabilities is not None:
                        self.rotkehlchen.chains_aggregator.flush_cache('query_balances')
                        self.rotkehlchen.chains_aggregator.flush_cache(
                            name='query_balances',
                            blockchain=blockchain,
                        )

        self.rotkehlchen.data.add_ignored_assets(assets=tokens)
        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def remove_token_from_spam(self, token: EvmToken) -> dict[str, Any]:
        if token.protocol == SPAM_PROTOCOL:
            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                set_token_spam_protocol(write_cursor=write_cursor, token=token, is_spam=False)

        self.rotkehlchen.data.remove_ignored_assets(assets=[token])
        AssetResolver().clean_memory_cache(token.identifier)
        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def get_types_mappings(self) -> dict[str, Any]:
        result = {
            'global_mappings': EVENT_CATEGORY_MAPPINGS,
            'entry_type_mappings': ENTRY_TYPE_MAPPINGS,
            'event_category_details': {
                category: {
                    'counterparty_mappings': entries,
                    'direction': category.direction.serialize(),
                }
                for category, entries in EVENT_CATEGORY_DETAILS.items()
            },
            'accounting_events_icons': ACCOUNTING_EVENTS_ICONS,
        }
        return {'result': process_result(result), 'message': '', 'status_code': HTTPStatus.OK}

    def get_counterparties_details(self) -> dict[str, Any]:
        counterparties = {(exchange_id := x.name.lower()): CounterpartyDetails(
            identifier=exchange_id,
            label=LOCATION_DETAILS[x].get('label', x.name.capitalize()),
            image=LOCATION_DETAILS[x].get('image'),
        ) for x in ALL_SUPPORTED_EXCHANGES}
        for counterparty in self.rotkehlchen.chains_aggregator.get_all_counterparties():
            counterparties.setdefault(counterparty.identifier, counterparty)

        return {
            'result': list(counterparties.values()),
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def refresh_protocol_data(self, cache_protocol: ProtocolsWithCache) -> dict[str, Any]:
        eth_node_inquirer = self.rotkehlchen.chains_aggregator.ethereum.node_inquirer
        optimism_inquirer = self.rotkehlchen.chains_aggregator.optimism.node_inquirer
        base_inquirer = self.rotkehlchen.chains_aggregator.base.node_inquirer
        arbitrum_inquirer = self.rotkehlchen.chains_aggregator.arbitrum_one.node_inquirer
        gnosis_inquirer = self.rotkehlchen.chains_aggregator.gnosis.node_inquirer
        polygon_inquirer = self.rotkehlchen.chains_aggregator.polygon_pos.node_inquirer
        cache_rules: list[tuple[str, CacheType, Callable, ChainID | None, Any]] = []

        match cache_protocol:
            case ProtocolsWithCache.CURVE:
                cache_rules.extend([
                    (
                        'curve pools',
                        CacheType.CURVE_LP_TOKENS,
                        query_curve_data,
                        chain_id,
                        node_inquirer,
                    )
                    for chain_id, node_inquirer in (
                        (ChainID.ETHEREUM, eth_node_inquirer),
                        (ChainID.OPTIMISM, optimism_inquirer),
                        (ChainID.ARBITRUM_ONE, arbitrum_inquirer),
                        (ChainID.BASE, base_inquirer),
                        (ChainID.GNOSIS, gnosis_inquirer),
                        (ChainID.POLYGON_POS, polygon_inquirer),
                    )
                ])
            case ProtocolsWithCache.VELODROME:
                cache_rules.append((
                    'velodrome pools',
                    CacheType.VELODROME_POOL_ADDRESS,
                    query_velodrome_like_data,
                    None,
                    optimism_inquirer,
                ))
            case ProtocolsWithCache.AERODROME:
                cache_rules.append((
                    'aerodrome pools',
                    CacheType.AERODROME_POOL_ADDRESS,
                    query_velodrome_like_data,
                    None,
                    base_inquirer,
                ))
            case ProtocolsWithCache.CONVEX:
                cache_rules.append((
                    'convex pools',
                    CacheType.CONVEX_POOL_ADDRESS,
                    query_convex_data,
                    None,
                    eth_node_inquirer,
                ))
            case ProtocolsWithCache.GEARBOX:
                cache_rules.append((
                    'gearbox pools',
                    CacheType.GEARBOX_POOL_ADDRESS,
                    query_gearbox_data,
                    ChainID.ETHEREUM,
                    eth_node_inquirer,
                ))
            case ProtocolsWithCache.YEARN:
                try:
                    query_yearn_vaults(
                        db=self.rotkehlchen.data.db,
                        ethereum_inquirer=eth_node_inquirer,
                    )
                except RemoteError as e:
                    return {
                        'result': None,
                        'message': f'Failed to refresh yearn vaults cache due to: {e!s}',
                        'status_code': HTTPStatus.CONFLICT,
                    }
            case ProtocolsWithCache.MAKER:
                try:
                    query_ilk_registry_and_maybe_update_cache(eth_node_inquirer)
                except RemoteError as e:
                    return {
                        'result': None,
                        'message': f'Failed to refresh makerdao vault ilk cache due to: {e!s}',
                        'status_code': HTTPStatus.CONFLICT,
                    }
            case ProtocolsWithCache.SPARK | ProtocolsWithCache.AAVE:
                fn = (
                    update_aave_v3_underlying_assets
                    if cache_protocol == ProtocolsWithCache.AAVE
                    else update_spark_underlying_assets
                )
                try:
                    fn(chains_aggregator=self.rotkehlchen.chains_aggregator)
                except RemoteError as e:
                    return {
                        'result': None,
                        'message': (
                            f'Failed to refresh {cache_protocol.name.lower()} cache due to: {e!s}'
                        ),
                        'status_code': HTTPStatus.CONFLICT,
                    }
            case ProtocolsWithCache.BALANCER_V1:
                cache_rules.extend([
                    (
                        'balancer v1 pools',
                        CacheType.BALANCER_V1_POOLS,
                        query_balancer_data,
                        chain_id,
                        node_inquirer,
                    )
                    for chain_id, node_inquirer in (
                        (ChainID.GNOSIS, gnosis_inquirer),
                        (ChainID.ETHEREUM, eth_node_inquirer),
                        (ChainID.ARBITRUM_ONE, arbitrum_inquirer),
                    )
                ])
            case ProtocolsWithCache.BALANCER_V2:
                cache_rules.extend([
                    (
                        'balancer v2 pools',
                        CacheType.BALANCER_V2_POOLS,
                        query_balancer_data,
                        chain_id,
                        node_inquirer,
                    )
                    for chain_id, node_inquirer in (
                        (ChainID.BASE, base_inquirer),
                        (ChainID.GNOSIS, gnosis_inquirer),
                        (ChainID.ETHEREUM, eth_node_inquirer),
                        (ChainID.OPTIMISM, optimism_inquirer),
                        (ChainID.POLYGON_POS, polygon_inquirer),
                        (ChainID.ARBITRUM_ONE, arbitrum_inquirer),
                    )
                ])
            case ProtocolsWithCache.BALANCER_V3:
                cache_rules.extend([
                    (
                        'balancer v3 pools',
                        CacheType.BALANCER_V3_POOLS,
                        query_balancer_data,
                        chain_id,
                        node_inquirer,
                    )
                    for chain_id, node_inquirer in (
                        (ChainID.BASE, base_inquirer),
                        (ChainID.GNOSIS, gnosis_inquirer),
                        (ChainID.ETHEREUM, eth_node_inquirer),
                        (ChainID.OPTIMISM, optimism_inquirer),
                        (ChainID.ARBITRUM_ONE, arbitrum_inquirer),
                    )
                ])
            case ProtocolsWithCache.ETH_WITHDRAWALS:
                with self.rotkehlchen.data.db.conn.write_ctx() as write_cursor:
                    self.rotkehlchen.data.db.delete_dynamic_caches(
                        write_cursor=write_cursor,
                        key_parts=[
                            DBCacheDynamic.WITHDRAWALS_TS.value[0].split('_')[0],
                            DBCacheDynamic.WITHDRAWALS_IDX.value[0].split('_')[0],
                        ],
                    )
            case ProtocolsWithCache.ETH_BLOCKS:
                with self.rotkehlchen.data.db.conn.write_ctx() as write_cursor:
                    self.rotkehlchen.data.db.delete_dynamic_caches(
                        write_cursor=write_cursor,
                        key_parts=[DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS.value[0][:30]],
                    )
            case ProtocolsWithCache.ETH_VALIDATORS_DATA:
                with self.rotkehlchen.data.db.conn.write_ctx() as write_cursor:
                    write_cursor.execute('DELETE FROM eth_validators_data_cache')
            case ProtocolsWithCache.MERKL:
                with GlobalDBHandler().conn.write_ctx() as write_cursor:
                    write_cursor.execute(
                        'DELETE FROM unique_cache WHERE key LIKE ?',
                        (f'{CacheType.MERKL_REWARD_PROTOCOLS.serialize()}%',),
                    )
            case ProtocolsWithCache.BEEFY_FINANCE:
                with GlobalDBHandler().conn.write_ctx() as write_cursor:
                    write_cursor.execute(
                        'DELETE FROM general_cache WHERE key LIKE ?',
                        (f'{CacheType.BEEFY_VAULTS.serialize()}%',),
                    )
            case ProtocolsWithCache.CUSTOMIZED_EVENTS:
                with self.rotkehlchen.data.db.conn.write_ctx() as write_cursor:
                    write_cursor.execute(
                        'DELETE FROM key_value_cache WHERE name LIKE ?',
                        (f'{DBCacheDynamic.CUSTOMIZED_EVENT_ORIGINAL_SEQ_IDX.value[0][:25]}%',),
                    )

        failed_to_update = []
        for (cache, cache_type, query_method, chain_id, inquirer) in cache_rules:
            if inquirer.ensure_cache_data_is_updated(
                cache_type=cache_type,
                query_method=query_method,
                chain_id=chain_id,
                cache_key_parts=None if chain_id is None else (str(chain_id.serialize_for_db()),),
                force_refresh=True,
            ) == RemoteDataQueryStatus.FAILED:
                failed_to_update.append(cache)

        if len(failed_to_update) != 0:
            return {
                'result': None,
                'message': f'Failed to refresh caches for: {", ".join(failed_to_update)}',
                'status_code': HTTPStatus.CONFLICT,
            }

        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def get_airdrops_metadata(self) -> dict[str, Any]:
        result = []
        try:
            for identifier, airdrop in fetch_airdrops_metadata(self.rotkehlchen.data.db)[0].items():  # noqa: E501
                result.append({
                    'identifier': identifier,
                    'name': airdrop.name,
                    'icon': airdrop.icon,
                })
                if airdrop.icon_url is not None:
                    result[-1]['icon_url'] = airdrop.icon_url
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}
        return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}

    def get_defi_metadata(self) -> dict[str, Any]:
        result = []
        for identifier, protocol in DEFI_PROTOCOLS.items():
            result.append({
                'identifier': identifier,
                'name': protocol.name,
                'icon': protocol.icon,
            })
        return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}
