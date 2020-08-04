from unittest.mock import patch

import gevent

from rotkehlchen.chain.ethereum.zerion import ZERION_ADAPTER_ADDRESS
from rotkehlchen.chain.manager import ChainManager
from rotkehlchen.typing import ChecksumEthAddress


def create_zerion_patch():
    target = 'rotkehlchen.chain.ethereum.zerion.query_zerion_address'
    return patch(target, side_effect=mock_query_zerion_address)


def mock_query_zerion_address(ethereum, msg_aggregator) -> ChecksumEthAddress:
    return ZERION_ADAPTER_ADDRESS


def wait_until_zerion_is_initialized(chain_manager: ChainManager) -> None:
    """Since chain manager initializes zerion asynchonously, this function makes
    sure that we wait until it's initialized.

    This is required for example so that the mocking of the querying of the zerion
    address can still be in effect"""
    with gevent.Timeout(5):
        while True:
            if chain_manager.zerion is None:
                gevent.sleep(.1)
            else:
                break
