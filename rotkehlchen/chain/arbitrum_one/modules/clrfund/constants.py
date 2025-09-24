from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails

CPT_CLRFUND: Final = 'clrfund'
REQUEST_SUBMITTED_ABI = '{"anonymous":false,"inputs":[{"indexed":true,"internalType":"bytes32","name":"_recipientId","type":"bytes32"},{"indexed":true,"internalType":"enum OptimisticRecipientRegistry.RequestType","name":"_type","type":"uint8"},{"indexed":false,"internalType":"address","name":"_recipient","type":"address"},{"indexed":false,"internalType":"string","name":"_metadata","type":"string"},{"indexed":false,"internalType":"uint256","name":"_timestamp","type":"uint256"}],"name":"RequestSubmitted","type":"event"}'  # noqa: E501

CLRFUND_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_CLRFUND,
    label='Clrfund',
    image='clrfund.png',
)
