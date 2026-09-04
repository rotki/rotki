from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_ZERION: Final = 'zerion'
ZERION_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_ZERION,
    label='Zerion',
    image='zerion.png',
)

# The Zerion DeFi SDK Router. Every user interaction is a call to its startExecution(),
# which pulls the inputs from the user and hands them to the Core contract.
ZERION_ROUTER: Final = string_to_evm_address('0xB2BE281e8b11b47FeC825973fc8BB95332022A54')
# The Zerion DeFi SDK Core. It runs the protocol adapters (Uniswap, Curve, yearn, ...) and
# sends the outputs back to the user, emitting an ExecutedAction log per adapter step.
ZERION_CORE: Final = string_to_evm_address('0xD291328a6c202c5B18dCB24f279f69dE1E065f70')
# ExecutedAction((bytes32,uint8,(address,uint256,uint8)[],bytes))
# 0x5c416a271db2ac40f70515df028f580eeb1e2f7be2e656664553b83d9e15a039
EXECUTED_ACTION: Final = b"\\Aj'\x1d\xb2\xac@\xf7\x05\x15\xdf\x02\x8fX\x0e\xeb\x1e/{\xe2\xe6VfES\xb8=\x9e\x15\xa09"  # noqa: E501
