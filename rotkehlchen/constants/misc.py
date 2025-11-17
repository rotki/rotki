from typing import Final

from rotkehlchen.fval import FVal

ZERO: Final = FVal(0)
ONE: Final = FVal(1)
EXP18_INT: Final = int(1e18)
# Tolerance used when querying claims in the database since we need to cast
# to float and we can loose precision in SQL. With lower tolerance the ens
# airdrop fails to get detected.
AIRDROPS_TOLERANCE: Final = FVal(10e-13)

# Could also try to extend HTTPStatus but looks complicated
# https://stackoverflow.com/questions/45028991/best-way-to-extend-httpstatus-with-custom-value
HTTP_STATUS_INTERNAL_DB_ERROR: Final = 542

NFT_DIRECTIVE: Final = '_nft_'

# API URLS
KRAKEN_BASE_URL: Final = 'https://api.kraken.com'
KRAKEN_API_VERSION: Final = '0'

DEFAULT_MAX_LOG_SIZE_IN_MB: Final = 300
DEFAULT_MAX_LOG_BACKUP_FILES: Final = 3
DEFAULT_SQL_VM_INSTRUCTIONS_CB: Final = 5000
DEFAULT_LOGLEVEL: Final = 'DEBUG'
VALID_LOGLEVELS: Final = ('TRACE', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')

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
AIRDROPSDIR_NAME: Final = 'airdrops'
AIRDROPSPOAPDIR_NAME: Final = 'airdrops_poap'

DEFAULT_BALANCE_LABEL: Final = 'address'
