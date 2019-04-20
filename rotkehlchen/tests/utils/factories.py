import base64
import random
import string

from rotkehlchen.fval import FVal
from rotkehlchen.utils.misc import ts_now


def make_random_bytes(size):
    return bytes(bytearray(random.getrandbits(8) for _ in range(size)))


def make_random_b64bytes(size):
    return base64.b64encode(make_random_bytes(size))


def make_random_uppercasenumeric_string(size):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=size))


def make_random_positive_fval(max_num=1000000):
    return FVal(random.uniform(0, max_num))


def make_random_timestamp(start=1451606400, end=None):
    if end is None:
        end = ts_now()
    return random.randint(start, end)
