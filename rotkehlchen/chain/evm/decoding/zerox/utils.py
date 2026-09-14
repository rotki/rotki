from typing import TYPE_CHECKING, Final

from eth_utils import keccak, to_checksum_address

if TYPE_CHECKING:
    from rotkehlchen.types import ChainID, ChecksumEvmAddress

# The 0x Settler deployer/registry lives at the same address on every chain and deploys
# each new Settler instance via CREATE2 of a shim (salt: feature << 128 | chain id << 64
# | deploy nonce), which then CREATEs the Settler as its first transaction. The address
# of every past and future Settler instance is therefore computable offline:
# https://github.com/0xProject/0x-settler#how-do-i-find-the-most-recent-deployment
SETTLER_DEPLOYER: Final = b'\x00\x00\x00\x00\x00\x00\x04S?\xe1UV\xb1\xe0\x86\xbb\x1ar\xce\xae'  # 0x00000000000004533Fe15556B1E086BB1A72cEae  # noqa: E501
# Shim init code hash for chains supporting the Cancun hardfork, which is every chain rotki
# decodes 0x on. London-only chains use
# 0x1774bbdc4a308eaf5967722c7a4708ea7a3097859cb8768a10611448c29981c3 instead.
SETTLER_SHIM_INIT_CODE_HASH: Final = b';\xf3\xf9\x7f\x0b\xe1\xe2\xc0\x00#\x03>\xef\xebO\xc0b\xacU/\xf3gx\xb1p`\xd9\x0bgd\x90/'  # 0x3bf3f97f0be1e2c00023033eefeb4fc062ac552ff36778b17060d90b6764902f  # noqa: E501
# The deployer's feature id for the taker submitted Settler, the one users send swaps to.
# Metatransaction (3), intents (4) and bridge (5) settlers are not decoded yet.
SETTLER_TAKER_SUBMITTED_FEATURE: Final = 2
# Deploy nonces are sequential per feature and chain. Mainnet is at 19 after two and a
# half years (Sept 2026), so this bound covers well over a decade of deployments at a
# cost of two keccaks per nonce at decoder initialization.
SETTLER_MAX_DEPLOY_NONCE: Final = 128


def compute_settler_address(chain_id: ChainID, feature: int, nonce: int) -> ChecksumEvmAddress:
    """Compute the address of the 0x Settler deployed for the given feature with the given
    deploy nonce on the given chain. This is the Python version of computeGenuineSettler()
    from the 0x-settler README."""
    salt = ((feature << 128) | (chain_id.value << 64) | nonce).to_bytes(32, 'big')
    shim = keccak(b'\xff' + SETTLER_DEPLOYER + salt + SETTLER_SHIM_INIT_CODE_HASH)[12:]
    # CREATE address of the shim's first transaction: keccak(rlp([shim, 1]))[12:]
    return to_checksum_address(keccak(b'\xd6\x94' + shim + b'\x01')[12:])


def generate_settler_addresses(chain_id: ChainID) -> set[ChecksumEvmAddress]:
    """Return the addresses of all taker submitted 0x Settler deployments on the given chain,
    including ones not deployed yet, so that new deployments are decoded without any code
    change. The 0x docs explicitly say not to hardcode Settler addresses."""
    return {
        compute_settler_address(chain_id=chain_id, feature=SETTLER_TAKER_SUBMITTED_FEATURE, nonce=nonce)  # noqa: E501
        for nonce in range(1, SETTLER_MAX_DEPLOY_NONCE + 1)
    }
