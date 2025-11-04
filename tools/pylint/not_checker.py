# Some example checkers that have complicated logic
# https://github.com/PyCQA/pylint/tree/master/pylint/checkers

import astroid
from pylint.checkers import BaseChecker, utils

NONBOOLEANNOT_SYMBOL = 'rotki-nonbooleannot'
NONBOOLEANNOT_MSG = 'Do not use the not operator with non boolean values'


def register(linter):
    linter.register_checker(NotBooleanChecker(linter))


class NotBooleanChecker(BaseChecker):
    """A pylint custom checker to detect if we use not for non boolean values"""

    name = 'nonbooleannot'
    priority = -1
    msgs = {  # noqa: RUF012  # can't control library's base class typing
        'E9011': (
            NONBOOLEANNOT_MSG,
            NONBOOLEANNOT_SYMBOL,
            'Message Help is empty',
        ),
    }

    def visit_unaryop(self, node):
        self._detect_nonboolean_not(node)

    def _detect_nonboolean_not(self, node):
        if node.op != 'not':
            return

        if isinstance(node.operand, astroid.Call):
            operand_type = utils.node_type(node.operand.func)
            operand_type = operand_type.returns if operand_type else None
            if isinstance(operand_type, astroid.Subscript):
                # This means return is like Optional[Something]. Ignore these cases
                # as it's not possible to determine the type as far as I can see
                return
        else:
            operand_type = utils.node_type(node.operand)

        if operand_type is None:
            return

        if hasattr(operand_type, 'name') and operand_type.name != 'bool':
            self.add_message(NONBOOLEANNOT_SYMBOL, node=node)
