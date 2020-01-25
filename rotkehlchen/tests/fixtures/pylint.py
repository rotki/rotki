import pytest
from pylint.testutils import UnittestLinter


@pytest.fixture()
def pylint_test_linter():
    return UnittestLinter()
