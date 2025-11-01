from types import SimpleNamespace
from unittest.mock import MagicMock

from eth_utils import to_checksum_address

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.modules.lido.constants import CPT_LIDO
from rotkehlchen.chain.ethereum.modules.lido_csm.balances import LidoCsmBalances
from rotkehlchen.db.lido_csm import LidoCsmNodeOperator
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.types import ChainID
from rotkehlchen.constants.assets import A_STETH


def _make_evm_inquirer():
    return SimpleNamespace(
        database=MagicMock(),
        chain_id=ChainID.ETHEREUM,
    )


def test_lido_csm_balances_accumulates(monkeypatch):
    entry = LidoCsmNodeOperator(
        address=to_checksum_address('0xABCD00000000000000000000000000000000ABCD'),
        node_operator_id=9,
    )
    node_db = MagicMock(get_node_operators=MagicMock(return_value=(entry,)))
    balances = LidoCsmBalances(
        evm_inquirer=_make_evm_inquirer(),
        tx_decoder=MagicMock(),
        node_operator_db=node_db,
    )

    monkeypatch.setattr(
        LidoCsmBalances,
        '_get_bond_shares',
        lambda self, node_operator_id: 1_000_000_000_000_000_000,
    )
    monkeypatch.setattr(
        LidoCsmBalances,
        '_convert_shares_to_steth',
        lambda self, shares: FVal('1.5'),
    )
    monkeypatch.setattr(
        Inquirer,
        'find_usd_price',
        staticmethod(lambda asset: FVal('2000')),
    )

    result = balances.query_balances()
    steth_token = A_STETH.resolve_to_evm_token()
    assert result[entry.address].assets[steth_token][CPT_LIDO] == Balance(
        amount=FVal('1.5'),
        usd_value=FVal('3000'),
    )


def test_lido_csm_balances_skips_on_error(monkeypatch):
    entry = LidoCsmNodeOperator(
        address=to_checksum_address('0x1234500000000000000000000000000000006789'),
        node_operator_id=5,
    )
    node_db = MagicMock(get_node_operators=MagicMock(return_value=(entry,)))
    balances = LidoCsmBalances(
        evm_inquirer=_make_evm_inquirer(),
        tx_decoder=MagicMock(),
        node_operator_db=node_db,
    )

    def _raise_remote_error(*_args, **_kwargs):
        raise RemoteError('boom')

    monkeypatch.setattr(LidoCsmBalances, '_get_bond_shares', _raise_remote_error)
    monkeypatch.setattr(
        Inquirer,
        'find_usd_price',
        staticmethod(lambda asset: FVal('2000')),
    )

    result = balances.query_balances()
    assert len(result) == 0
