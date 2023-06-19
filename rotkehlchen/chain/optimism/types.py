from typing import Any, NamedTuple, Optional

from rotkehlchen.types import ChainID, ChecksumEvmAddress, EVMTxHash, Timestamp

class OptimismTransaction(NamedTuple):
    """Represent an Optimism transaction"""
    tx_hash: EVMTxHash
    chain_id: ChainID
    timestamp: Timestamp
    block_number: int
    from_address: ChecksumEvmAddress
    to_address: Optional[ChecksumEvmAddress]
    value: int
    gas: int
    gas_price: int
    gas_used: int
    input_data: bytes
    nonce: int
    l1_fee: Optional[int]

    def serialize(self) -> dict[str, Any]:
        result = self._asdict()  # pylint: disable=no-member
        result['tx_hash'] = result['tx_hash'].hex()
        result['evm_chain'] = result.pop('chain_id').to_name()
        result['input_data'] = '0x' + result['input_data'].hex()

        # Most integers are turned to string to be sent via the API
        result['value'] = str(result['value'])
        result['gas'] = str(result['gas'])
        result['gas_price'] = str(result['gas_price'])
        result['gas_used'] = str(result['gas_used'])
        result['l1_fee'] = str(result['l1_fee'])
        return result

    def __hash__(self) -> int:
        return hash(self.identifier)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, OptimismTransaction):
            return False

        return hash(self) == hash(other)

    @property
    def identifier(self) -> str:
        return str(self.chain_id.value) + self.tx_hash.hex()
