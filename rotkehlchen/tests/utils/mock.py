from typing import Dict

from hexbytes import HexBytes


class MockResponse():
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text
        self.content = text.encode()
        self.url = 'http://someurl.com'


class MockEth():

    syncing = False

    def __init__(self, block_number: int) -> None:
        self.blockNumber = block_number
        self.chainId = 1

    def getBlock(self, number: int) -> Dict[str, HexBytes]:  # noqa: N802
        """Always return genesis block since this is what we care about in the tests"""
        genesis = (
            b'\xd4\xe5g@\xf8v\xae\xf8\xc0\x10\xb8j@\xd5\xf5gE\xa1\x18\xd0\x90j4'
            b'\xe6\x9a\xec\x8c\r\xb1\xcb\x8f\xa3'
        )
        return {'hash': HexBytes(genesis)}


class MockWeb3():

    def __init__(self, providers=None, middlewares=None):
        self.eth = MockEth(0)

    def isConnected(self):  # noqa: N802
        return True
