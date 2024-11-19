import importlib.util
import inspect
import sys
from pathlib import Path
from typing import TypeVar

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.rotkehlchen import BalancesTestSetup
from rotkehlchen.utils.misc import from_wei, satoshis_to_btc


def get_asset_balance_total(asset: Asset, setup: BalancesTestSetup) -> FVal:
    conversion_function = satoshis_to_btc if asset == A_BTC else from_wei
    total = ZERO

    if asset in (A_ETH, A_BTC):
        asset_balances = getattr(
            setup,
            f'{asset.resolve_to_asset_with_symbol().symbol.lower()}_balances',
        )
        total += sum(conversion_function(FVal(b)) for b in asset_balances)
    elif asset.is_evm_token():
        asset_balances = setup.token_balances[asset.resolve_to_evm_token()]
        total += sum(conversion_function(FVal(b)) for b in asset_balances)

    if asset.is_asset_with_oracles():
        total += setup.binance_balances.get(asset.resolve_to_asset_with_oracles(), ZERO)
        total += setup.poloniex_balances.get(asset.resolve_to_asset_with_oracles(), ZERO)

    if setup.manually_tracked_balances:
        for entry in setup.manually_tracked_balances:
            if entry.asset == asset:
                total += entry.amount

    return total


T = TypeVar('T')


def find_inheriting_classes(
        root_directory: Path,
        search_directory: Path,
        base_class: type[T],
        exclude_class_names: set[str],
        exclude_dirs: set[str] | None = None,
) -> set[type[T]]:
    """
    Recursively find all classes in a directory that inherit from a specific base class.
    Limit only to non-abstract classes and non-common classes.

    Args:
        rootdirectory: The project root
        search_directory: Search directory to start searching from
        base_class: The base class to check inheritance against
        exclude_class_names: The names of classes to exclude. These are needed
        since unfortunately common classes are not seen as abstract.
        exclude_dirs: Set of directory names to exclude from search

    Returns:
        List of classes that inherit from base_class
    """
    inheriting_classes = set()
    if exclude_dirs is None:
        exclude_dirs = {'.git', '.venv', '__pycache__', 'venv', 'env'}

    # Add the root directory to Python path to help with imports
    if root_directory not in sys.path:
        sys.path.insert(0, str(root_directory))

    def get_module_name(file_path: Path) -> str:
        """Generate the full module name from the file path."""
        rel_path = file_path.relative_to(root_directory.parent)
        module_parts = list(rel_path.parent.parts) + [rel_path.stem]
        return '.'.join(module_parts)

    for path in search_directory.rglob('*.py'):
        if any(part in exclude_dirs for part in path.parts):  # skip excluded paths
            continue

        # Generate proper module name based on file path
        module_name = get_module_name(path)
        # Check if module is already loaded
        if module_name in sys.modules:
            module = sys.modules[module_name]
        else:
            # Load the module
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module  # Add to sys.modules before executing
            spec.loader.exec_module(module)

        # Inspect all members and find classes that match our criteria
        for name, obj in inspect.getmembers(module):
            if (
                    inspect.isclass(obj) and
                    issubclass(obj, base_class) and
                    name not in exclude_class_names and
                    not inspect.isabstract(obj) and
                    obj != base_class
            ):
                inheriting_classes.add(obj)

    return inheriting_classes
