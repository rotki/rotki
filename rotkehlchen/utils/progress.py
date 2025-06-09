import functools
import os
import sys
from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

from rotkehlchen.logging import enter_exit_debug_log

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBConnection
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


def progress_step(description: str) -> Callable:
    """Decorates a function with a description attribute and applies the enter/exit debug log too.

    Used by DB upgrade and migration for each step
    """
    def step_decorator(function: Callable) -> Callable:
        function._description = description  # type: ignore  # we are creating the attribute

        @enter_exit_debug_log(name=function.__name__)
        @wraps(function)
        def step_wrapped(*args: Any, **kwargs: Any) -> Any:
            return function(*args, **kwargs)
        return step_wrapped
    return step_decorator


def gather_caller_functions(depth: int) -> list[tuple[Callable, Callable]]:
    """Find all functions of the caller scope

    Returns a list of tuples. Each tuple contains the function and the
    original function after all wrapping from decorators and closures is cleared.
    """
    def get_original_func(obj: Callable) -> Callable:
        """Since a function can be wrapped (and in our use-case is)
        with complex decorators, unwrap it and get the original function"""
        if isinstance(obj, functools.partial):
            return get_original_func(obj.func)

        for attr in ['__wrapped__', '__func__', 'func', '__closure__']:
            if hasattr(obj, attr):
                attr_value = getattr(obj, attr)
                if callable(attr_value):
                    return get_original_func(attr_value)
                elif attr == '__closure__' and attr_value:
                    # Check if any cell in the closure contains a function
                    for cell in attr_value:
                        if callable(cell.cell_contents):
                            return get_original_func(cell.cell_contents)

        # If we can't find the original function, return the object itself
        return obj

    def is_function_from_module(func: Callable, module_name: str) -> bool:
        """Check various attributes that might indicate the function's origin"""
        if getattr(func, '__module__', None) == module_name:
            return True
        if getattr(func, '__globals__', {}).get('__name__') == module_name:
            return True
        if getattr(func, '__code__', None) and getattr(func.__code__, 'co_filename', None):
            # This checks if the function's code object is from a file in the same directory
            # as the caller's module. This is a heuristic and might need adjustment.
            caller_file = caller_frame.f_code.co_filename
            func_file = func.__code__.co_filename
            return os.path.dirname(caller_file) == os.path.dirname(func_file)
        return False

    caller_frame = sys._getframe(depth)  # Get the frame of the caller
    caller_locals = caller_frame.f_locals
    caller_module = caller_frame.f_globals.get('__name__')
    step_functions = []
    for obj in caller_locals.values():
        if callable(obj):
            original_func = get_original_func(obj)
            # Check if the original function is defined in the caller's module
            if caller_module and is_function_from_module(original_func, caller_module) and hasattr(original_func, '_description'):  # noqa: E501
                step_functions.append((obj, original_func))

    return step_functions


def perform_userdb_upgrade_steps(
        db: 'DBHandler',
        progress_handler: 'DBUpgradeProgressHandler',
        should_vacuum: bool = False,
) -> None:
    """Performs caller introspection and gathers the userDB upgrade steps. Sets the total,
    calls each step along with its description and if needed performs a VACUUM at the end
    NB: The function definition order is the function calling order"""
    step_functions = gather_caller_functions(depth=2)
    progress_handler.set_total_steps(len(step_functions) + (1 if should_vacuum else 0))
    with db.user_write() as write_cursor:
        for function, original_function in step_functions:
            progress_handler.new_step(original_function._description)  # type: ignore  # we do confirm all gathered functions have the attribute
            function(write_cursor)

    if should_vacuum:  # TODO: Probably can generalize this to a given post-transaction step
        progress_handler.new_step('Vacuuming database.')
        db.conn.execute('VACUUM;')


def perform_globaldb_upgrade_steps(
        connection: 'DBConnection',
        progress_handler: 'DBUpgradeProgressHandler',
        should_vacuum: bool = False,
) -> None:
    """Performs caller introspection and gathers the globalDB upgrade steps.

    TODO: Very similar to userdb upgrade. Only difference is we use connection alone
    here while in userb we use db.user_write(). Perhaps figure out a way to better abstract it?
    """
    step_functions = gather_caller_functions(depth=2)
    progress_handler.set_total_steps(len(step_functions) + (1 if should_vacuum else 0))
    with connection.write_ctx() as write_cursor:
        for function, original_function in step_functions:
            progress_handler.new_step(original_function._description)  # type: ignore  # we do confirm all gathered functions have the attribute
            function(write_cursor)

    if should_vacuum:  # TODO: Probably can generalize this to a given post-transaction step
        progress_handler.new_step('Vacuuming database.')
        connection.execute('VACUUM;')


def perform_userdb_migration_steps(
        rotki: 'Rotkehlchen',
        progress_handler: 'MigrationProgressHandler',
        should_vacuum: bool = False,
) -> None:
    """Performs caller introspection and gathers the userDB migration steps. Sets the total,
    calls each step along with its description.

    NB: The function definition order is the function calling order"""
    step_functions = gather_caller_functions(depth=2)
    progress_handler.set_total_steps(len(step_functions) + (1 if should_vacuum else 0))
    for function, original_function in step_functions:
        progress_handler.new_step(original_function._description)  # type: ignore  # we do confirm all gathered functions have the attribute
        function(rotki)

    if should_vacuum:  # TODO: Probably can generalize this to a given post-transaction step
        progress_handler.new_step('Vacuuming database.')
        rotki.data.db.conn.execute('VACUUM;')
