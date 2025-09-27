from contextlib import suppress

from astroid.exceptions import InferenceError
from pylint.checkers import BaseChecker

LOGNOKWARGS_SYMBOL = 'rotki-lognokwargs'
LOGNOKWARGS_MSG = (
    'Normal loggers can not receive kwargs. To pass kwargs to a logger please '
    'use RotkehlchenLogsAdapter.'
)


def is_normal_logging_call(inferred_func):
    return (
        inferred_func.name in {'info', 'debug', 'error', 'warning'} and
        inferred_func.callable() and
        inferred_func.parent.name == 'Logger'
    )


def register(linter):
    linter.register_checker(LogNokwargsChecker(linter))


class LogNokwargsChecker(BaseChecker):
    """A pylint custom checker to detect if we ever use kwargs in a normal Logger call"""

    name = 'lognokwargs'
    priority = -1
    msgs = {  # noqa: RUF012  # can't control library's base class typing
        'E9001': (
            LOGNOKWARGS_MSG,
            LOGNOKWARGS_SYMBOL,
            'Message Help is empty',
        ),
    }

    def visit_call(self, node):
        """Called on expressions of the form `expr()`, where `expr` is a simple
        name e.g. `f()` or a path e.g. `v.f()`.
        """
        with suppress(InferenceError):
            self._detect_normal_logs_with_kwargs(node)

    def _detect_normal_logs_with_kwargs(self, node):
        """This stops usages of the form:

            >>> logger = logging.getLogger(__name__)
            >>> logger.debug('foo', a=1)

            but allows usage of
            >>> logger = logging.getLogger(__name__)
            >>> log = RotkehlchenLogsAdapter(logger)
            >>> log.debug('foo', a=1)
        """
        for inferred_func in node.func.infer():
            if is_normal_logging_call(inferred_func) and node.keywords:
                self.add_message(LOGNOKWARGS_SYMBOL, node=node)
