from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

SUSHI_ROUTE_PROCESSORS: Final = (  # https://docs.sushi.com/docs/Products/Route%20Processor
    string_to_evm_address('0x83eC81Ae54dD8dca17C3Dd4703141599090751D1'),
)
