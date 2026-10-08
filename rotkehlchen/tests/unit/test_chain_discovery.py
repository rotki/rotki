from rotkehlchen.chain.discovery import discover_submodules

ETHEREUM_MODULES = 'rotkehlchen.chain.ethereum.modules'


def test_discover_submodules_lists_nested_packages_after_their_parent():
    names = [name for name, _ in discover_submodules(ETHEREUM_MODULES, 'decoder')]
    assert names.index('.curve') < names.index('.curve.crvusd') < names.index('.curve.lend')
    assert all(name.startswith('.') for name in names)


def test_discover_submodules_returns_the_requested_module():
    modules = discover_submodules(ETHEREUM_MODULES, 'decoder')
    assert len(modules) != 0
    assert all(module.__name__.endswith('.decoder') for _, module in modules)
    assert any(module.__name__ == f'{ETHEREUM_MODULES}.curve.crvusd.decoder' for _, module in modules)  # noqa: E501


def test_discover_submodules_walks_each_root_once():
    assert discover_submodules(ETHEREUM_MODULES, 'accountant') is discover_submodules(ETHEREUM_MODULES, 'accountant')  # noqa: E501
