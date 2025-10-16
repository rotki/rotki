import logging
import re
from typing import TYPE_CHECKING, Any

from rotkehlchen.errors.misc import DBSchemaError

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor
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


def sanity_check_impl(
        cursor: 'DBCursor',
        db_name: str,
        minimized_schema: dict[str, str],
        minimized_indexes: dict[str, str],
) -> None:
    """The implementation of the DB sanity check. Out of DBConnection to keep things cleaner"""
    # Fetch all tables and indexes from the database
    db_objects: dict[str, dict[str, tuple[str, str]]] = {'table': {}, 'index': {}}
    # Fetch tables
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
    for (name, raw_script) in cursor:
        table_properties = re.findall(
            pattern=r'createtable.*?\((.+)\)',
            string=db_script_normalizer(raw_script),
        )[0]
        db_objects['table'][name] = (table_properties, raw_script)

    # Fetch indexes (excluding auto-generated ones)
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL")
    for (name, raw_script) in cursor:
        normalized_script = db_script_normalizer(raw_script).replace('createindexifnotexists', 'createindex').replace('createuniqueindexifnotexists', 'createuniqueindex')  # noqa: E501
        db_objects['index'][name] = (normalized_script, raw_script)

    # Check for extra structures such as views
    extra_db_structures = cursor.execute(
        "SELECT type, name, sql FROM sqlite_master WHERE type NOT IN ('table', 'index')",
    ).fetchall()

    # Prepare all error and warning messages
    errors = []
    warnings = []
    info_msgs = []

    if extra_db_structures:
        logger.critical(f'Unexpected structures in {db_name} database: {extra_db_structures}')
        errors.append(f'There are unexpected structures in your {db_name} database.')

    # Check tables and indexes
    for obj_type, minimized_data in [('table', minimized_schema), ('index', minimized_indexes)]:
        db_data = db_objects[obj_type]
        missing = minimized_data.keys() - db_data.keys()
        if missing:
            msg = f'{obj_type.capitalize()}s {missing} are missing from your {db_name} database.'
            if obj_type == 'table':
                errors.append(msg)
            else:  # indexes
                warnings.append(msg + ' Consider recreating them for better performance.')
                logger.warning(msg)

        extra = db_data.keys() - minimized_data.keys()
        if extra:
            msg = f'Your {db_name} database has the following unexpected {obj_type}s: {extra}.'
            if obj_type == 'table':
                info_msgs.append(msg + ' Feel free to delete them.')
            else:  # indexes
                info_msgs.append(msg + ' These are not harmful but are not required.')
            logger.info(msg)
            for extra_obj in extra:
                db_data.pop(extra_obj)

        # Check differing structures
        differing: dict[str, tuple[tuple[str, str], str]] = {}
        for obj_name, obj_data in db_data.items():
            if obj_name in minimized_data:
                expected = minimized_data[obj_name]
                if obj_type == 'table':
                    # For tables, compare the properties part
                    if obj_data[0] != expected.lower():
                        differing[obj_name] = (obj_data, expected)
                else:  # For indexes, normalize both sides by removing "ifnotexists"
                    expected_normalized = expected.replace('createindexifnotexists', 'createindex').replace('createuniqueindexifnotexists', 'createuniqueindex')  # noqa: E501
                    if obj_data[0] != expected_normalized:
                        differing[obj_name] = (obj_data, expected)

        if differing:
            log_msg = f'Differing {obj_type}s in the {db_name} database are:'
            for obj_name, ((normalized_or_props, raw_script), expected) in differing.items():
                log_msg += f'\n- For {obj_type} {obj_name} expected {expected} but found {normalized_or_props}. {obj_type.capitalize()} raw script is: {raw_script}'  # noqa: E501

            if obj_type == 'table':
                logger.critical(log_msg)
                errors.append(f'Structure of some tables in your {db_name} database differ from the expected.')  # noqa: E501
            else:  # indexes
                logger.warning(log_msg)
                warnings.append(f'Structure of some indexes in your {db_name} database differ from the expected.')  # noqa: E501

    for msg in info_msgs:
        logger.info(msg)

    # Raise error if there are any critical issues
    if errors:
        error_msg = ' '.join(errors) + ' Check the logs for more details. ' + DEFAULT_SANITY_CHECK_MESSAGE  # noqa: E501
        raise DBSchemaError(error_msg)
