from typing import TYPE_CHECKING

from eth_utils import to_checksum_address

from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.types import ChainID, ChecksumEvmAddress, GeneralCacheType

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


def read_fraxlend_pairs() -> set[ChecksumEvmAddress]:
    """Reads globaldb cache and returns a set of all known frax lend pairs' addresses.
    Doesn't raise anything unless cache entries were inserted incorrectly."""
    fraxlend_pairs = GlobalDBHandler().get_general_cache_values(
        key_parts=[GeneralCacheType.FRAXLEND_PAIRS],
    )
    return set(map(string_to_evm_address, fraxlend_pairs))


def ensure_fraxlend_tokens_existence(
        ethereum_inquirer: 'EthereumInquirer',
        pairs: list[ChecksumEvmAddress],
) -> None:
    """This function receives data about frax lend pairs and ensures that pair tokens
    exist in rotki's database."""
    for pair_address in pairs:
        abi = ethereum_inquirer.contracts.abi('FRAXLEND_PAIR')
        collateral_address = ethereum_inquirer.call_contract(
            contract_address=pair_address,
            abi=abi,
            method_name='collateralContract',
        )
        get_or_create_evm_token(
            userdb=ethereum_inquirer.database,
            evm_address=to_checksum_address(collateral_address),
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=ethereum_inquirer,
        )
        asset_address = ethereum_inquirer.call_contract(
            contract_address=pair_address,
            abi=abi,
            method_name='asset',
        )
        get_or_create_evm_token(
            userdb=ethereum_inquirer.database,
            evm_address=to_checksum_address(asset_address),
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=ethereum_inquirer,
        )


def save_fraxlend_pairs_to_cache(
        write_cursor: DBCursor,
        pairs: list[ChecksumEvmAddress],
) -> None:
    """Receives data about frax lend pairs and saves in cache."""
    GlobalDBHandler().delete_general_cache(
        write_cursor=write_cursor,
        key_parts=[GeneralCacheType.FRAXLEND_PAIRS],
    )
    GlobalDBHandler().set_general_cache_values(
        write_cursor=write_cursor,
        key_parts=[GeneralCacheType.FRAXLEND_PAIRS],
        values=pairs,
    )


def query_fraxlend_pairs(
        ethereum: 'EthereumInquirer',
) -> list[ChecksumEvmAddress]:
    fraxlend_pair_deployer = ethereum.contracts.contract('FRAXLEND_PAIR_DEPLOYER')
    pairs_result = fraxlend_pair_deployer.call(
        node_inquirer=ethereum,
        method_name='getAllPairAddresses',
    )
    return list(map(to_checksum_address, pairs_result))
