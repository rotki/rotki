#!/usr/bin/env python


class PoloniexError(Exception):
    def __init__(self, err):
        self.err = err

    def __str__(self):
        return self.err


class KrakenAPIRateLimitExceeded(Exception):
    def __init__(self, method):
        self.err = "Exceeded kraken API limit while querying {}".format(method)

    def __str__(self):
        return self.err
