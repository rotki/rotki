import logging
from collections import deque
from typing import Deque, List

logger = logging.getLogger(__name__)


class MessagesAggregator():
    """
    This class is passed around where needed and aggreggates messages for the user
    """

    def __init__(self) -> None:
        self.warnings: Deque = deque()
        self.errors: Deque = deque()

    def add_warning(self, msg: str) -> None:
        logger.warning(msg)
        self.warnings.appendleft(msg)

    def consume_warnings(self) -> List[str]:
        result = []
        while len(self.warnings) != 0:
            result.append(self.warnings.pop())
        return result

    def add_error(self, msg: str) -> None:
        logger.error(msg)
        self.errors.appendleft(msg)

    def consume_errors(self) -> List[str]:
        result = []
        while len(self.errors) != 0:
            result.append(self.errors.pop())
        return result
