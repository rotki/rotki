from typing import Optional

from requests_html import HTMLSession


class GlobalRequestsHTML():
    """A global wrapper around requests_html HTMLSession

    Since this is used in many places and we should only initialize it once we have
    this global object that lives for as long as the app runs.

    The reason for the existence of this global object is that requests_html session
    creates a browser instance to render javascript and re-doing this every time a
    request happens is too much.
    """
    __instance: Optional['GlobalRequestsHTML'] = None
    _session: HTMLSession

    def __new__(cls) -> 'GlobalRequestsHTML':
        if GlobalRequestsHTML.__instance is not None:
            return GlobalRequestsHTML.__instance

        GlobalRequestsHTML.__instance = object.__new__(cls)
        GlobalRequestsHTML._session = HTMLSession()
        return GlobalRequestsHTML.__instance

    @staticmethod
    def session() -> HTMLSession:
        return GlobalRequestsHTML()._session

    @staticmethod
    def close() -> None:
        instance = GlobalRequestsHTML()
        instance._session.close()
