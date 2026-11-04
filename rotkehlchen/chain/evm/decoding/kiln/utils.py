from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.utils import get_vault_price
from rotkehlchen.utils.misc import bytes_to_address

from .constants import EIP1967_BEACON_SLOT, KILN_VAULT_ABI

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.inquirer import Inquirer
    from rotkehlchen.types import ChecksumEvmAddress, Price


def has_beacon(
        evm_inquirer: EvmNodeInquirer,
        address: ChecksumEvmAddress,
        beacon: ChecksumEvmAddress,
) -> bool:
    """Whether the given beacon proxy uses the given beacon.

    May raise:
    - RemoteError if the storage could not be read
    """
    return bytes_to_address(evm_inquirer.get_storage_at(
        account_address=address,
        position=EIP1967_BEACON_SLOT,
    )) == beacon


def get_kiln_vault_token_price(
        inquirer: Inquirer,
        vault_token: EvmToken,
        evm_inquirer: EvmNodeInquirer,
) -> Price:
    """Price a Kiln DeFi vault share as the underlying assets one share converts to"""
    return get_vault_price(
        inquirer=inquirer,
        vault_token=vault_token,
        evm_inquirer=evm_inquirer,
        display_name='Kiln DeFi',
        vault_abi=KILN_VAULT_ABI,
        pps_method='convertToAssets',
        pps_method_args=[10 ** vault_token.get_decimals()],  # one share
    )
