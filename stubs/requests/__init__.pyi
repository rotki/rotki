from .sessions import Session
from .exceptions import ConnectionError

def get(url, params=None, **kwargs):...

def session():...


class Response:
    status_code: int
    url: str
    @property
    def text(self)->str:...
