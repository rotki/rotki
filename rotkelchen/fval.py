from decimal import Decimal


def evaluate_input(other):
    if isinstance(other, FVal):
        other = other.num
    elif not isinstance(other, int):
        raise NotImplementedError("Expected either FVal or int.")

    return other


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
        if isinstance(data, float):
            self.num = Decimal(str(data))
        elif isinstance(data, (Decimal, int, str)):
            self.num = Decimal(data)
        elif isinstance(data, FVal):
            self.num = data.num
        else:
            raise ValueError(
                'Expected string, int, float, or Decimal to initialize an FVal.'
                'Found {}.'.format(type(data))
            )

    def __str__(self):
        return str(self.num)

    def __cmp__(self, other):
        other = evaluate_input(other)
        return self.num.compare_signal(other)

    def __add__(self, other):
        other = evaluate_input(other)
        return FVal(self.num.__add__(other))

    def __sub__(self, other):
        other = evaluate_input(other)
        return FVal(self.num.__sub__(other))

    def __mul__(self, other):
        other = evaluate_input(other)
        return FVal(self.num.__mul__(other))

    def __div__(self, other):
        other = evaluate_input(other)
        return FVal(self.num.__div__(other))

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

    def __rdiv__(self, other):
        other = evaluate_input(other)
        return FVal(self.num.__rdiv__(other))

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

    def to_exact_int(self):
        """Tries to convert to int only if it is a whole decimal number;
        i.e.: if it has got nothing after the decimal point"""
        if self.num.to_integral_exact() != self.num:
            raise ValueError('Tried to ask for exact int from {}'.format(self.num))
        return int(self.num)
