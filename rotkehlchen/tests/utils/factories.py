import base64
import random
import string
from typing import Optional

from eth_utils.address import to_checksum_address

from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_ethereum_address
from rotkehlchen.typing import ApiKey, ApiSecret, ChecksumEthAddress, Timestamp
from rotkehlchen.utils.misc import ts_now

DEFAULT_START_TS = Timestamp(1451606400)


def make_random_bytes(size: int) -> bytes:
    return bytes(bytearray(random.getrandbits(8) for _ in range(size)))


def make_random_b64bytes(size: int) -> bytes:
    return base64.b64encode(make_random_bytes(size))


def make_random_uppercasenumeric_string(size: int) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=size))


def make_random_positive_fval(max_num: int = 1000000) -> FVal:
    return FVal(random.uniform(0, max_num))


def make_random_timestamp(
        start: Optional[Timestamp] = DEFAULT_START_TS,
        end: Optional[Timestamp] = None,
) -> Timestamp:
    if end is None:
        end = ts_now()
    if start is None:
        start = DEFAULT_START_TS
    return Timestamp(random.randint(start, end))


def make_api_key() -> ApiKey:
    return ApiKey(make_random_b64bytes(128).decode())


def make_api_secret() -> ApiSecret:
    return ApiSecret(base64.b64encode(make_random_b64bytes(128)))


def make_ethereum_address() -> ChecksumEthAddress:
    return to_checksum_address('0x' + make_random_bytes(20).hex())


UNIT_BTC_ADDRESS1 = '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2'
UNIT_BTC_ADDRESS2 = '1CounterpartyXXXXXXXXXXXXXXXUWLpVr'
UNIT_BTC_ADDRESS3 = '18ddjB7HWTVxzvTbLp1nWvaBxU3U2oTZF2'

ZERO_ETH_ADDRESS = deserialize_ethereum_address('0x' + '0' * 40)
