from typing import Final

from rotkehlchen.fval import FVal

CURRENCYCONVERTER_API_KEY = 'feaa5a7ddc2d76789e58'

ZERO = FVal(0)
ONE = FVal(1)
EXP18 = FVal(1e18)

# Could also try to extend HTTPStatus but looks complicated
# https://stackoverflow.com/questions/45028991/best-way-to-extend-httpstatus-with-custom-value
HTTP_STATUS_INTERNAL_DB_ERROR = 542

NFT_DIRECTIVE = '_nft_'

# API URLS
KRAKEN_BASE_URL = 'https://api.kraken.com'
KRAKEN_API_VERSION = '0'

DEFAULT_MAX_LOG_SIZE_IN_MB = 300
DEFAULT_MAX_LOG_BACKUP_FILES = 3
DEFAULT_SQL_VM_INSTRUCTIONS_CB = 5000

GLOBALDIR_NAME: Final = 'global'
GLOBALDB_NAME: Final = 'global.db'
USERSDIR_NAME: Final = 'users'
USERDB_NAME: Final = 'rotkehlchen.db'
IMAGESDIR_NAME: Final = 'images'
ASSETIMAGESDIR_NAME: Final = 'assets'
AVATARIMAGESDIR_NAME: Final = 'avatars'
ALLASSETIMAGESDIR_NAME: Final = 'all'
CUSTOMASSETIMAGESDIR_NAME: Final = 'custom'
MISCDIR_NAME: Final = 'misc'
APPDIR_NAME: Final = 'app'
