from decimal import Decimal, InvalidOperation


def evaluate_input(other):
    if isinstance(other, FVal):
        other = other.num
    elif not isinstance(other, int):
        raise NotImplementedError("Expected either FVal or int.")

    return other


def fval_from_percentage(perc):
    """Create an fval from a percentage string in the style of "0.23478%

    We will essentially get the corresponding float and divide by 100"""
    perc = perc.rstrip('%')
    perc = FVal(perc) / 100
    return perc


class FVal(object):
    """A value to represent numbers for financial applications. At the moment
    we use the python Decimal library but the abstraction will help us change the
    underlying implementation if needed.

    At the moment we do not allow any operations against floating points. Even though
    floating points could be converted to Decimals before each operation we will
    use this restriction to make sure floating point numbers are rooted from the codebase first.
    """

    __slots__ = ('num',)

    def __init__(self, data):
        try:
            if isinstance(data, float):
                self.num = Decimal(str(data))
            elif isinstance(data, bytes):
                # assume it's an ascii string and try to decode the bytes to one
                self.num = Decimal(data.decode())
            elif isinstance(data, (Decimal, int, str)):
                self.num = Decimal(data)
            elif isinstance(data, FVal):
                self.num = data.num
            else:
                self.num = None

        except InvalidOperation as e:
            self.num = None

            if not self.num:
                raise ValueError(
                    'Expected string, int, float, or Decimal to initialize an FVal.'
                    'Found {}.'.format(type(data))
                )

    def __str__(self):
        return str(self.num)

    def __repr__(self):
        return 'FVal({})'.format(str(self.num))

    def __gt__(self, other):
        other = evaluate_input(other)
        return self.num.compare_signal(other) == Decimal('1')

    def __lt__(self, other):
        other = evaluate_input(other)
        return self.num.compare_signal(other) == Decimal('-1')

    def __le__(self, other):
        other = evaluate_input(other)
        return self.num.compare_signal(other) in (Decimal('-1'), Decimal('0'))

    def __ge__(self, other):
        other = evaluate_input(other)
        return self.num.compare_signal(other) in (Decimal('1'), Decimal('0'))

    def __eq__(self, other):
        other = evaluate_input(other)
        return self.num.compare_signal(other) == Decimal('0')

    def __add__(self, other):
        other = evaluate_input(other)
        return FVal(self.num.__add__(other))

    def __sub__(self, other):
        other = evaluate_input(other)
        return FVal(self.num.__sub__(other))

    def __mul__(self, other):
        other = evaluate_input(other)
        return FVal(self.num.__mul__(other))

    def __truediv__(self, other):
        other = evaluate_input(other)
        return FVal(self.num.__truediv__(other))

    def __floordiv__(self, other):
        other = evaluate_input(other)
        return FVal(self.num.__floordiv__(other))

    def __pow__(self, other):
        other = evaluate_input(other)
        return FVal(self.num.__pow__(other))

    def __radd__(self, other):
        other = evaluate_input(other)
        return FVal(self.num.__radd__(other))

    def __rsub__(self, other):
        other = evaluate_input(other)
        return FVal(self.num.__rsub__(other))

    def __rmul__(self, other):
        other = evaluate_input(other)
        return FVal(self.num.__rmul__(other))

    def __rtruediv__(self, other):
        other = evaluate_input(other)
        return FVal(self.num.__rtruediv__(other))

    def __rfloordiv__(self, other):
        other = evaluate_input(other)
        return FVal(self.num.__rfloordiv__(other))

    def __float__(self):
        return float(self.num)

    # --- Unary operands

    def __neg__(self):
        return FVal(self.num.__neg__())

    def __abs__(self):
        return FVal(self.num.copy_abs())

    # --- Other oparations

    def fma(self, other, third):
        """
        Fused multiply-add. Return self*other+third with no rounding of the
        intermediate product self*other
        """
        other = evaluate_input(other)
        third = evaluate_input(third)
        return FVal(self.num.fma(other, third))

    def to_percentage(self):
        return '{:.5%}'.format(self.num)

    def to_int(self, exact):
        """Tries to convert to int, If `exact` is true then it will convert only if
        it is a whole decimal number; i.e.: if it has got nothing after the decimal point"""
        if exact and self.num.to_integral_exact() != self.num:
            raise ValueError('Tried to ask for exact int from {}'.format(self.num))
        return int(self.num)

    def is_close(self, other, max_diff="1e-9"):
        max_diff = FVal(max_diff)

        if not isinstance(other, FVal):
            other = FVal(other)

        diff_num = abs(self.num - other.num)
        return diff_num <= max_diff.num
