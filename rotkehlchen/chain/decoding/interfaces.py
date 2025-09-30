from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from .tools import BaseDecoderTools

if TYPE_CHECKING:
    from .types import CounterpartyDetails

T_Address = TypeVar('T_Address')
T_NodeInquirer = TypeVar('T_NodeInquirer')
T_DecoderTools = TypeVar('T_DecoderTools', bound=BaseDecoderTools)


class DecoderInterface(ABC, Generic[T_Address, T_NodeInquirer, T_DecoderTools]):

    def __init__(self, node_inquirer: 'T_NodeInquirer', base_tools: 'T_DecoderTools') -> None:
        self.base = base_tools
        self.node_inquirer = node_inquirer

    def addresses_to_decoders(self) -> dict[T_Address, tuple[Any, ...]]:
        """Subclasses may implement this to return the mappings of contract/program addresses
        to corresponding decoder functions.
        """
        return {}

    @staticmethod
    @abstractmethod
    def counterparties() -> tuple['CounterpartyDetails', ...]:
        """Subclasses implement this to specify which counterparties they introduce."""
