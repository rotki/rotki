import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants.resolver import (
    ETHEREUM_DIRECTIVE,
    ETHEREUM_DIRECTIVE_LENGTH,
    ChainID,
    TokenKind,
    evm_address_to_identifier,
    strethaddress_to_identifier,
)
from rotkehlchen.logging import enter_exit_debug_log

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

log = logging.getLogger(__name__)

OTHER_EVM_CHAINS_ASSETS = {
    'SMG': 'eip155:56/erc20:0x6bfd576220e8444CA4Cc5f89Efbd7f02a4C94C16',
    'GSPI': 'eip155:56/erc20:0xB42e1c3902b85b410334f5fff79cDc51fBeE6950',
    'DINO': 'eip155:137/erc20:0xAa9654BECca45B5BDFA5ac646c939C62b527D394',
    'MDX': 'eip155:56/erc20:0x9C65AB58d8d978DB963e63f2bfB7121627e3a739',
    'SSG': 'eip155:56/erc20:0xA0c8c80ED6B7F09F885e826386440B2349F0Da7E',
    'bDOT': 'eip155:56/erc20:0x08bd7F9849f8EEC12fd78c9fED6ba4e47269e3d5',
    'MONI': 'eip155:56/erc20:0x9573c88aE3e37508f87649f87c4dd5373C9F31e0',
    'ALPINE': 'eip155:56/erc20:0x287880Ea252b52b63Cc5f40a2d3E5A44aa665a76',
    'PLATO': 'eip155:56/erc20:0xf2572fDACf09bfAE08FF7D35423870B5a8aC26b7',
    'WOOP': 'eip155:56/erc20:0x8b303d5BbfBbf46F1a4d9741E491e06986894e18',
    'TIME': 'eip155:43114/erc20:0xb54f16fB19478766A268F172C9480f8da1a7c9C3',
    'ITAMCUBE': 'eip155:56/erc20:0x9B08f10D8C250714F6485212300a7B72f973F1Fd',
    'OP': 'eip155:10/erc20:0x4200000000000000000000000000000000000042',
    'MV': 'eip155:137/erc20:0xA3c322Ad15218fBFAEd26bA7f616249f7705D945',
    'KARA': 'eip155:56/erc20:0x1e155e26085Be757780B45a5420D9f16a938f76b',
    'POSI': 'eip155:56/erc20:0x5CA42204cDaa70d5c773946e69dE942b85CA6706',
    'BLOK': 'eip155:137/erc20:0x229b1b6C23ff8953D663C4cBB519717e323a0a84',
    'NHCT': 'eip155:43114/erc20:0x3CE2fceC09879af073B53beF5f4D04327a1bC032',
    'BMON': 'eip155:56/erc20:0x08ba0619b1e7A582E0BCe5BBE9843322C954C340',
    'XAVA': 'eip155:43114/erc20:0xd1c3f94DE7e5B45fa4eDBBA472491a9f4B166FC4',
    'ALPACA': 'eip155:56/erc20:0x8F0528cE5eF7B51152A59745bEfDD91D97091d2F',
    'NBT': 'eip155:56/erc20:0x1D3437E570e93581Bd94b2fd8Fbf202d4a65654A',
    'QI': 'eip155:43114/erc20:0x8729438EB15e2C8B576fCc6AeCdA6A148776C0F5',
    'SANTOS': 'eip155:56/erc20:0xA64455a4553C9034236734FadDAddbb64aCE4Cc7',
    'LATTE': 'eip155:56/erc20:0xa269A9942086f5F87930499dC8317ccC9dF2b6CB',
    'LAVAX': 'eip155:56/erc20:0xa9BE3cd803Fa19F2af24412FF0a2a4a67a29dE88',
    'PLGR': 'eip155:56/erc20:0x6Aa91CbfE045f9D154050226fCc830ddbA886CED',
    'PORTO': 'eip155:56/erc20:0x49f2145d6366099e13B10FbF80646C0F377eE7f6',
    'H3RO3S': 'eip155:137/erc20:0x480fD103973357266813EcfcE9faABAbF3C4ca3A',
    'DREAMS': 'eip155:56/erc20:0x54523D5fB56803baC758E8B10b321748A77ae9e9',
    'FEVR': 'eip155:56/erc20:0x82030CDBD9e4B7c5bb0b811A61DA6360D69449cc',
    'WAL': 'eip155:56/erc20:0xd306c124282880858a634E7396383aE58d37c79c',
    'VAI': 'eip155:56/erc20:0x4BD17003473389A42DAF6a0a729f6Fdb328BbBd7',
    'GAFI': 'eip155:56/erc20:0x89Af13A10b32F1b2f8d1588f93027F69B6F4E27e',
    'MBOX': 'eip155:56/erc20:0x3203c9E46cA618C8C1cE5dC67e7e9D75f5da2377',
    'CATE': 'eip155:56/erc20:0xE4FAE3Faa8300810C835970b9187c268f55D998F',
    'ERTHA': 'eip155:56/erc20:0x62823659d09F9F9D2222058878f89437425eB261',
    'DAR': 'eip155:56/erc20:0x23CE9e926048273eF83be0A3A8Ba9Cb6D45cd978',
    'ETHO': 'eip155:100/erc20:0xB17d999E840e0c1B157Ca5Ab8039Bd958b5fA317',
    'BURGER': 'eip155:56/erc20:0xAe9269f27437f0fcBC232d39Ec814844a51d6b8f',
    'TAUM': 'eip155:56/erc20:0x02e22Eb7F6e73EF313DD71248cD164b1Bdc5aAdd',
    'CHESS': 'eip155:56/erc20:0x20de22029ab63cf9A7Cf5fEB2b737Ca1eE4c82A6',
    'FITFI': 'eip155:43114/erc20:0x714f020C54cc9D104B6F4f6998C63ce2a31D1888',
    'EPS': 'eip155:56/erc20:0xA7f552078dcC247C2684336020c03648500C6d9F',
    'SPARTA': 'eip155:56/erc20:0x3910db0600eA925F63C36DdB1351aB6E2c6eb102',
    'PNG': 'eip155:43114/erc20:0x60781C2586D68229fde47564546784ab3fACA982',
    'H2O': 'eip155:56/erc20:0xAF3287cAe99C982586c07401C0d911Bf7De6CD82',
    'POLYDOGE': 'eip155:137/erc20:0x8A953CfE442c5E8855cc6c61b1293FA648BAE472',
    'TKO': 'eip155:56/erc20:0x9f589e3eabe42ebC94A44727b3f3531C0c877809',
    'JOE': 'eip155:43114/erc20:0x6e84a6216eA6dACC71eE8E6b0a5B7322EEbC0fDd',
    'ARKER': 'eip155:56/erc20:0x9c67638c4Fa06FD47fB8900fC7F932f7EAB589De',
    'ROCO': 'eip155:43114/erc20:0xb2a85C5ECea99187A977aC34303b80AcbDdFa208',
    'REV3L': 'eip155:56/erc20:0x4ffA6BB42d1a1A6d8e79935CcF1457d55deCff3f',
    'YEFI': 'eip155:56/erc20:0x193B8230f594F63da50876EaF362177d1Dca4A45',
    'HERO': 'eip155:56/erc20:0xD40bEDb44C081D2935eebA6eF5a3c8A31A1bBE13',
    'ROSN': 'eip155:56/erc20:0x651Cd665bD558175A956fb3D72206eA08Eb3dF5b',
    'CRFI': 'eip155:56/erc20:0xAE20BC46300BAb5d85612C6BC6EA87eA0F186035',
    'BIFI': 'eip155:56/erc20:0xCa3F508B8e4Dd382eE878A314789373D80A5190A',
    'WSB': 'eip155:56/erc20:0x22168882276e5D5e1da694343b41DD7726eeb288',
    'IDIA': 'eip155:56/erc20:0x0b15Ddf19D47E6a86A56148fb4aFFFc6929BcB89',
    'DPET': 'eip155:56/erc20:0xfb62AE373acA027177D1c18Ee0862817f9080d08',
    'KLIMA': 'eip155:137/erc20:0x4e78011Ce80ee02d2c3e649Fb657E45898257815',
    'LACE': 'eip155:56/erc20:0xA3499dd7dBBBD93CB0f8303f8a8AcE8D02508E73',
    'GODZ': 'eip155:56/erc20:0xDa4714fEE90Ad7DE50bC185ccD06b175D23906c1',
    'TWT': 'eip155:56/erc20:0x4B0F1812e5Df2A09796481Ff14017e6005508003',
    'AUSD': 'eip155:56/erc20:0xDCEcf0664C33321CECA2effcE701E710A2D28A3F',
    'MQST': 'eip155:56/erc20:0xFD0ed86319BbF02359266d5Fa1cF10BC1720B2e0',
    'SCLP': 'eip155:56/erc20:0xF2c96E402c9199682d5dED26D3771c6B192c01af',
    'DLTA': 'eip155:56/erc20:0x3a06212763CAF64bf101DaA4b0cEbb0cD393fA1a',
    'ZPTC': 'eip155:56/erc20:0x39Ae6D231d831756079ec23589D2D37A739F2E89',
    'MTRG': 'eip155:56/erc20:0xBd2949F67DcdC549c6Ebe98696449Fa79D988A9F',
    'EPX': 'eip155:56/erc20:0xAf41054C1487b0e5E2B9250C0332eCBCe6CE9d71',
    'RACA': 'eip155:56/erc20:0x12BB890508c125661E03b09EC06E404bc9289040',
    'CAKE': 'eip155:56/erc20:0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82',
    'SON': 'eip155:56/erc20:0x3b0E967cE7712EC68131A809dB4f78ce9490e779',
    'MNST': 'eip155:56/erc20:0x6a6Ccf15B38DA4b5B0eF4C8fe9FefCB472A893F9',
    'BNX': 'eip155:56/erc20:0x8C851d1a123Ff703BD1f9dabe631b69902Df5f97',
    'SWINGBY': 'eip155:56/erc20:0x71DE20e0C4616E7fcBfDD3f875d568492cBE4739',
    'ARV': 'eip155:56/erc20:0x6679eB24F59dFe111864AEc72B443d1Da666B360',
    'BSW': 'eip155:56/erc20:0x965F527D9159dCe6288a2219DB51fc6Eef120dD1',
    'SIN': 'eip155:56/erc20:0x6397de0F9aEDc0F7A8Fa8B438DDE883B9c201010',
    'BRISE': 'eip155:56/erc20:0x8FFf93E810a2eDaaFc326eDEE51071DA9d398E83',
    'GGG': 'eip155:56/erc20:0xD8047AFECB86e44eFf3aDd991B9F063eD4ca716B',
    'CHMB': 'eip155:56/erc20:0x5492Ef6aEebA1A3896357359eF039a8B11621b45',
    'FALCONS': 'eip155:56/erc20:0xB139eD26b743C7254A246cf91eb594D097238524',
    'BAKE': 'eip155:56/erc20:0xE02dF9e3e622DeBdD69fb838bB799E3F168902c5',
    'XWG': 'eip155:56/erc20:0x6b23C89196DeB721e6Fd9726E6C76E4810a464bc',
    'XEP': 'eip155:56/erc20:0xb897D0a0f68800f8Be7D69ffDD1c24b69f57Bf3e',
    'RD': 'eip155:56/erc20:0x27eb4587783F2744c489aD2e64269A2e86daeB80',
    'SFUND': 'eip155:56/erc20:0x477bC8d23c634C154061869478bce96BE6045D12',
    'FLAME': 'eip155:137/erc20:0x22e3f02f86Bc8eA0D73718A2AE8851854e62adc5',
    'NFTB': 'eip155:56/erc20:0xde3dbBE30cfa9F437b293294d1fD64B26045C71A',
    'WRX': 'eip155:56/erc20:0x8e17ed70334C87eCE574C9d537BC153d8609e2a3',
    'ANI': 'eip155:56/erc20:0xaC472D0EED2B8a2f57a6E304eA7eBD8E88D1d36f',
    'NRV': 'eip155:56/erc20:0x42F6f551ae042cBe50C739158b4f0CAC0Edb9096',
    'IHC': 'eip155:56/erc20:0x86a53fcd199212FEa44FA7e16EB1f28812be911D',
    'OPS': 'eip155:56/erc20:0xDf0121a3bA5C10816eA2943C722650C4A4B0dbE6',
    'VOXEL': 'eip155:137/erc20:0xd0258a3fD00f38aa8090dfee343f10A9D4d30D3F',
    'SURV': 'eip155:56/erc20:0x1180C484f55024C5Ce1765101f4efaC1e7A3F6d4',
    'LAZIO': 'eip155:56/erc20:0x77d547256A2cD95F32F67aE0313E450Ac200648d',
    'XVS': 'eip155:56/erc20:0xcF6BB5389c92Bdda8a3747Ddb454cB7a64626C63',
    'GMM': 'eip155:56/erc20:0x5B6bf0c7f989dE824677cFBD507D9635965e9cD3',
    'SFP': 'eip155:56/erc20:0xD41FDb03Ba84762dD66a0af1a6C8540FF1ba5dfb',
    'STARLY': 'eip155:56/erc20:0xb0A480E2FA5AF51C733a0Af9FcB4De62Bc48c38B',
    'UPO': 'eip155:137/erc20:0x9dBfc1cbf7a1E711503a29B4b5F9130ebeCcaC96',
    'ELV': 'eip155:56/erc20:0xE942C48044FB1C7f4C9eB456f6097fa4A1A17B8f',
}
COMMON_ASSETS_INSERT = """INSERT OR IGNORE INTO common_asset_details(
    identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for
    ) VALUES(?, ?, ?, ?, ?, ?, ?)
"""
ASSETS_INSERT = """INSERT OR IGNORE INTO assets(
        identifier, name, type
    )VALUES(?, ?, ?);
"""
EVM_TOKEN_INSERT = """INSERT OR IGNORE INTO evm_tokens(
        identifier, token_kind, chain, address, decimals, protocol
    ) VALUES(?, ?, ?, ?, ?, ?)
"""
UNDERLYING_TOKEN_INSERT = """INSERT OR IGNORE INTO
    underlying_tokens_list(identifier, weight, parent_token_entry)
    VALUES (?, ?, ?)
"""
OWNED_ASSETS_INSERT = 'INSERT OR IGNORE INTO user_owned_assets(asset_id) VALUES (?);'
PRICES_INSERT = 'INSERT INTO price_history(from_asset, to_asset, source_type, timestamp, price) VALUES (?, ?, ?, ?, ?)'  # noqa: E501
BINANCE_INSERT = 'INSERT INTO binance_pairs(pair, base_asset, quote_asset, location) VALUES(?, ?, ?, ?)'  # noqa: E501


EVM_TUPLES_CREATION_TYPE = (
    tuple[
        list[tuple[str, str, int, str, Any, Any]],
        list[tuple[Any, Any, str]],
        list[tuple[Any, Any, Any, Any, None, Any, Any]],
    ]
)

ASSET_CREATION_TYPE = (
    tuple[
        list[tuple[Any, Any, Any]],
        list[tuple[Any, Any, Any, Any, Any, Any, Any]],
    ]
)


def _maybe_upgrade_identifier(identifier: str) -> str:
    """Change the identifier to the new format and return it.

    - If it's an ethereim token return its CAIP
    - If it's another known EVM chain identifier return its CAIP
    - Otherwise return unmodified
    """
    if identifier.startswith(ETHEREUM_DIRECTIVE):
        return strethaddress_to_identifier(identifier[ETHEREUM_DIRECTIVE_LENGTH:])

    maybe_other_chain_new_id = OTHER_EVM_CHAINS_ASSETS.get(identifier)
    return maybe_other_chain_new_id if maybe_other_chain_new_id is not None else identifier


def upgrade_ethereum_asset_ids_v3(cursor: 'DBCursor') -> EVM_TUPLES_CREATION_TYPE:
    """Query all the information available from ethereum tokens in
    the v2 schema to be used in v3"""
    result = cursor.execute(
        "SELECT A.address, A.decimals, A.protocol, B.identifier, B.name, B.symbol, B.started, "
        "B.swapped_for, B.coingecko, B.cryptocompare FROM assets "
        "AS B JOIN ethereum_tokens "
        "AS A ON A.address = B.details_reference WHERE B.type='C';",
    )
    query = result.fetchall()
    old_ethereum_data = []
    old_ethereum_id_to_new = {}
    evm_tuples = []
    assets_tuple = []
    common_asset_details = []

    for entry in query:
        new_id = evm_address_to_identifier(
            address=entry[0],
            chain_id=ChainID.ETHEREUM,
            token_type=TokenKind.ERC20,
            collectible_id=None,
        )
        old_ethereum_id_to_new[entry[3]] = new_id
        old_ethereum_data.append((new_id, *entry))

    for entry in old_ethereum_data:
        evm_tuples.append((
            str(entry[0]),  # identifier
            TokenKind.ERC20.serialize_for_db(),  # token type
            ChainID.ETHEREUM.value,  # chain
            str(entry[1]),  # address
            entry[2],  # decimals
            entry[3],  # protocol
        ))
        new_swapped_for = old_ethereum_id_to_new.get(entry[8])
        if new_swapped_for is not None:
            new_swapped_for = _maybe_upgrade_identifier(entry[8])
            old_ethereum_id_to_new[entry[8]] = new_swapped_for

        assets_tuple.append((
            entry[0],  # identifier
            entry[5],  # name
            AssetType.EVM_TOKEN.serialize_for_db(),  # type
        ))
        common_asset_details.append((
            entry[0],  # identifier
            entry[6],  # symbol
            entry[9],  # coingecko
            entry[10],  # cryptocompare
            None,  # forked, none for eth
            entry[7],  # started
            new_swapped_for,  # swapped for
        ))

    return (
        evm_tuples,
        assets_tuple,
        common_asset_details,
    )


def upgrade_other_assets(cursor: 'DBCursor') -> ASSET_CREATION_TYPE:
    """Create the bindings tuple for the assets and common_asset_details tables using the
    information from the V2 tables for non ethereum assets"""
    result = cursor.execute(
        'SELECT A.identifier, A.type, A.name, A.symbol, A.started, A.swapped_for, A.coingecko, '
        'A.cryptocompare, B.forked FROM assets as A JOIN common_asset_details AS B '
        'ON B.asset_id=A.identifier WHERE A.type!=?',
        ('C', ),
    )

    assets_tuple = []
    common_asset_details = []
    for entry in result:
        if entry[0] in OTHER_EVM_CHAINS_ASSETS:
            continue
        swapped_for = entry[5]
        if swapped_for is not None:
            swapped_for = _maybe_upgrade_identifier(swapped_for)

        assets_tuple.append((
            entry[0],  # identifier
            entry[2],  # name
            entry[1],  # type
        ))
        common_asset_details.append((
            entry[0],  # identifier
            entry[3],  # symbol
            entry[6],  # coingecko
            entry[7],  # cryptocompare
            entry[8],  # forked
            entry[4],  # started
            swapped_for,
        ))

    return (
        assets_tuple,
        common_asset_details,
    )


def translate_underlying_table(cursor: 'DBCursor') -> list[tuple[str, str, str]]:
    """Get information about the underlying tokens and upgrade it to the V3 schema from the
    information in the v2 schema"""
    query = cursor.execute(
        'SELECT address, weight, parent_token_entry FROM underlying_tokens_list;',
    )
    mappings = []
    for row in query:
        new_address = evm_address_to_identifier(
            address=row[0],
            chain_id=ChainID.ETHEREUM,
            token_type=TokenKind.ERC20,
            collectible_id=None,
        )
        new_parent = evm_address_to_identifier(
            address=row[2],
            chain_id=ChainID.ETHEREUM,
            token_type=TokenKind.ERC20,
            collectible_id=None,
        )
        mappings.append((new_address, row[1], new_parent))
    return mappings


def translate_owned_assets(cursor: 'DBCursor') -> list[tuple[str]]:
    """Collect and update assets in the user_owned_assets tables to use the new id format"""
    cursor.execute('SELECT asset_id from user_owned_assets;')
    owned_assets = []
    for (asset_id,) in cursor:
        owned_assets.append((_maybe_upgrade_identifier(asset_id),))
    return owned_assets


def translate_binance_pairs(cursor: 'DBCursor') -> list[tuple[str, str, str, str]]:
    """Collect and update assets in the binance_pairs tables to use the new id format"""
    table_exists = cursor.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='binance_pairs'",
    ).fetchone()[0]
    if table_exists == 0:  # handle binance_pairs not having been created
        cursor.execute(  # fix https://github.com/rotki/rotki/issues/5073
            """CREATE TABLE IF NOT EXISTS binance_pairs (
            pair TEXT NOT NULL,
            base_asset TEXT NOT NULL,
            quote_asset TEXT NOT NULL,
            location TEXT NOT NULL,
            FOREIGN KEY(base_asset) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
            FOREIGN KEY(quote_asset) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
            PRIMARY KEY(pair, location)
            );""",  # noqa: E501
        )
        return []

    cursor.execute('SELECT pair, base_asset, quote_asset, location from binance_pairs;')
    binance_pairs = []
    for entry in cursor:
        new_base = _maybe_upgrade_identifier(entry[1])
        new_quote = _maybe_upgrade_identifier(entry[2])
        binance_pairs.append((entry[0], new_base, new_quote, entry[3]))

    return binance_pairs


def translate_assets_in_price_table(cursor: 'DBCursor') -> list[tuple[str, str, str, int, str]]:
    """
    Translate the asset ids in the price table.

    Also drop all non manually input asset prices since otherwise this upgrade
    will take forever for a heavily used globaldb
    """
    assets = (
        'ETH',
        'ETH2',
        'BTC',
        'BCH',
        'ETC',
        'DOT',
        'KSM',
    )
    cursor.execute(
        f"SELECT from_asset, to_asset, source_type, timestamp, price FROM "
        f"price_history WHERE (source_type=='A' OR from_asset IN ({','.join(['?'] * len(assets))}))",  # noqa: E501
        assets,
    )
    updated_rows = []
    for (from_asset, to_asset, source_type, timestamp, price) in cursor:
        new_from_asset = _maybe_upgrade_identifier(from_asset)
        new_to_asset = _maybe_upgrade_identifier(to_asset)
        updated_rows.append((new_from_asset, new_to_asset, source_type, timestamp, price))

    return updated_rows


@enter_exit_debug_log(name='GlobalDB v2->v3 upgrade')
def migrate_to_v3(connection: 'DBConnection', progress_handler: 'DBUpgradeProgressHandler') -> None:  # noqa: E501
    """Upgrade assets information and migrate globaldb to version 3

    At the adding steps to the global DB upgrades, skipped this one. Too old
    and not organized in functions. Will go away soon anyway.
    """
    with connection.read_ctx() as cursor:
        log.debug('Obtain ethereum assets information')
        evm_tuples, assets_tuple, common_asset_details = upgrade_ethereum_asset_ids_v3(cursor)
        mappings = translate_underlying_table(cursor)
        log.debug('Upgrade other and owned assets')
        assets_tuple_others, common_asset_details_others = upgrade_other_assets(cursor)
        owned_assets = translate_owned_assets(cursor)
        log.debug('Upgrade prices')
        updated_prices = translate_assets_in_price_table(cursor)
        log.debug('Upgrade binance pairs')
        updated_binance_pairs = translate_binance_pairs(cursor)

    with connection.write_ctx() as cursor:
        log.debug('Purge/delete tables with outdated information')
        # Some of these tables like user_owned_assets are recreated in an identical state but are
        # dropped and recreated since they have references to a table that is dropped and modified
        cursor.switch_foreign_keys('OFF')
        cursor.execute('DROP TABLE IF EXISTS user_owned_assets')
        cursor.execute('DROP TABLE IF EXISTS assets')
        cursor.execute('DROP TABLE IF EXISTS ethereum_tokens')
        cursor.execute('DROP TABLE IF EXISTS evm_tokens')
        cursor.execute('DROP TABLE IF EXISTS common_asset_details')
        cursor.execute('DROP TABLE IF EXISTS underlying_tokens_list')
        cursor.execute('DROP TABLE IF EXISTS price_history')
        cursor.execute('DROP TABLE IF EXISTS binance_pairs')
        cursor.switch_foreign_keys('ON')

        log.debug('Create new tables')
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS token_kinds (
          token_kind    CHAR(1)       PRIMARY KEY NOT NULL,
          seq     INTEGER UNIQUE
        );""")
        # ERC20
        cursor.execute("INSERT OR IGNORE INTO token_kinds(token_kind, seq) VALUES ('A', 1)")
        # ERC721
        cursor.execute("INSERT OR IGNORE INTO token_kinds(token_kind, seq) VALUES ('B', 2)")
        # UNKNOWN
        cursor.execute("INSERT OR IGNORE INTO token_kinds(token_kind, seq) VALUES ('C', 3)")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            identifier TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
            name TEXT,
            type CHAR(1) NOT NULL DEFAULT('A') REFERENCES asset_types(type)
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS common_asset_details(
            identifier TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
            symbol TEXT,
            coingecko TEXT,
            cryptocompare TEXT,
            forked TEXT,
            started INTEGER,
            swapped_for TEXT,
            FOREIGN KEY(forked) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE SET NULL,
            FOREIGN KEY(identifier) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
            FOREIGN KEY(swapped_for) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE SET NULL
        );
        """)  # noqa: E501
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS evm_tokens (
            identifier TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
            token_kind CHAR(1) NOT NULL DEFAULT('A') REFERENCES token_kinds(token_kind),
            chain INTEGER NOT NULL,
            address VARCHAR[42] NOT NULL,
            decimals INTEGER,
            protocol TEXT,
            FOREIGN KEY(identifier) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE
        );
        """)  # noqa: E501
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS multiasset_mappings(
            collection_id INTEGER NOT NULL,
            asset TEXT NOT NULL,
            FOREIGN KEY(collection_id) REFERENCES asset_collections(id) ON UPDATE CASCADE ON DELETE CASCADE,
            FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE
        );
        """)  # noqa: E501
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_owned_assets (
            asset_id VARCHAR[24] NOT NULL PRIMARY KEY,
            FOREIGN KEY(asset_id) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS underlying_tokens_list (
            identifier TEXT NOT NULL,
            weight TEXT NOT NULL,
            parent_token_entry TEXT NOT NULL,
            FOREIGN KEY(parent_token_entry) REFERENCES evm_tokens(identifier)
                ON DELETE CASCADE ON UPDATE CASCADE
            FOREIGN KEY(identifier) REFERENCES evm_tokens(identifier) ON UPDATE CASCADE ON DELETE CASCADE
            PRIMARY KEY(identifier, parent_token_entry)
        );
        """)  # noqa: E501
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            from_asset TEXT NOT NULL COLLATE NOCASE,
            to_asset TEXT NOT NULL COLLATE NOCASE,
            source_type CHAR(1) NOT NULL DEFAULT('A') REFERENCES price_history_source_types(type),
            timestamp INTEGER NOT NULL,
            price TEXT NOT NULL,
            FOREIGN KEY(from_asset) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
            FOREIGN KEY(to_asset) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
            PRIMARY KEY(from_asset, to_asset, source_type, timestamp)
        );
        """)  # noqa: E501
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS asset_collections(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            symbol TEXT NOT NULL
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_assets(
            identifier TEXT NOT NULL PRIMARY KEY,
            notes TEXT,
            type TEXT NOT NULL COLLATE NOCASE,
            FOREIGN KEY(identifier) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE
        );
        """)  # noqa: E501
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS binance_pairs (
        pair TEXT NOT NULL,
        base_asset TEXT NOT NULL,
        quote_asset TEXT NOT NULL,
        location TEXT NOT NULL,
        FOREIGN KEY(base_asset) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
        FOREIGN KEY(quote_asset) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
        PRIMARY KEY(pair, location)
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS general_cache (
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            last_queried_ts INTEGER NOT NULL,
            PRIMARY KEY(key, value)
        );
        """)

        cursor.switch_foreign_keys('OFF')
        log.debug('Input common asset data')
        cursor.executemany(COMMON_ASSETS_INSERT, common_asset_details)
        cursor.executemany(COMMON_ASSETS_INSERT, common_asset_details_others)
        log.debug('Input asset data')
        cursor.executemany(ASSETS_INSERT, assets_tuple)
        cursor.executemany(ASSETS_INSERT, assets_tuple_others)
        cursor.executemany(OWNED_ASSETS_INSERT, owned_assets)
        log.debug('Input prices')
        cursor.executemany(PRICES_INSERT, updated_prices)
        log.debug('Input binance pairs')
        cursor.executemany(BINANCE_INSERT, updated_binance_pairs)
        cursor.switch_foreign_keys('ON')
        log.debug('Input evm and underlying tokens')
        cursor.executemany(EVM_TOKEN_INSERT, evm_tuples)
        cursor.executemany(UNDERLYING_TOKEN_INSERT, mappings)
        # Add `custom asset` asset type
        cursor.execute("INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('[', 27)")
        # Add manual current price source and defillama
        cursor.execute("INSERT OR IGNORE INTO price_history_source_types(type, seq) VALUES ('E', 5)")  # noqa: E501
        cursor.execute("INSERT OR IGNORE INTO price_history_source_types(type, seq) VALUES ('F', 6)")  # noqa: E501

        dir_path = Path(__file__).resolve().parent.parent.parent
        # This file contains the EVM version of the assets that are currently in the
        # database and are not EVM (matic tokens, Optimism tokens, etc) + their variants in
        # other chains. And populates them properly via sql statements
        raw_sql_sentences = (dir_path / 'data' / 'globaldb_v2_v3_assets.sql').read_text(encoding='utf8')  # noqa: E501
        per_table_sentences = raw_sql_sentences.split('\n\n')
        for sql_sentences in per_table_sentences:
            cursor.execute(sql_sentences)
