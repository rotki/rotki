import base64
import random

from rotkehlchen.fval import FVal


def make_random_bytes(size):
    return bytes(bytearray(random.getrandbits(8) for _ in range(size)))


def make_random_b64bytes(size):
    return base64.b64encode(make_random_bytes(size))


def make_random_positive_fval():
    return FVal(random.uniform(0, 1000000))
