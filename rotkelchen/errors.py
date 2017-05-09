#!/usr/bin/env python

class PoloniexError(Exception):
    def __init__(self, err):
        self.err = err

    def __str__(self):
        return self.err
