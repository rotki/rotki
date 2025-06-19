import pytest

from rotkehlchen.exchanges.manager import ExchangeManager

from .binance import *  # noqa: F403
from .bitcoinde import *  # noqa: F403
from .bitfinex import *  # noqa: F403
from .bitmex import *  # noqa: F403
from .bitpanda import *  # noqa: F403
from .bitstamp import *  # noqa: F403
from .bybit import *  # noqa: F403
from .coinbase import *  # noqa: F403
from .cryptocom import *  # noqa: F403
from .gemini import *  # noqa: F403
from .htx import *  # noqa: F403
from .iconomi import *  # noqa: F403
from .independentreserve import *  # noqa: F403
from .kraken import *  # noqa: F403
from .kucoin import *  # noqa: F403
from .okx import *  # noqa: F403
from .poloniex import *  # noqa: F403
from .woo import *  # noqa: F403


@pytest.fixture(name='exchange_manager')
def fixture_exchange_manager(function_scope_messages_aggregator, database) -> ExchangeManager:
    exchange_manager = ExchangeManager(msg_aggregator=function_scope_messages_aggregator)
    exchange_manager.initialize_exchanges(exchange_credentials={}, database=database)
    return exchange_manager
