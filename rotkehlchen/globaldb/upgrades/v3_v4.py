import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from rotkehlchen.errors.misc import DBUpgradeError
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor

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


def _create_new_tables(cursor: 'DBCursor') -> None:
    log.debug('Enter _create_new_tables')

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

    log.debug('Exit _create_new_tables')


def _add_eth_abis_json(cursor: 'DBCursor') -> None:
    log.debug('Enter _add_eth_abis_json')

    root_dir = Path(__file__).resolve().parent.parent.parent
    with open(root_dir / 'data' / 'eth_abi.json') as f:
        abi_entries = json.loads(f.read())

    abi_entries_tuples = []
    for name, value in abi_entries.items():
        abi_entries_tuples.append((name, json.dumps(value, separators=(',', ':'))))
    cursor.executemany('INSERT INTO contract_abi(name, value) VALUES(?, ?)', abi_entries_tuples)  # noqa: E501

    log.debug('Exit _add_eth_abis_json')


def _add_eth_contracts_json(cursor: 'DBCursor') -> tuple[int, int]:
    log.debug('Enter _add_eth_contracts_json')

    eth_scan_abi_id, multicall_abi_id = None, None
    root_dir = Path(__file__).resolve().parent.parent.parent
    with open(root_dir / 'data' / 'eth_contracts.json') as f:
        contract_entries = json.loads(f.read())
    with open(root_dir / 'chain' / 'ethereum' / 'modules' / 'dxdaomesa' / 'data' / 'contracts.json') as f:  # noqa: E501
        dxdao_contracts = json.loads(f.read())

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
                contract_key = 'BALANCE_SCAN'  # let's rename to non eth-specific
            elif contract_key == 'ETH_MULTICALL_2':
                contract_key = 'MULTICALL2'  # let's rename to non eth-specific
            abi_id = _insert_abi_return_id(
                cursor=cursor,
                name=contract_key,
                serialized_abi=serialized_abi,
            )

        if contract_key == 'BALANCE_SCAN':
            eth_scan_abi_id = abi_id
        elif contract_key == 'MULTICALL2':
            multicall_abi_id = abi_id

        cursor.execute(
            'INSERT INTO contract_data(address, chain_id, name, abi, deployed_block) '
            'VALUES(?, ?, ?, ?, ?)',
            (items['address'], 1, contract_key, abi_id, items['deployed_block']),
        )

    if eth_scan_abi_id is None or multicall_abi_id is None:
        raise DBUpgradeError(
            'Failed to find either eth_scan or multicall abi id during v3->v4 global DB upgrade',
        )

    log.debug('Exit _add_eth_contracts_json')
    return eth_scan_abi_id, multicall_abi_id


def _add_optimism_contracts(cursor: 'DBCursor', eth_scan_abi_id: int, multicall_abi_id: int) -> None:  # noqa: E501
    log.debug('Enter _add_optimism_contracts')

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
        )],
    )

    log.debug('Exit _add_optimism_contracts')


def migrate_to_v4(connection: 'DBConnection') -> None:
    """Upgrades globalDB to v4 by creating and populating the contract data + abi tables.

    Also making sure to not repeat existing abis. Ran a script to determine which
    abis are common between all contracts and encoding the output of these relations
    to the upgrade.

    eth_abi.json has no repeating ABIs
    """
    log.debug('Entered globaldb v3->v4 upgrade')
    with connection.write_ctx() as cursor:
        _create_new_tables(cursor)
        _add_eth_abis_json(cursor)
        eth_scan_abi_id, multicall_abi_id = _add_eth_contracts_json(cursor)
        _add_optimism_contracts(cursor, eth_scan_abi_id, multicall_abi_id)

    log.debug('Finished globaldb v3->v4 upgrade')
