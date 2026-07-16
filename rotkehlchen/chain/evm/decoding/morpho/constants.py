from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from eth_typing import ABI

CPT_MORPHO: Final = 'morpho'
MORPHO_VAULT_ABI: ABI = [{'inputs': [{'name': 'shares', 'type': 'uint256'}], 'name': 'convertToAssets', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501
