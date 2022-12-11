import pytest

from rotkehlchen.tests.utils.xpubs import setup_db_for_xpub_tests_impl


@pytest.fixture(name='setup_db_for_xpub_tests')
def fixture_setup_db_for_xpub_tests(data_dir, username, sql_vm_instructions_cb):
    return setup_db_for_xpub_tests_impl(data_dir, username, sql_vm_instructions_cb)
