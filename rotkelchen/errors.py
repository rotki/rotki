#!/usr/bin/env python


class PoloniexError(Exception):
    def __init__(self, err):
        self.err = err

    def __str__(self):
        return self.err


class RecoverableRequestError(Exception):
    def __init__(self, exchange, err):
        self.exchange = exchange
        self.err = err

    def __str__(self):
        return 'While querying {} got error: "{}"'.format(self.exchange, self.err)


class CorruptData(Exception):
    def __init__(self, err):
        self.err = err

    def __str__(self):
        return self.err


class InputError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class PermissionError(Exception):
    pass
