from http import HTTPStatus

from rotkehlchen.errors.cause import FailureCause


class SystemPermissionError(Exception):
    pass


class DBUpgradeError(Exception):
    pass


class TagConstraintError(Exception):
    pass


class EthSyncError(Exception):
    pass


class UnableToDecryptRemoteData(Exception):
    pass


class RemoteBackupError(Exception):
    """The remote premium backup can't be restored for a reason other than a wrong password.

    The message is shown to the user as is, so it has to say what to do about it.
    """


class BackupTooLargeError(Exception):
    """The compressed premium backup is bigger than what the user's tier allows to store.

    Raised both by the local check before uploading and when the server refuses the upload
    for its size. Uploading again can't succeed until the DB or the plan changes.

    The message is shown to the user as is.
    """


class UnsupportedRemoteBackup(RemoteBackupError):
    """The remote backup header names a version or KDF this rotki can't read.

    Either a newer rotki made it or the header is damaged, and before deriving a key the two
    can't be told apart.
    """

    def __init__(self) -> None:
        super().__init__(
            'The backup on the rotki server was made by a newer rotki version or is damaged. '
            'If it is newer, update rotki on this device to restore it.',
        )


class RemoteBackupDowngrade(RemoteBackupError):
    """The remote backup is in the legacy format but this device already synced the new one"""

    def __init__(self) -> None:
        super().__init__(
            'The backup on the rotki server is in an older format than the one this device '
            'already synced, so it was probably uploaded by an older rotki version on another '
            'device. Update rotki on that device and upload from it again.',
        )


class RemoteBackupMismatch(RemoteBackupError):
    """The authenticated timestamp of the remote backup differs from the server metadata"""

    def __init__(self) -> None:
        super().__init__(
            'The backup received from the rotki server does not match the backup details the '
            'server reported. It may have been replaced while downloading. Try syncing again.',
        )


class InputError(Exception):
    pass


class AlreadyExists(Exception):
    pass


class NotFoundError(Exception):
    pass


class RemoteError(Exception):
    """Thrown when a remote API can't be reached or throws unexpected error.

    `cause` says which of the two it was, since only the raise site knows: an unreachable
    remote is worth retrying, a remote that rejected the key or the request is not.
    `error_code` is the HTTP status of the response, or 0 when there was none.
    """

    def __init__(
            self,
            message: str = '',
            *,
            cause: FailureCause | None = None,
            error_code: int = 0,
    ) -> None:
        self.cause = cause
        self.error_code = error_code
        super().__init__(message)


class RecoverableRemoteError(RemoteError):
    """Raised when a remote query failed for a reason that is expected to go away by itself
    shortly, such as rate limiting, a timeout, a connection problem or a 408/5xx response."""


def cause_for_status(status_code: int) -> FailureCause:
    """The cause of a failed HTTP response, read from its status.

    A 429 asks us to slow down, and server errors and request timeouts (408) are the remote
    failing to answer. A 401 or 403 rejects our credentials; any other status rejects the
    request itself.
    """
    if status_code == HTTPStatus.TOO_MANY_REQUESTS:
        return FailureCause.RATE_LIMITED
    if (
            status_code == HTTPStatus.REQUEST_TIMEOUT or
            status_code >= HTTPStatus.INTERNAL_SERVER_ERROR
    ):
        return FailureCause.NETWORK
    if status_code in {HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN}:
        return FailureCause.AUTH
    return FailureCause.REMOTE_REJECTED


def remote_error_for_status(status_code: int, message: str) -> RemoteError:
    """Build the error for a failed HTTP response. Server errors and request timeouts
    (408) are expected to clear up by themselves, so they are recoverable."""
    error_class = RecoverableRemoteError if (
        status_code == HTTPStatus.REQUEST_TIMEOUT or
        status_code >= HTTPStatus.INTERNAL_SERVER_ERROR
    ) else RemoteError
    return error_class(message, cause=cause_for_status(status_code), error_code=status_code)


class APIKeyNotAvailable(RemoteError):
    """Raised when an API key required for a query is not available."""

    def __init__(self, message: str) -> None:
        super().__init__(message, cause=FailureCause.AUTH)


class NoAvailableIndexers(RemoteError):
    """Raised when there are no available indexers for a given chain."""

    def __init__(self, message: str) -> None:
        super().__init__(message, cause=FailureCause.UNSUPPORTED)


class IndexerRangeNotCovered(RemoteError):
    """Raised when an indexer cannot serve the requested chain history range."""

    def __init__(self, message: str) -> None:
        super().__init__(message, cause=FailureCause.UNSUPPORTED)


class BlockscoutIncompleteResponse(RemoteError):
    """Raised when Blockscout reports that the requested data is not fully indexed yet."""

    def __init__(self, message: str) -> None:
        super().__init__(message, cause=FailureCause.NETWORK)


class IncompleteTransactionsQuery(RemoteError):
    """Raised when the transactions of some addresses could not be fully queried.

    Its message is shown to the user, so it must not carry the underlying indexer error,
    which can include request URLs with API keys and raw response bodies. The failed
    addresses are retried by the next sync, so it is a transient failure.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message, cause=FailureCause.NETWORK)


class RequestTooLargeError(RemoteError):
    """Raised when a request fails due to size limits (gas limit, URL too long)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, cause=FailureCause.REMOTE_REJECTED)


class XPUBError(Exception):
    """Error XPUB Parsing and address derivation"""


class ModuleInitializationFailure(Exception):
    """Raises when a module failed to initialize"""


class ModuleInactive(Exception):
    """Raises when call happens for a module that is not initialized"""


class ModuleLoadingError(Exception):
    """Error at loading a specific Module's class"""


class NotERC20Conformant(Exception):
    """An address is not conforming to the ERC20 standard"""


class NotERC721Conformant(Exception):
    """An address is not conforming to the ERC721 standard"""


class TokenQueryFailed(NotERC20Conformant, NotERC721Conformant):
    """The details of a token could not be queried because the nodes could not be reached.

    It is a subclass of the non conformant errors so that callers that only care about not
    getting the token keep working, while the ones that need to retry can tell it apart.
    """


class NotSPLConformant(Exception):
    """An address is not conforming to the solana SPL token standard"""


class BlockchainQueryError(Exception):
    """Raises when there are problems querying a blockchain node.

    For example a VM Execution error in ethereum contract calls
    """


class EventNotInABI(Exception):
    """Raised when trying to query an event and that is not found in the ABI"""


class DBSchemaError(Exception):
    """May be raised during database sanity check"""


class DataIntegrityError(Exception):
    """Raised when an operation would corrupt or destroy data that is already stored in the DB."""


class AccountingError(Exception):
    """Fatal error while processing accounting events during a PnL report"""

    def __init__(self, message: str, report_id: int | None = None):
        """
        report_id is not mandatory since where it is used the id is not known until later.
        It is later set.
        """
        super().__init__(message)
        self.report_id = report_id


class AddressNotSupported(Exception):
    """Used when we detect an address with a unknown format for the addressbook"""


class ChainNotSupported(RemoteError):
    """Raised when a chain is not supported by a service/api/etc"""

    def __init__(self, message: str) -> None:
        super().__init__(message, cause=FailureCause.UNSUPPORTED)


class MissingAPIKey(Exception):
    """Raised when an API key is missing for a service"""
