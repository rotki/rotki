import random

from rotkehlchen.fval import FVal


def make_random_bytes(size):
    return bytes(bytearray(random.getrandbits(8) for _ in range(size)))


def make_random_bytes_for_requests(size):
    bits = []
    while size != 0:
        x = random.getrandbits(8)
        # Seems that requests is a bit picky with what kind of values it
        # accepts in a header: https://github.com/requests/requests/issues/3488
        if x in (10, 93, 193):
            continue
        bits.append(x)
        size -= 1
    return bytes(bytearray(bits))


def make_random_positive_fval():
    return FVal(random.uniform(0, 1000000))
