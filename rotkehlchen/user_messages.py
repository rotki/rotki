import logging
from collections import deque
from typing import List

logger = logging.getLogger(__name__)


class MessagesAggregator():
    """
    This class is passed around where needed and aggreggates messages for the user
    """

    def __init__(self):
        self.warnings = deque()
        self.errors = deque()

    def add_warning(self, msg: str):
        logger.warning(msg)
        self.warnings.appendleft(msg)

    def consume_warnings(self) -> List[str]:
        result = []
        while len(self.warnings) != 0:
            result.append(self.warnings.pop())

    def add_error(self, msg: str):
        logger.error(msg)
        self.error.appendleft(msg)

    def consume_errors(self) -> List[str]:
        result = []
        while len(self.errors) != 0:
            result.append(self.errors.pop())
