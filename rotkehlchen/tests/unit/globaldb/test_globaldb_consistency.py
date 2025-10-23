import json
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, cast
from urllib import request
from warnings import warn

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.types import AssetType
from rotkehlchen.chain.ethereum.modules.pickle_finance.constants import CPT_PICKLE
from rotkehlchen.chain.ethereum.modules.yearn.constants import CPT_YEARN_V1, CPT_YEARN_V2
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.decoding.gearbox.constants import CPT_GEARBOX
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_AERODROME, CPT_VELODROME
from rotkehlchen.constants.misc import GLOBALDIR_NAME, ONE
from rotkehlchen.db.constants import UpdateType
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.asset_updates.manager import AssetsUpdater
from rotkehlchen.tests.fixtures.globaldb import create_globaldb
from rotkehlchen.types import (
    SPAM_PROTOCOL,
    ChainID,
    Location,
    Timestamp,
)

if TYPE_CHECKING:
    from rotkehlchen.db.updates import RotkiDataUpdater
    from rotkehlchen.globaldb.handler import GlobalDBHandler
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

ASSET_COLLECTION_UPDATE: Final = 'INSERT INTO asset_collections(id, name, symbol) VALUES ({collection}, "{name}", "{symbol}");'  # noqa: E501
ASSET_MAPPING: Final = 'INSERT INTO multiasset_mappings(collection_id, asset) VALUES ({collection}, "{id}");'  # noqa: E501
ASSET_UPDATE: Final = "[('{address}', Chain.{chain_name}, '{coingecko}', '{cryptocompare}', {field_updates}, '{protocol}', {underlying_token_addresses})],"  # noqa: E501
NON_EVM_ASSET_INSERT = "INSERT INTO assets(identifier, name, type) VALUES('{identifier}', '{name}', '{type}'); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES('{identifier}', '{symbol}', '{coingecko}', '{cryptocompare}', {forked}, {started}, {swapped_for});"  # noqa: E501
IGNORED_PROTOCOLS: Final = {
    CPT_CURVE,
    CPT_YEARN_V1,
    CPT_YEARN_V2,
    CPT_VELODROME,
    CPT_AERODROME,
    CPT_PICKLE,
    SPAM_PROTOCOL,
    CPT_GEARBOX,
}


@dataclass(init=True, repr=False, eq=False, order=False, unsafe_hash=False, frozen=False)
class DBToken:
    address: 'ChecksumEvmAddress'
    type: str
    chain: int
    token_kind: str
    name: str
    symbol: str
    started: Timestamp | None = None
    forked: str | None = None
    swapped_for: str | None = None
    coingecko: str | None = None
    cryptocompare: str | None = None
    decimals: int | None = None
    protocol: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            'address': self.address,
            'chain': self.chain,
            'token_kind': self.token_kind,
            'name': self.name,
            'symbol': self.symbol,
            'started': self.started,
            'forked': self.forked,
            'swapped_for': self.swapped_for,
            'coingecko': self.coingecko,
            'cryptocompare': self.cryptocompare,
            'decimals': self.decimals,
            'protocol': self.protocol,
        }


def test_asset_updates_consistency_with_packaged_db(
        tmpdir_factory: 'pytest.TempdirFactory',
        messages_aggregator: 'MessagesAggregator',
):
    """Test that the globalDB updates are consistent with the packaged one.
    - All assets are present in both cases.
    - All details of these assets are the same in both cases.
    - All underlying assets are present and mapped in both cases.
    Protocol tokens that are queried automatically are not tested here.

    This test uses the env variable `TARGET_BRANCH` to select what branch in the assets repo
    it needs to check. Defaults to `develop`.
    """
    temp_data_dir = Path(tmpdir_factory.mktemp(GLOBALDIR_NAME))
    (old_db_dir := temp_data_dir / GLOBALDIR_NAME).mkdir(parents=True, exist_ok=True)
    request.urlretrieve(
        url='https://github.com/rotki/rotki/raw/v1.26.0/rotkehlchen/data/global.db',
        filename=old_db_dir / 'global.db',
    )
    target_branch = os.environ.get('TARGET_BRANCH', 'develop')

    globaldb = create_globaldb(
        data_directory=temp_data_dir,
        sql_vm_instructions_cb=0,
        perform_assets_updates=True,
        messages_aggregator=messages_aggregator,
    )

    with (
        globaldb.conn.read_ctx() as old_globaldb_cursor,
        globaldb.packaged_db_conn().read_ctx() as packaged_db_cursor,
    ):
        # Assets version here is 36 because:
        # - Global DB v9->v10 & v12 -> v13 includes breaking schema changes
        # - `apply_pending_compatible_updates` runs during create_globaldb() and pulls all compatible asset updates up to v32 and then v36 (max compatible)  # noqa: E501
        # - At this point we are sure that assets updates up until 36 are applied
        assert old_globaldb_cursor.execute("SELECT value FROM settings WHERE name='assets_version'").fetchone()[0] == '36'  # noqa: E501
        assert packaged_db_cursor.execute("SELECT value FROM settings WHERE name='assets_version'").fetchone()[0] == '38'  # noqa: E501

    assets_updater = AssetsUpdater(
        globaldb=globaldb,
        msg_aggregator=messages_aggregator,
    )
    assets_updater.branch = target_branch
    if (conflicts := assets_updater.perform_update(
        up_to_version=None,
        conflicts=None,
    )) is not None:
        assert assets_updater.perform_update(
            up_to_version=None,
            conflicts={
                Asset(conflict['identifier']): 'remote'
                for conflict in conflicts
            },
        ) is None

    evm_type_db = AssetType.EVM_TOKEN.serialize_for_db()
    with (
        globaldb.conn.read_ctx() as old_db_cursor,
        globaldb.packaged_db_conn().read_ctx() as packaged_db_cursor,
    ):
        ignored_identifiers = {  # prepare a set of identifiers that should be ignored
            identifiers[0]
            for cursor in (old_db_cursor, packaged_db_cursor)
            for identifiers in cursor.execute(
                f'SELECT identifier FROM evm_tokens WHERE '
                f'protocol IN ({",".join(["?"] * len(IGNORED_PROTOCOLS))}) OR '
                f'address in (SELECT value FROM general_cache)',
                list(IGNORED_PROTOCOLS),
            ).fetchall()
        }

        (
            (updated_assets, updated_underlying_db_assets, updated_collections, updated_multiasset_mappings),  # noqa: E501
            (packaged_assets, packaged_underlying_db_assets, packaged_collections, packaged_multiasset_mappings),  # noqa: E501
        ) = (
            (
                {
                    identifier: DBToken(
                        address=address,
                        type=asset_type,
                        chain=chain,
                        token_kind=token_kind,
                        decimals=decimals,
                        name=name,
                        symbol=symbol,
                        started=started,
                        forked=forked,
                        swapped_for=swapped_for,
                        coingecko=coingecko,
                        cryptocompare=cryptocompare,
                        protocol=protocol,
                    )
                    for (identifier, asset_type, address, decimals, name, symbol, started, forked, swapped_for, coingecko, cryptocompare, protocol, chain, token_kind)  # noqa: E501
                    in cursor.execute(
                        f"""
                        SELECT A.identifier, A.type, B.address, B.decimals, A.name, C.symbol, C.started, null, C.swapped_for, C.coingecko, C.cryptocompare, B.protocol, B.chain, B.token_kind FROM assets as A JOIN evm_tokens as B
                        ON B.identifier = A.identifier JOIN common_asset_details AS C ON C.identifier = B.identifier WHERE A.type = '{evm_type_db}'
                        UNION ALL
                        SELECT A.identifier, A.type, null, null, A.name, B.symbol,  B.started, B.forked, B.swapped_for, B.coingecko, B.cryptocompare, null, null, null from assets as A JOIN common_asset_details as B
                        ON B.identifier = A.identifier WHERE A.type != '{evm_type_db}';
                        """,  # noqa: E501
                    )
                    if identifier not in ignored_identifiers
                }, cursor.execute(
                    'SELECT identifier, weight, parent_token_entry FROM underlying_tokens_list',
                ).fetchall(), {
                    collection_id: (name, symbol)
                    for (collection_id, name, symbol)
                    in cursor.execute('SELECT id, name, symbol FROM asset_collections')
                }, cursor.execute(
                    'SELECT collection_id, asset FROM multiasset_mappings',
                ).fetchall(),
            )
            for cursor in (old_db_cursor, packaged_db_cursor)
        )

    missing_in_updates = []
    # find all the asset collections that are present in asset updates but not in packaged DB  # noqa: E501
    missing_in_packaged_db = [
        f'Asset collection id: {group_id} ({updated_collections[group_id][1]}) not found in packaged DB.'  # noqa: E501
        for group_id in updated_collections
        if group_id not in packaged_collections
    ]

    # find all the asset collections that are present in packaged DB but not in asset updates  # noqa: E501
    for group_id in packaged_collections:
        if group_id not in updated_collections:
            assert None not in (packaged_collections[group_id][i] for i in (0, 1))
            missing_in_updates.append(ASSET_COLLECTION_UPDATE.format(
                collection=group_id,
                name=packaged_collections[group_id][0],
                symbol=packaged_collections[group_id][1],
            ))
            continue

        if packaged_collections[group_id] != updated_collections[group_id]:
            missing_in_packaged_db.append(f'Asset collection id: {group_id} ({packaged_collections[group_id][1]}) - {packaged_collections[group_id]} (packaged) != {updated_collections[group_id]} (asset update)')  # noqa: E501

    # find all the multiasset mappings that are present in asset updates but not in packaged DB
    missing_in_packaged_db.extend([
        f'Multiasset mapping {mapping} not found in packaged DB.'
        for mapping in updated_multiasset_mappings
        if mapping not in packaged_multiasset_mappings
    ])

    # find all the multiasset mappings that are present in packaged DB but not in asset updates
    for mapping in packaged_multiasset_mappings:
        assert None not in (mapping[i] for i in (0, 1))
        if mapping not in updated_multiasset_mappings:
            missing_in_updates.append(ASSET_MAPPING.format(collection=mapping[0], id=mapping[1]))

    field_to_table = {  # a mapping from EvmTokens field names to the DB table they are stored in
        'name': 'assets',
        'address': 'evm_tokens',
        'chain': 'evm_tokens',
        'token_kind': 'evm_tokens',
        'decimals': 'evm_tokens',
        'protocol': 'evm_tokens',
        'symbol': 'common_asset_details',
        'started': 'common_asset_details',
        'swapped_for': 'common_asset_details',
        'coingecko': 'common_asset_details',
        'cryptocompare': 'common_asset_details',
    }

    # populate mappings from parent token to set of underlying tokens for both DBs
    updated_underlying_assets: dict[str, set[str]] = defaultdict(set)
    packaged_underlying_assets: dict[str, set[str]] = defaultdict(set)
    for underlying_db_assets, underlying_assets in (
        (updated_underlying_db_assets, updated_underlying_assets),
        (packaged_underlying_db_assets, packaged_underlying_assets),
    ):
        for underlying_identifier, weight, parent_identifier in underlying_db_assets:
            if FVal(weight) != ONE:
                warn(f'Underlying asset {underlying_identifier} weight is not 1: {weight}. Skipping its DB check. Check it manually.')  # noqa: E501
                continue

            underlying_assets[parent_identifier].add(underlying_identifier)

    # skip the assets that have underlying assets that are ignored
    updated_assets = {
        identifier: updated_assets[identifier]
        for identifier in updated_assets
        if all(
            underlying_asset not in ignored_identifiers
            for underlying_asset in updated_underlying_assets[identifier]
        )
    }
    packaged_assets = {
        identifier: packaged_assets[identifier]
        for identifier in packaged_assets
        if all(
            underlying_asset not in ignored_identifiers
            for underlying_asset in packaged_underlying_assets[identifier]
        )
    }

    # find all the assets that are present in asset updates but not in packaged DB
    missing_in_packaged_db.extend([
        f'Asset: {identifier} ({updated_assets[identifier].symbol}) not found in packaged DB. Protocol: {updated_assets[identifier].protocol}'  # noqa: E501
        for identifier in updated_assets
        if identifier not in packaged_assets
    ])

    # find all the assets that are present in packaged DB but not in asset updates
    for identifier in packaged_assets:
        if identifier not in updated_assets:
            if packaged_assets[identifier].type == evm_type_db:
                missing_in_updates.append(ASSET_UPDATE.format(
                    address=packaged_assets[identifier].address,
                    chain_name=ChainID.deserialize(packaged_assets[identifier].chain).name,
                    coingecko=packaged_assets[identifier].coingecko,
                    cryptocompare=packaged_assets[identifier].cryptocompare,
                    field_updates={},
                    protocol=packaged_assets[identifier].protocol,
                    underlying_token_addresses=[
                        packaged_assets[identifier].address
                        for identifier in packaged_underlying_assets[identifier]
                    ],
                ))
            else:
                missing_in_updates.append(NON_EVM_ASSET_INSERT.format(
                    identifier=identifier,
                    name=packaged_assets[identifier].name,
                    type=packaged_assets[identifier].type,
                    symbol=packaged_assets[identifier].symbol,
                    coingecko=packaged_assets[identifier].coingecko,
                    cryptocompare=packaged_assets[identifier].cryptocompare,
                    forked='NULL' if packaged_assets[identifier].forked is None else f"'{packaged_assets[identifier].forked}'",  # noqa: E501
                    started='NULL' if packaged_assets[identifier].started is None else packaged_assets[identifier].started,  # noqa: E501
                    swapped_for='NULL' if packaged_assets[identifier].swapped_for is None else f"'{packaged_assets[identifier].swapped_for}'",  # noqa: E501
                ) + '\n*')
            continue

        for assets in (updated_assets, packaged_assets):
            for key, value in assets[identifier].as_dict().items():
                if value == '':
                    setattr(assets[identifier], key, None)

        # if the updated asset values are different from the packaged asset values, prepare their updates  # noqa: E501
        if packaged_assets[identifier].as_dict() != updated_assets[identifier].as_dict():
            updates: dict[str, dict[str, str]] = defaultdict(dict)  # mapping from table name to mapping from column name to value, that needs to update  # noqa: E501
            fields_to_update: dict = {'underlying_tokens': []}
            for key, packaged_field in packaged_assets[identifier].as_dict().items():
                updated_field = getattr(updated_assets[identifier], key)
                if packaged_field is not None and updated_field != packaged_field:
                    updates[field_to_table[key]][key] = packaged_field
                    fields_to_update[key] = packaged_field

                elif updated_field is not None and packaged_field is None:
                    missing_in_packaged_db.append(f'Asset: {identifier} ({key}) - {packaged_field} (packaged) != {updated_field} (asset update)')  # noqa: E501
                    fields_to_update[key] = updated_field

                else:
                    fields_to_update[key] = packaged_field

            if packaged_underlying_assets[identifier] != updated_underlying_assets[identifier]:
                if len(updated_underlying_assets[identifier] - packaged_underlying_assets[identifier]) > 0:  # noqa: E501
                    missing_in_packaged_db.append(f'Asset: {identifier} ({key}) - {packaged_field} (packaged) != {updated_field} (asset update)')  # noqa: E501  # pylint: disable=undefined-loop-variable

                if len(underlying_tokens_to_update := updated_underlying_assets[identifier] - packaged_underlying_assets[identifier]) > 0:  # noqa: E501
                    fields_to_update['underlying_tokens'] = [
                        updated_assets[identifier].address
                        for identifier in underlying_tokens_to_update
                    ]

            if len(updates) > 0:
                if packaged_assets[identifier].type == evm_type_db:
                    missing_in_updates.append(ASSET_UPDATE.format(
                        address=fields_to_update['address'],
                        chain_name=ChainID.deserialize(fields_to_update['chain']).name,
                        coingecko=fields_to_update['coingecko'],
                        cryptocompare=fields_to_update['cryptocompare'],
                        field_updates=dict(updates),
                        protocol=fields_to_update['protocol'],
                        underlying_token_addresses=fields_to_update['underlying_tokens'],
                    ))
                else:
                    # log SQL query to update it
                    missing_in_updates.extend([
                        '; '.join([
                            f'UPDATE {table_name} SET ' + ', '.join([
                                field + ' = ' + (
                                    '{value}' if field in {'forked', 'started', 'swapped_for'} else "'{value}'"  # noqa: E501
                                ).format(value=value)
                                for field, value in fields.items()
                            ]) + f" WHERE identifier = '{identifier}';"
                            for table_name, fields in updates.items()
                        ]),
                        NON_EVM_ASSET_INSERT.format(  # and its insert query
                            identifier=identifier,
                            name=packaged_assets[identifier].name,
                            type=packaged_assets[identifier].type,
                            symbol=packaged_assets[identifier].symbol,
                            coingecko=packaged_assets[identifier].coingecko,
                            cryptocompare=packaged_assets[identifier].cryptocompare,
                            forked='NULL' if packaged_assets[identifier].forked is None else f"'{packaged_assets[identifier].forked}'",  # noqa: E501
                            started='NULL' if packaged_assets[identifier].started is None else packaged_assets[identifier].started,  # noqa: E501
                            swapped_for='NULL' if packaged_assets[identifier].swapped_for is None else f"'{packaged_assets[identifier].swapped_for}'",  # noqa: E501
                        ),
                    ])

    missing_in_updates = [
        str(update).replace('None', '')
        for update in missing_in_updates
    ]

    if missing_in_packaged_db != []:
        warn('\n'.join(missing_in_packaged_db))

    if missing_in_updates != []:
        pytest.fail('Found entries that are missing in remote updates:\n' + '\n'.join(missing_in_updates))  # noqa: E501


def test_oracle_ids_in_asset_collections(globaldb: 'GlobalDBHandler'):
    """Test that for each asset in a collection, their oracle IDs are same."""
    with globaldb.conn.read_ctx() as cursor:
        assets = {
            identifier: {
                'coingecko': coingecko,
                'cryptocompare': cryptocompare,
            }
            for (identifier, coingecko, cryptocompare)
            in cursor.execute(
                'SELECT identifier, coingecko, cryptocompare FROM common_asset_details',
            )
        }

        multiasset_mappings = cursor.execute(
            'SELECT collection_id, asset FROM multiasset_mappings',
        ).fetchall()

    asset_to_group_id = {}
    group_id_to_assets = defaultdict(set)
    for mapping in multiasset_mappings:
        group_id_to_assets[mapping[0]].add(mapping[1])
        asset_to_group_id[mapping[1]] = mapping[0]

    # TODO: This needs to go away and group types with price attributes need to
    # be taken into account here: https://github.com/rotki/rotki/issues/8639
    oracle_exceptions = {  # Exceptions for the oracle group test for groups that have contain both an asset and wrapped versions. Also some other exceptions  # noqa: E501
        23,  # DAI group exception for XDAI
        38,  # ETH group exception for WETH
        40,  # btc and wrapped bitcoin
        52,  # pol-matic. Have different oracle ids
        155,  # wLUNA and LUNA
        348,  # BNB and WBNB
        240,  # eure since the new coins use a different coingecko id.
    }
    mismatches = []
    group_id_to_oracle_ids: dict[str, dict[str, str]] = defaultdict(dict)
    for oracle in ('coingecko', 'cryptocompare'):
        for group_id, asset_collection in group_id_to_assets.items():
            for identifier in asset_collection:
                if identifier in assets and assets[identifier][oracle] not in {None, ''}:
                    if group_id not in oracle_exceptions and group_id_to_oracle_ids[group_id].get(oracle) not in {None, ''}:  # noqa: E501
                        if assets[identifier][oracle].lower() != group_id_to_oracle_ids[group_id][oracle].lower():  # noqa: E501
                            mismatches.append(f'{oracle} ({assets[identifier][oracle]} != {group_id_to_oracle_ids[group_id][oracle]}) mismatch for asset {identifier} in group {group_id}')  # noqa: E501
                    else:
                        group_id_to_oracle_ids[group_id][oracle] = assets[identifier][oracle]

    if len(mismatches) > 0:
        pytest.fail('oracle IDs do not match:\n' + '\n'.join(mismatches))


@pytest.mark.parametrize('our_version', ['1.40.0'])  # set latest version so data can be updated
def test_remote_updates_consistency_with_packaged_db(
        tmpdir_factory: 'pytest.TempdirFactory',
        messages_aggregator: 'MessagesAggregator',
        data_updater: 'RotkiDataUpdater',
):
    """Test that the remote updates are consistent with the packaged db for:
    - Location asset mappings
    - Counterparty asset mappings
    - Location unsupported assets
    """
    temp_data_dir = Path(tmpdir_factory.mktemp(GLOBALDIR_NAME))
    (old_db_dir := temp_data_dir / GLOBALDIR_NAME).mkdir(parents=True, exist_ok=True)
    request.urlretrieve(  # location_asset_mappings and location_unsupported_assets were added since v1.33.0  # noqa: E501
        url='https://github.com/rotki/rotki/raw/v1.33.0/rotkehlchen/data/global.db',
        filename=old_db_dir / 'global.db',
    )

    globaldb = create_globaldb(
        data_directory=temp_data_dir,
        sql_vm_instructions_cb=0,
        messages_aggregator=messages_aggregator,
    )
    data_updater.check_for_updates(updates=[
        UpdateType.LOCATION_ASSET_MAPPINGS,
        UpdateType.LOCATION_UNSUPPORTED_ASSETS,
        UpdateType.COUNTERPARTY_ASSET_MAPPINGS,
    ])

    with (
        globaldb.conn.read_ctx() as old_db_cursor,
        globaldb.packaged_db_conn().read_ctx() as packaged_db_cursor,
    ):
        (
            (updated_location_asset_mappings, updated_counterparty_asset_mappings, updated_location_unsupported_assets),  # noqa: E501
            (packaged_location_asset_mappings, packaged_counterparty_asset_mappings, packaged_location_unsupported_assets),  # noqa: E501
        ) = (
            (
                {
                    (location, symbol): identifier
                    for location, symbol, identifier in cursor.execute(
                        'SELECT location, exchange_symbol, local_id FROM location_asset_mappings',
                    )
                },
                {
                    (counterparty, symbol): identifier
                    for counterparty, symbol, identifier in cursor.execute(
                        'SELECT counterparty, symbol, local_id FROM counterparty_asset_mappings',
                    )
                }, set(cursor.execute(
                    'SELECT location, exchange_symbol FROM location_unsupported_assets',
                ).fetchall()),
            )
            for cursor in (old_db_cursor, packaged_db_cursor)
        )

    missing_in_packaged_db: list[Any] = []
    missing_in_remote_updates: list[Any] = []
    for mapping_type, table_details in [
        (
            'location',
            {
                'updated_mappings': updated_location_asset_mappings,
                'packaged_mappings': packaged_location_asset_mappings,
                'table_name': 'location_asset_mappings',
                'id_field': 'local_id',
                'field1_name': 'location',
                'field2_name': 'exchange_symbol',
            },
        ),
        (
            'counterparty',
            {
                'updated_mappings': updated_counterparty_asset_mappings,
                'packaged_mappings': packaged_counterparty_asset_mappings,
                'table_name': 'counterparty_asset_mappings',
                'id_field': 'local_id',
                'field1_name': 'counterparty',
                'field2_name': 'symbol',
            },
        ),
    ]:
        updated_mappings = cast('dict[tuple[Any, Any], Any]', table_details['updated_mappings'])
        packaged_mappings = cast('dict[tuple[Any, Any], Any]', table_details['packaged_mappings'])
        table_name = table_details['table_name']
        id_field = table_details['id_field']
        field1_name = table_details['field1_name']
        field2_name = table_details['field2_name']

        # find entries in remote updates but not in packaged db
        missing_in_packaged_db.extend([
            f"INSERT INTO {table_name}({id_field}, {field1_name}, {field2_name}) VALUES('{identifier}', '{field1}', '{field2}');"  # noqa: E501
            for (field1, field2), identifier in updated_mappings.items()
            if (field1, field2) not in packaged_mappings
        ])

        # find entries in packaged db but not in remote updates
        missing_in_remote_updates.extend([
            {
                'asset': identifier,
                field1_name: None if field1 is None else Location.deserialize_from_db(
                    field1).serialize() if mapping_type == 'location' else field1,
                f'{field1_name}_symbol': field2,
            }
            for (field1, field2), identifier in packaged_mappings.items()
            if (field1, field2) not in updated_mappings
        ])

        # find entries in both but with different values
        missing_in_packaged_db.extend([
            f'UPDATE {table_name} SET {id_field} = "{updated_mappings[field1, field2]}" WHERE {field1_name} = "{field1}" AND {field2_name} = "{field2}";'  # noqa: E501
            for (field1, field2), identifier in packaged_mappings.items()
            if (field1, field2) in updated_mappings and updated_mappings[field1, field2] != identifier  # noqa: E501
        ])

    # find all the location_unsupported_assets that are present in remote updates but not in packaged db  # noqa: E501
    missing_in_packaged_db.extend([
        f"INSERT INTO location_unsupported_assets(location, exchange_symbol) VALUES('{location}', '{symbol}');"  # noqa: E501
        for location, symbol in updated_location_unsupported_assets
        if (location, symbol) not in packaged_location_unsupported_assets
    ])

    # find all the location_unsupported_assets that are present in packaged db but not in remote updates  # noqa: E501
    missing_unsupported_assets = defaultdict(list)
    for location, symbol in packaged_location_unsupported_assets:
        if (location, symbol) not in updated_location_unsupported_assets:
            missing_unsupported_assets[Location.deserialize_from_db(location).serialize()].append(symbol)

    if len(missing_unsupported_assets) > 0:
        missing_in_remote_updates.append(missing_unsupported_assets)

    if len(missing_in_packaged_db) > 0:
        # warning here instead of failing because we generally keep adding remote updates without
        # adding them in packaged db and add all of them together right before releasing.
        warn('Found entries that are missing in packaged db:\n' + '\n'.join(missing_in_packaged_db))  # noqa: E501

    if len(missing_in_remote_updates) > 0:
        pytest.fail('Found entries that are missing in remote updates:\n' + json.dumps(missing_in_remote_updates, indent=4))  # noqa: E501
