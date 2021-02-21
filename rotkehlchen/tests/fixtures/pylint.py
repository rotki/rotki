import pytest
from pylint.testutils.unittest_linter import UnittestLinter


@pytest.fixture()
def pylint_test_linter():
    return UnittestLinter()
