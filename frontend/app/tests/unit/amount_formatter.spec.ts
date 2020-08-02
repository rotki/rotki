import { AmountFormatter } from '@/data/amount_formatter';
import { bigNumberify } from '@/utils/bignumbers';

describe('AmountFormatter', () => {
  const converter = new AmountFormatter();

  it('should handle decimal precision correctly', () => {
    expect(
      converter.format(bigNumberify(127.32189477847), '%T %U,%D %C', 2, '$')
    ).toEqual('127,32 $');
    expect(
      converter.format(bigNumberify(127.32789477847), '%T %U,%D %C', 2, '$')
    ).toEqual('127,33 $');
  });

  it('should handle decimal separator correctly', () => {
    expect(
      converter.format(bigNumberify(127.32), '%T %U,%D %C', 2, '$')
    ).toEqual('127,32 $');
  });

  it('should not display decimals if integer', () => {
    expect(converter.format(bigNumberify(127), '%T %U,%D %C', 2, '$')).toEqual(
      '127 $'
    );
  });

  it('should handle one thousands separator correctly', () => {
    expect(
      converter.format(bigNumberify(1127.32), '%T %U,%D %C', 2, '$')
    ).toEqual('1 127,32 $');
  });

  it('should multiple thousands separator correctly', () => {
    expect(
      converter.format(bigNumberify(1221127.32), '%T %U,%D %C', 2, '$')
    ).toEqual('1 221 127,32 $');
  });

  it('should allow currency to be omitted', () => {
    expect(converter.format(bigNumberify(127.32), '%T %U,%D', 2, '$')).toEqual(
      '127,32'
    );
  });

  it('should handle currency before or after', () => {
    expect(
      converter.format(bigNumberify(127.32), '%T %U,%D %C', 2, '$')
    ).toEqual('127,32 $');
    expect(
      converter.format(bigNumberify(127.32), '%C%T %U,%D', 2, '$')
    ).toEqual('$127,32');
  });
});
