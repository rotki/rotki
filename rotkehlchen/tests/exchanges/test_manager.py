import inspect
from importlib import import_module

from rotkehlchen.exchanges.constants import SUPPORTED_EXCHANGES
from rotkehlchen.exchanges.manager import ExchangeManager

EXCHANGE_METHODS_TO_CHECK = (
    'query_balances',
    'query_online_deposits_withdrawals',
    'query_online_margin_history',
)


def test_all_methods_implemented():
    """Tests all methods needed by the exchange interface are implemented by all exchanges"""

    for name in SUPPORTED_EXCHANGES:
        module_name = ExchangeManager._get_exchange_module_name(name)
        try:
            module = import_module(f'rotkehlchen.exchanges.{module_name}')
        except ModuleNotFoundError:
            # This should never happen
            raise AssertionError(
                f'Tried to initialize unknown exchange {name}. Should never happen.',
            ) from None

        exchange_object = getattr(module, module_name.capitalize())
        members = inspect.getmembers(exchange_object)
        methods = [x for x in members if x[0] in EXCHANGE_METHODS_TO_CHECK]
        for method_name, method in methods:
            code = inspect.getsource(method)
            msg = f'{method_name} for exchange {name} is not implemented'
            assert 'raise NotImplementedError' not in code, msg
