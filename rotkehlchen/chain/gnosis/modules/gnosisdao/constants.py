from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_GNOSISDAO: Final = 'gnosisdao'
GNOSISDAO_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_GNOSISDAO,
    label='GnosisDAO',
    image='gnosis.svg',
)

# Contracts of the GIP-151 one-time pro-rata treasury redemption
# https://forum.gnosis.io/t/gip-151-should-gnosisdao-offer-a-one-time-pro-rata-treasury-redemption/12337
REDEMPTION_DEPOSIT_ADDRESS: Final = string_to_evm_address('0xB53e4a513C1fbb11a66Da851643126D933489C4D')  # noqa: E501
REDEMPTION_DISTRIBUTOR_ADDRESS: Final = string_to_evm_address('0x09b2D4403385C992C5FBE0e1368193951Fa3F67D')  # noqa: E501
GNOSISDAO_TREASURY_SAFE: Final = string_to_evm_address('0xD8cD32876624bE785E7CbdA82bC93f585e8b1C2D')  # noqa: E501

DEPOSITED_TOPIC: Final = b'\x87R\xa4r\xe5q\xa8\x16\xae\xa9.\xec\x8d\xae\x9b\xafb\x8e\x84\x0fI)\xfb\xcc-\x15^b3\xffh\xa7'  # noqa: E501
CLAIMED_TOPIC: Final = b'(\xeeVk\xde\xca\xf9u\xc0\x97\x9fM\t\xfe\xcf\x91\xa9\x00\x9f\xfexR:\xef\x05:g\x814\x13{\x8b'  # noqa: E501
