from typing import Final

from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails

CPT_SPARK: Final = 'spark'
SPARK_COUNTERPARTY_LABEL: Final = 'Spark'
SPARK_COUNTERPARTY_DETAILS = CounterpartyDetails(
    identifier=CPT_SPARK,
    label=SPARK_COUNTERPARTY_LABEL,
    image='spark.svg',
)
