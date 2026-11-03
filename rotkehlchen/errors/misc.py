from http import HTTPStatus
from typing import TYPE_CHECKING

from rotkehlchen.errors.cause import FailureCause

if TYPE_CHECKING:
    from collections.abc import Collection


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
            cause: FailureCause,
            error_code: int = 0,
    ) -> None:
        self.cause = cause
        self.error_code = error_code
        super().__init__(message)


class RequestFieldRemoteError(RemoteError):
    """A remote needed to validate a request field failed. A marshmallow ValidationError
    keeps only its messages, so the cause of the failure would not survive one."""

    def __init__(self, field_name: str, message: str, *, cause: FailureCause) -> None:
        super().__init__(message, cause=cause)
        self.field_name = field_name


class RecoverableRemoteError(RemoteError):
    """Raised when a remote query failed for a reason that is expected to go away by itself
    shortly, such as rate limiting, a timeout, a connection problem or a 408/5xx response."""


def cause_for_status(status_code: int) -> FailureCause:
    """The cause of a failed HTTP response, read from its status.

    A 429 asks us to slow down, and server errors and request timeouts (408) are the remote
    failing to answer. A 401 rejects our credentials. Any other status rejects the request
    itself, including a 403, which services also send for rate and plan limits, and a 2xx
    whose body reports a failure. A site that knows its 403 means a rejected key says so.
    """
    if status_code == HTTPStatus.TOO_MANY_REQUESTS:
        return FailureCause.RATE_LIMITED
    if (
            status_code == HTTPStatus.REQUEST_TIMEOUT or
            status_code >= HTTPStatus.INTERNAL_SERVER_ERROR
    ):
        return FailureCause.NETWORK
    if status_code == HTTPStatus.UNAUTHORIZED:
        return FailureCause.AUTH
    return FailureCause.REMOTE_REJECTED


def cause_for_undecodable_body(status_code: int) -> FailureCause:
    """The cause of a response whose body could not be decoded. A success that can't be read
    is bad data. On any other status the body is likely an error page, so the status decides.
    """
    if HTTPStatus.OK <= status_code < HTTPStatus.MULTIPLE_CHOICES:
        return FailureCause.BAD_DATA
    return cause_for_status(status_code)


def cause_for_credential_check(status_code: int) -> FailureCause:
    """The cause of a failed response to a request that only checks credentials. Any refusal
    means they were rejected, but a 429 or a server error says nothing about them."""
    cause = cause_for_status(status_code)
    return FailureCause.AUTH if cause == FailureCause.REMOTE_REJECTED else cause


def remote_error_for_status(status_code: int, message: str) -> RemoteError:
    """Build the error for a failed HTTP response. Server errors and request timeouts
    (408) are expected to clear up by themselves, so they are recoverable."""
    cause = cause_for_status(status_code)
    error_class = RecoverableRemoteError if cause == FailureCause.NETWORK else RemoteError
    return error_class(message, cause=cause, error_code=status_code)


def cause_of(error: Exception, default: FailureCause) -> FailureCause:
    """The cause a caught error carries, or `default` for one that is not a RemoteError."""
    return error.cause if isinstance(error, RemoteError) else default


def combined_cause(causes: Collection[FailureCause]) -> FailureCause:
    """The cause of one failure that stands for several: theirs when they all agree, and
    otherwise REMOTE_REJECTED, since a retry would not help every one of them."""
    return next(iter(causes)) if len(set(causes)) == 1 else FailureCause.REMOTE_REJECTED


def alternatives_cause(causes: Collection[FailureCause]) -> FailureCause:
    """The cause of a query that failed on every source able to answer it. Any one source
    answering is enough, so a retry can help as soon as one of them may heal by itself, and
    a source that never serves this query says nothing about what the others need."""
    for transient_cause in (FailureCause.RATE_LIMITED, FailureCause.NETWORK):
        if transient_cause in causes:
            return transient_cause
    return combined_cause((set(causes) - {FailureCause.UNSUPPORTED}) or causes)


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


class ContractReverted(RemoteError):
    """Raised when a contract call reverted on-chain.

    The revert is deterministic, so querying other nodes can't change the outcome.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message, cause=FailureCause.REMOTE_REJECTED)


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
