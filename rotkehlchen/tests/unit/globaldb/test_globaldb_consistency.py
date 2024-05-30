from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final
from urllib import request
from warnings import warn

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE_V3
from rotkehlchen.constants.misc import GLOBALDIR_NAME, ONE
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.updates import AssetsUpdater
from rotkehlchen.tests.fixtures.globaldb import create_globaldb
from rotkehlchen.types import (
    AERODROME_POOL_PROTOCOL,
    CURVE_POOL_PROTOCOL,
    PICKLE_JAR_PROTOCOL,
    SPAM_PROTOCOL,
    VELODROME_POOL_PROTOCOL,
    YEARN_VAULTS_V1_PROTOCOL,
    YEARN_VAULTS_V2_PROTOCOL,
    ChainID,
    Timestamp,
)

if TYPE_CHECKING:
    from rotkehlchen.globaldb.handler import GlobalDBHandler
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

ASSET_COLLECTION_UPDATE: Final = 'INSERT INTO asset_collections(id, name, symbol) VALUES ({collection}, "{name}", "{symbol}");'  # noqa: E501
ASSET_MAPPING: Final = 'INSERT INTO multiasset_mappings(collection_id, asset) VALUES ({collection}, "{id}");'  # noqa: E501
ASSET_UPDATE: Final = "[('{address}', Chain.{chain_name}, '{coingecko}', '{cryptocompare}', {field_updates}, '{protocol}', {underlying_token_addresses})],"  # noqa: E501
IGNORED_PROTOCOLS: Final = {
    CURVE_POOL_PROTOCOL,
    YEARN_VAULTS_V1_PROTOCOL,
    YEARN_VAULTS_V2_PROTOCOL,
    VELODROME_POOL_PROTOCOL,
    AERODROME_POOL_PROTOCOL,
    PICKLE_JAR_PROTOCOL,
    SPAM_PROTOCOL,
    CPT_AAVE_V3,
}


@dataclass(init=True, repr=False, eq=False, order=False, unsafe_hash=False, frozen=False)
class DBToken:
    address: 'ChecksumEvmAddress'
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


def test_update_consistency_with_packaged_db(
        tmpdir_factory: 'pytest.TempdirFactory',
        messages_aggregator: 'MessagesAggregator',
):
    """Test that the globalDB updates are consistent with the packaged one.
    - All assets are present in both cases.
    - All details of these assets are the same in both cases.
    - All underlying assets are present and mapped in both cases.
    Protocol tokens that are queried automatically are not tested here."""
    temp_data_dir = Path(tmpdir_factory.mktemp(GLOBALDIR_NAME))
    (old_db_dir := temp_data_dir / GLOBALDIR_NAME).mkdir(parents=True, exist_ok=True)
    request.urlretrieve(
        url='https://github.com/rotki/rotki/raw/v1.26.0/rotkehlchen/data/global.db',
        filename=old_db_dir / 'global.db',
    )

    globaldb = create_globaldb(data_directory=temp_data_dir, sql_vm_instructions_cb=0)

    with (
        globaldb.conn.read_ctx() as old_db_cursor,
        globaldb.packaged_db_conn().read_ctx() as packaged_db_cursor,
    ):
        assert old_db_cursor.execute('SELECT value FROM settings WHERE name="assets_version"').fetchone()[0] == '15'  # noqa: E501
        assert packaged_db_cursor.execute('SELECT value FROM settings WHERE name="assets_version"').fetchone()[0] == '24'  # noqa: E501

    assets_updater = AssetsUpdater(msg_aggregator=messages_aggregator)
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
                        chain=chain,
                        token_kind=token_kind,
                        decimals=decimals,
                        name=name,
                        symbol=symbol,
                        started=started,
                        swapped_for=swapped_for,
                        coingecko=coingecko,
                        cryptocompare=cryptocompare,
                        protocol=protocol,
                    )
                    for (identifier, address, chain, token_kind, decimals, name, symbol, started, swapped_for, coingecko, cryptocompare, protocol)  # noqa: E501
                    in cursor.execute(
                        'SELECT A.identifier, B.address, B.chain, B.token_kind, B.decimals, '
                        'C.name, A.symbol, A.started, A.swapped_for, A.coingecko, '
                        'A.cryptocompare, B.protocol FROM evm_tokens AS B JOIN '
                        'common_asset_details AS A ON B.identifier = A.identifier '
                        'JOIN assets AS C on C.identifier=A.identifier',
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

    # find all the assets that are present in asset updates but not in packaged DB
    missing_in_packaged_db.extend([
        f'Asset: {identifier} ({updated_assets[identifier].symbol}) not found in packaged DB. Protocol: {updated_assets[identifier].protocol}'  # noqa: E501
        for identifier in updated_assets
        if identifier not in packaged_assets
    ])

    # find all the assets that are present in packaged DB but not in asset updates
    for identifier in packaged_assets:
        if identifier not in updated_assets:
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
                missing_in_updates.append(ASSET_UPDATE.format(
                    address=fields_to_update['address'],
                    chain_name=ChainID.deserialize(fields_to_update['chain']).name,
                    coingecko=fields_to_update['coingecko'],
                    cryptocompare=fields_to_update['cryptocompare'],
                    field_updates=dict(updates),
                    protocol=fields_to_update['protocol'],
                    underlying_token_addresses=fields_to_update['underlying_tokens'],
                ))

    missing_in_updates = [
        str(update).replace('None', '')
        for update in missing_in_updates
    ]

    if missing_in_packaged_db != []:
        warn('\n'.join(missing_in_packaged_db))

    if missing_in_updates != []:
        pytest.fail('\n'.join(missing_in_updates))


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

    mismatches = []
    group_id_to_oracle_ids: dict[str, dict[str, str]] = defaultdict(dict)
    for oracle in ('coingecko', 'cryptocompare'):
        for group_id, asset_collection in group_id_to_assets.items():
            for identifier in asset_collection:
                if identifier in assets and assets[identifier][oracle] not in {None, ''}:
                    if group_id_to_oracle_ids[group_id].get(oracle) not in {None, ''}:
                        if assets[identifier][oracle].lower() != group_id_to_oracle_ids[group_id][oracle].lower():  # noqa: E501
                            mismatches.append(f'{oracle} ({assets[identifier][oracle]} != {group_id_to_oracle_ids[group_id][oracle]}) mismatch for asset {identifier} in group {group_id}')  # noqa: E501
                    else:
                        group_id_to_oracle_ids[group_id][oracle] = assets[identifier][oracle]

    if len(mismatches) > 0:
        pytest.fail('\n'.join(mismatches))
