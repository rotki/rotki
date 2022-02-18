from typing import Any, Callable, Dict, List, Tuple

from rotkehlchen.types import ChecksumEthAddress


class DecoderInterface():

    def addresses_to_decoders(self) -> Dict[ChecksumEthAddress, Tuple[Any, ...]]:  # pylint: disable=no-self-use  # noqa: E501
        """Subclasses implement this to return the mappings of addresses to decode functions"""
        return {}

    def decoding_rules(self) -> List[Callable]:  # pylint: disable=no-self-use
        """
        Subclasses implement this to add new generic decoding rules to be attemped
        by the decoding process
        """
        return []
