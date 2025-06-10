import logging
import re
from typing import TYPE_CHECKING, Any

from rotkehlchen.errors.misc import DBSchemaError

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.logging import RotkehlchenLogger


logger: 'RotkehlchenLogger' = logging.getLogger(__name__)  # type: ignore

DEFAULT_SANITY_CHECK_MESSAGE = (
    'If you have manually edited the db please undo it. Otherwise open an issue in our '
    'github or contact us in our discord server.'
)

WHITESPACE_RE = re.compile(
    r'//.*?\n|/\*.*?\*/',
    re.DOTALL | re.MULTILINE,
)


def db_script_normalizer(text: str) -> str:
    """Normalize the string for comparison of the DB schema. That means removing all
    C/C++ style comments, whitespaces, newlines and moving all to lowercase
    """
    def replacer(match: Any) -> str:
        s = match.group(0)
        if s.startswith('/'):
            return ' '  # note: a space and not an empty string
        # else
        return s

    return WHITESPACE_RE.sub(replacer, text).replace(' ', '').replace('\n', '').replace('"', "'").replace('\t', '').lower()  # noqa: E501


async def sanity_check_impl(
        cursor: 'DBCursor',
        db_name: str,
        minimized_schema: dict[str, str],
) -> None:
    """The implementation of the DB sanity check. Out of DBConnection to keep things cleaner"""
    await cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
    tables_data_from_db: dict[str, tuple[str, str]] = {}
    rows = await cursor.fetchall()
    for (name, raw_script) in rows:
        table_properties = re.findall(
            pattern=r'createtable.*?\((.+)\)',
            string=db_script_normalizer(raw_script),
        )[0]
        # Store table properties for comparison with expected table structure and
        # raw_script for the ease of debugging
        tables_data_from_db[name] = (table_properties, raw_script)

    # Check that there are no extra structures such as views
    await cursor.execute(
        "SELECT type, name, sql FROM sqlite_master WHERE type NOT IN ('table', 'index')",
    )
    extra_db_structures = await cursor.fetchall()
    if len(extra_db_structures) > 0:
        logger.critical(
            f'Unexpected structures in {db_name} database: {extra_db_structures}',
        )
        raise DBSchemaError(
            f'There are unexpected structures in your {db_name} database. '
            f'Check the logs for more details. ' + DEFAULT_SANITY_CHECK_MESSAGE,
        )

    # Check what tables are missing from the db
    missing_tables = minimized_schema.keys() - tables_data_from_db.keys()
    if len(missing_tables) > 0:
        raise DBSchemaError(
            f'Tables {missing_tables} are missing from your {db_name} '
            f'database. ' + DEFAULT_SANITY_CHECK_MESSAGE,
        )

    # Check what extra tables are in the db
    extra_tables = tables_data_from_db.keys() - minimized_schema.keys()
    if len(extra_tables) > 0:
        logger.info(
            f'Your {db_name} database has the following unexpected tables: '
            f'{extra_tables}. Feel free to delete them.',
        )
        for extra_table in extra_tables:
            tables_data_from_db.pop(extra_table)

    # Check structure of which tables in the database differ from the expected.
    differing_tables_properties: dict[str, tuple[tuple[str, str], str]] = {}
    # At this point keys of two dictionaries match
    for table_name, table_data in tables_data_from_db.items():
        if table_data[0] != minimized_schema[table_name].lower():
            differing_tables_properties[table_name] = (
                table_data,
                minimized_schema[table_name],
            )

    if len(differing_tables_properties) > 0:
        log_msg = f'Differing tables in the {db_name} database are:'
        for table_name, ((raw_script, minimized_script), structure_expected) in differing_tables_properties.items():  # noqa: E501
            log_msg += (f'\n- For table {table_name} expected {structure_expected} but found {minimized_script}. Table raw script is: {raw_script}')  # noqa: E501
        logger.critical(log_msg)
        raise DBSchemaError(
            f'Structure of some tables in your {db_name} database differ from the '
            f'expected. Check the logs for more details. ' + DEFAULT_SANITY_CHECK_MESSAGE,
        )
