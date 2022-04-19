class DeserializationError(Exception):
    """Raised when deserializing data from the outside and something unexpected is found"""


class ConversionError(Exception):
    pass


class EncodingError(Exception):
    pass
