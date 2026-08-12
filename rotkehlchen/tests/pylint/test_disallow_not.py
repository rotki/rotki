from typing import TYPE_CHECKING

import astroid

from tools.pylint import NotBooleanChecker

if TYPE_CHECKING:
    from pylint.testutils.unittest_linter import UnittestLinter


def test_detect_list_as_nonboolean_not(pylint_test_linter: UnittestLinter) -> None:
    checker = NotBooleanChecker(linter=pylint_test_linter)
    node = astroid.extract_node("""
    a = []
    not a #@
    """)
    checker.visit_unaryop(node)  # type: ignore[no-untyped-call]  # tools.pylint is not typed
    messages = pylint_test_linter.release_messages()
    assert len(messages) == 1


def test_detect_dict_as_nonboolean_not(pylint_test_linter: UnittestLinter) -> None:
    checker = NotBooleanChecker(linter=pylint_test_linter)
    node = astroid.extract_node("""
    a = {}
    not a #@
    """)
    checker.visit_unaryop(node)  # type: ignore[no-untyped-call]  # tools.pylint is not typed
    messages = pylint_test_linter.release_messages()
    assert len(messages) == 1


def test_boolean_does_not_trigger_checker(pylint_test_linter: UnittestLinter) -> None:
    checker = NotBooleanChecker(linter=pylint_test_linter)
    node = astroid.extract_node("""
    a = False
    not a #@
    """)
    checker.visit_unaryop(node)  # type: ignore[no-untyped-call]  # tools.pylint is not typed
    messages = pylint_test_linter.release_messages()
    assert len(messages) == 0


def test_isinstance_does_not_trigger_checker(pylint_test_linter: UnittestLinter) -> None:
    checker = NotBooleanChecker(linter=pylint_test_linter)
    node = astroid.extract_node("""
    a = 5
    not isinstance(a, str) #@
    """)
    checker.visit_unaryop(node)  # type: ignore[no-untyped-call]  # tools.pylint is not typed
    messages = pylint_test_linter.release_messages()
    assert len(messages) == 0


def test_boolean_function_does_not_trigger_checker(pylint_test_linter: UnittestLinter) -> None:
    checker = NotBooleanChecker(linter=pylint_test_linter)
    node = astroid.extract_node("""
    def foo() -> bool:
        return True
    not foo() #@
    """)
    checker.visit_unaryop(node)  # type: ignore[no-untyped-call]  # tools.pylint is not typed
    messages = pylint_test_linter.release_messages()
    assert len(messages) == 0


def test_subscript_function_does_not_crash_checker(pylint_test_linter: UnittestLinter) -> None:
    checker = NotBooleanChecker(linter=pylint_test_linter)
    node = astroid.extract_node("""
    def foo() -> Optional[object]:
        return object()
    not foo() #@
    """)
    checker.visit_unaryop(node)  # type: ignore[no-untyped-call]  # tools.pylint is not typed
    messages = pylint_test_linter.release_messages()
    assert len(messages) == 0
