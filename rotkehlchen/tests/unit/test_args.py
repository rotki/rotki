import pytest

from rotkehlchen.args import app_args
from rotkehlchen.constants.misc import DEFAULT_SQL_VM_INSTRUCTIONS_CB


@pytest.fixture(name='argparser')
def fixture_appargs():
    arg_parser = app_args(
        prog='rotki',
        description=(
            'rotki, the portfolio tracker and accounting tool that respects your privacy'
        ),
    )
    return arg_parser


def test_arg_sql_vm_instructions_cb(argparser):
    with pytest.raises(SystemExit):
        argparser.parse_args(['--sqlite-instructions', '-3'])

    with pytest.raises(SystemExit):
        argparser.parse_args(['--sqlite-instructions', 'dsad'])

    args = argparser.parse_args(['--data-dir', 'foo'])
    assert args.sqlite_instructions == DEFAULT_SQL_VM_INSTRUCTIONS_CB
    args = argparser.parse_args(['--sqlite-instructions', '200'])
    assert args.sqlite_instructions == 200
    args = argparser.parse_args(['--sqlite-instructions', '0'])
    assert args.sqlite_instructions == 0
