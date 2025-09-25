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


class InputError(Exception):
    pass


class AlreadyExists(Exception):
    pass


class NotFoundError(Exception):
    pass


class RemoteError(Exception):
    """Thrown when a remote API can't be reached or throws unexpected error"""

    def __init__(self, message: str = '', error_code: int = 0):
        """
        Set error code with default 0 to not make it optional and always have an integer value.
        message: Error message for the error
        error_code: The error code of the http response if relevant
        """
        self.error_code = error_code
        super().__init__(message)


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


class GreenletKilledError(Exception):
    """Raised when a greenlet is killed"""


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


class MissingAPIKey(Exception):
    """Raised when an API key is missing for a service"""
