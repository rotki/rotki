import json
import logging
import re
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

from rotkehlchen.db.utils import update_table_schema
from rotkehlchen.errors.misc import DBUpgradeError
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import YEARN_VAULTS_V1_PROTOCOL
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.client import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Specify which of the eth_contracts.json contracts share identical ABI
MAKERDAO_ABI_GROUP_1 = [
    'MAKERDAO_ETH_A_JOIN',
    'MAKERDAO_ETH_B_JOIN',
    'MAKERDAO_ETH_C_JOIN',
    'MAKERDAO_BAT_A_JOIN',
    'MAKERDAO_PAXUSD_A_JOIN',
    'MAKERDAO_COMP_A_JOIN',
    'MAKERDAO_LRC_A_JOIN',
    'MAKERDAO_LINK_A_JOIN',
    'MAKERDAO_KNC_A_JOIN',
    'MAKERDAO_MANA_A_JOIN',
    'MAKERDAO_ZRX_A_JOIN',
    'MAKERDAO_BAL_A_JOIN',
    'MAKERDAO_YFI_A_JOIN',
    'MAKERDAO_UNI_A_JOIN',
    'MAKERDAO_AAVE_A_JOIN',
]
MAKERDAO_ABI_GROUP_2 = ['MAKERDAO_USDC_A_JOIN', 'MAKERDAO_USDC_B_JOIN', 'MAKERDAO_WBTC_A_JOIN']
MAKERDAO_ABI_GROUP_3 = ['MAKERDAO_WBTC_B_JOIN', 'MAKERDAO_WBTC_C_JOIN']

YEARN_ABI_GROUP_1 = ['YEARN_YCRV_VAULT', 'YEARN_USDC_VAULT']
YEARN_ABI_GROUP_2 = [
    'YEARN_YFI_VAULT',
    'YEARN_USDT_VAULT',
    'YEARN_BCURVE_VAULT',
    'YEARN_DAI_VAULT',
    'YEARN_SRENCURVE_VAULT',
]
YEARN_ABI_GROUP_3 = ['YEARN_TUSD_VAULT', 'YEARN_GUSD_VAULT', 'YEARN_3CRV_VAULT']
YEARN_ABI_GROUP_4 = [
    'YEARN_CDAI_CUSDC_VAULT',
    'YEARN_MUSD_3CRV_VAULT',
    'YEARN_GUSD_3CRV_VAULT',
    'YEARN_EURS_VAULT',
    'YEARN_MUSD_VAULT',
    'YEARN_RENBTC_WBTC_VAULT',
    'YEARN_USDN_3CRV_VAULT',
    'YEARN_UST_3CRV_VAULT',
    'YEARN_BBTC_SBTC_VAULT',
    'YEARN_TBTC_SBTC_VAULT',
    'YEARN_OBTC_SBTC_VAULT',
    'YEARN_HBTC_WBTC_VAULT',
    'YEARN_SUSD_3CRV_VAULT',
    'YEARN_HUSD_3CRV_VAULT',
    'YEARN_DUSD_3CRV_VAULT',
    'YEARN_A3CRV_VAULT',
    'YEARN_ETH_ANKER_VAULT',
    'YEARN_ASUSD_VAULT',
    'YEARN_USDP_3CRV_VAULT',
]


def _get_abi(cursor: 'DBCursor', name: str) -> int:
    cursor.execute('SELECT id FROM contract_abi WHERE name=?', (name,))
    result = cursor.fetchone()
    if result is None:
        error = f'During globalDB v3 -> v4 upgrade could not find abi {name} in the DB'
        log.error(error)
        raise DBUpgradeError(error)

    return result[0]


def _insert_abi_return_id(cursor: 'DBCursor', name: str, serialized_abi: str) -> int:
    cursor.execute(
        'INSERT INTO contract_abi(value, name) VALUES(?, ?)',
        (serialized_abi, name),
    )
    return cursor.lastrowid


def _get_or_create_common_abi(
        cursor: 'DBCursor',
        name: str,
        serialized_abi: str,
) -> int:
    cursor.execute('SELECT id FROM contract_abi WHERE name=?', (name,))
    result = cursor.fetchone()
    if result is not None:
        return result[0]

    return _insert_abi_return_id(
        cursor=cursor,
        name=name,
        serialized_abi=serialized_abi,
    )


def _add_eth_contracts_json(cursor: 'DBCursor') -> tuple[int, int, int]:
    eth_scan_abi_id, multicall_abi_id, ds_registry_abi_id = None, None, None
    root_dir = Path(__file__).resolve().parent.parent.parent
    contract_entries = json.loads((root_dir / 'data' / 'eth_contracts.json').read_text(encoding='utf8'))  # noqa: E501
    dxdao_contracts = json.loads((root_dir / 'chain' / 'ethereum' / 'modules' / 'dxdaomesa' / 'data' / 'contracts.json').read_text(encoding='utf8'))  # noqa: E501

    contract_entries.update(dxdao_contracts)
    for contract_key, items in contract_entries.items():
        if contract_key == 'ETH_MULTICALL':
            continue  # skip it as is superseded by multicall2

        serialized_abi = json.dumps(items['abi'], separators=(',', ':'))
        if contract_key == 'UNISWAP_V3_NFT_MANAGER':
            abi_id = _get_abi(cursor, 'ERC721_TOKEN')
        elif contract_key in MAKERDAO_ABI_GROUP_1:
            abi_id = _get_or_create_common_abi(
                cursor=cursor,
                name='MAKERDAO_JOIN_GROUP1',
                serialized_abi=serialized_abi,
            )
        elif contract_key in MAKERDAO_ABI_GROUP_2:
            abi_id = _get_or_create_common_abi(
                cursor=cursor,
                name='MAKERDAO_JOIN_GROUP2',
                serialized_abi=serialized_abi,
            )
        elif contract_key in MAKERDAO_ABI_GROUP_3:
            abi_id = _get_or_create_common_abi(
                cursor=cursor,
                name='MAKERDAO_JOIN_GROUP3',
                serialized_abi=serialized_abi,
            )
        elif contract_key in YEARN_ABI_GROUP_1:
            abi_id = _get_or_create_common_abi(
                cursor=cursor,
                name='YEARN_VAULTS_GROUP1',
                serialized_abi=serialized_abi,
            )
        elif contract_key in YEARN_ABI_GROUP_2:
            abi_id = _get_or_create_common_abi(
                cursor=cursor,
                name='YEARN_VAULTS_GROUP2',
                serialized_abi=serialized_abi,
            )
        elif contract_key in YEARN_ABI_GROUP_3:
            abi_id = _get_or_create_common_abi(
                cursor=cursor,
                name='YEARN_VAULTS_GROUP3',
                serialized_abi=serialized_abi,
            )
        elif contract_key in YEARN_ABI_GROUP_4:
            abi_id = _get_or_create_common_abi(
                cursor=cursor,
                name='YEARN_VAULTS_GROUP4',
                serialized_abi=serialized_abi,
            )
        else:  # need to add the abi to the DB
            if contract_key == 'ETH_SCAN':
                contract_key = 'BALANCE_SCAN'  # let's rename to non eth-specific  # noqa: E501, PLW2901
            elif contract_key == 'ETH_MULTICALL_2':
                contract_key = 'MULTICALL2'  # let's rename to non eth-specific  # noqa: E501, PLW2901
            abi_id = _insert_abi_return_id(
                cursor=cursor,
                name=contract_key,
                serialized_abi=serialized_abi,
            )

        if contract_key == 'BALANCE_SCAN':
            eth_scan_abi_id = abi_id
        elif contract_key == 'MULTICALL2':
            multicall_abi_id = abi_id
        elif contract_key == 'DS_PROXY_REGISTRY':
            ds_registry_abi_id = abi_id

        cursor.execute(
            'INSERT INTO contract_data(address, chain_id, name, abi, deployed_block) '
            'VALUES(?, ?, ?, ?, ?)',
            (items['address'], 1, contract_key, abi_id, items['deployed_block']),
        )

    if eth_scan_abi_id is None or multicall_abi_id is None or ds_registry_abi_id is None:
        raise DBUpgradeError(
            'Failed to find either eth_scan or multicall or ds registry abi id during '
            'v3->v4 global DB upgrade',
        )
    return eth_scan_abi_id, multicall_abi_id, ds_registry_abi_id


def _add_optimism_contracts(
        cursor: 'DBCursor',
        eth_scan_abi_id: int,
        multicall_abi_id: int,
        ds_registry_abi_id: int,
) -> None:
    cursor.executemany(
        'INSERT INTO contract_data(address, chain_id, name, abi, deployed_block) '
        'VALUES(?, ?, ?, ?, ?)',
        [(
            '0x1e21bc42FaF802A0F115dC998e2F0d522aDb1F68',
            10,
            'BALANCE_SCAN',
            eth_scan_abi_id,
            46787373,
        ), (
            '0x2DC0E2aa608532Da689e89e237dF582B783E552C',
            10,
            'MULTICALL2',
            multicall_abi_id,
            722566,
        ), (
            '0x283Cc5C26e53D66ed2Ea252D986F094B37E6e895',
            10,
            'DS_PROXY_REGISTRY',
            ds_registry_abi_id,
            2944824,
        )],
    )


def _copy_assets_from_packaged_db(
        cursor: 'DBCursor',
        assets_ids: list[str],
        root_dir: Path,
) -> None:
    """
    Copy missing assets from the packaged globaldb to the globaldb
    Since the upgrade happens when the connection to the globaldb hasn't been created yet we need
    to manually copy the assets information as we don't have the GlobalDBHandler object.

    We need to commit the changes here because otherwise the packaged globaldb is busy and we
    can't detach it. At this point all the information in the upgrade should be fine.

    TODO: This approach assumes that the schema in the packaged globaldb and the schema in v3 are
    the same. When this doesn't hold anymore we will ask users to use an intermediate
    version to upgrade.
    """
    packaged_db_path = root_dir / 'data' / 'global.db'
    identifiers_quotes = ','.join('?' * len(assets_ids))
    cursor.execute(f"ATTACH DATABASE '{packaged_db_path}' AS packaged_db;")
    cursor.execute(f'INSERT INTO assets SELECT * FROM packaged_db.assets WHERE identifier IN ({identifiers_quotes});', assets_ids)  # noqa: E501
    cursor.execute(f'INSERT INTO evm_tokens SELECT * FROM packaged_db.evm_tokens WHERE identifier IN ({identifiers_quotes});', assets_ids)  # noqa: E501
    cursor.execute(f'INSERT INTO common_asset_details SELECT * FROM packaged_db.common_asset_details WHERE identifier IN ({identifiers_quotes});', assets_ids)  # noqa: E501
    cursor.execute('COMMIT;')
    cursor.execute('DETACH DATABASE packaged_db;')


@enter_exit_debug_log(name='GlobalDB v3->v4 upgrade')
def migrate_to_v4(connection: 'DBConnection', progress_handler: 'DBUpgradeProgressHandler') -> None:  # noqa: E501
    """Upgrades globalDB to v4 by creating and populating the contract data + abi tables.

    Also making sure to not repeat existing abis. Ran a script to determine which
    abis are common between all contracts and encoding the output of these relations
    to the upgrade.

    eth_abi.json has no repeating ABIs
    """
    root_dir = Path(__file__).resolve().parent.parent.parent

    @progress_step('Adding new tables.')
    def _create_new_tables(cursor: 'DBCursor') -> None:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS contract_abi (
                id INTEGER NOT NULL PRIMARY KEY,
                value TEXT NOT NULL,
                name TEXT
            );""")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS contract_data (
                address VARCHAR[42] NOT NULL,
                chain_id INTEGER NOT NULL,
                name TEXT,
                abi INTEGER NOT NULL,
                deployed_block INTEGER,
                FOREIGN KEY(abi) REFERENCES contract_abi(id) ON UPDATE CASCADE ON DELETE SET NULL,
                PRIMARY KEY(address, chain_id)
            );""")

    @progress_step('Adding new ABIs.')
    def _add_eth_abis_json(cursor: 'DBCursor') -> None:
        root_dir = Path(__file__).resolve().parent.parent.parent
        abi_entries = json.loads((root_dir / 'data' / 'eth_abi.json').read_text(encoding='utf8'))
        abi_entries_tuples = []
        for name, value in abi_entries.items():
            abi_entries_tuples.append((name, json.dumps(value, separators=(',', ':'))))
        cursor.executemany('INSERT INTO contract_abi(name, value) VALUES(?, ?)', abi_entries_tuples)  # noqa: E501

    @progress_step('Adding new contracts.')
    def _add_new_contracts(cursor: 'DBCursor') -> None:
        eth_scan_abi_id, multicall_abi_id, ds_registry_abi_id = _add_eth_contracts_json(cursor)
        _add_optimism_contracts(cursor, eth_scan_abi_id, multicall_abi_id, ds_registry_abi_id)

    @progress_step('Populating asset collections.')
    def _populate_asset_collections(cursor: 'DBCursor') -> None:
        """Insert into the collections table the information about known collections"""
        cursor.execute((root_dir / 'data' / 'populate_asset_collections.sql').read_text(encoding='utf8'))  # noqa: E501

    @progress_step('Populating multiasset mappings.')
    def _populate_multiasset_mappings(cursor: 'DBCursor') -> None:
        """
        Insert into the assets_mappings table the information about each asset's collection
        If any of the assets that needs to go in the collections is missing we copy it from the
        packaged globaldb.
        """
        asset_regex = re.compile(r'eip155[a-zA-F0-9:\/]+')
        sql_sentences = (root_dir / 'data' / 'populate_multiasset_mappings.sql').read_text(encoding='utf8')  # noqa: E501
        # check if we are adding the assets
        # in this case we need to ensure that the assets exist locally and
        # if not copy them from the packaged db
        mapping_assets_identifiers = asset_regex.findall(sql_sentences)
        cursor.execute(
            f'SELECT identifier FROM assets WHERE identifier IN ({",".join("?" * len(mapping_assets_identifiers))})',  # noqa: E501
            mapping_assets_identifiers,
        )
        all_evm_assets = {entry[0] for entry in cursor}
        assets_to_add = set(mapping_assets_identifiers) - all_evm_assets

        if len(assets_to_add) != 0:
            try:
                _copy_assets_from_packaged_db(
                    cursor=cursor,
                    assets_ids=list(assets_to_add),
                    root_dir=root_dir,
                )
            except sqlite3.OperationalError as e:
                log.error(f'Failed to add missing assets for collections. Missing assets were {assets_to_add}. {e!s}')  # noqa: E501
                return

        cursor.execute(sql_sentences)

    @progress_step('Upgrading address book table.')
    def _upgrade_address_book_table(cursor: 'DBCursor') -> None:
        """Upgrades the address book table if it exists by making the blockchain column optional"""
        update_table_schema(
            write_cursor=cursor,
            table_name='address_book',
            schema="""address TEXT NOT NULL,
            blockchain TEXT,
            name TEXT NOT NULL,
            PRIMARY KEY(address, blockchain)""",
            insert_columns='address, blockchain, name',
        )

    @progress_step('Updating protocol name for yearn assets.')
    def _update_yearn_v1_protocol(cursor: 'DBCursor') -> None:
        """Update the protocol name for yearn assets"""
        cursor.execute("UPDATE evm_tokens SET protocol=? WHERE protocol='yearn-v1'", (YEARN_VAULTS_V1_PROTOCOL,))  # noqa: E501

    perform_globaldb_upgrade_steps(connection, progress_handler)
