from typing import Dict, Union
from rotkehlchen.typing import ApiKey


class Session:
    def __init__(self):
        self.headers: Dict[str, Union[str, ApiKey]] = dict()

def session() -> Session: ...
