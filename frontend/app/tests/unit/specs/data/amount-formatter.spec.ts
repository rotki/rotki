import { AmountFormatter } from '@/data/amount-formatter';
import { BigNumber } from '@rotki/common';
import { describe, expect, it } from 'vitest';

describe('amountFormatter', () => {
  const converter = new AmountFormatter();

  it('should handle decimal precision correctly', () => {
    expect(converter.format(bigNumberify(127.32189477847), 2, ' ', ',')).toEqual('127,32');
    expect(converter.format(bigNumberify(127.32789477847), 2, ' ', ',')).toEqual('127,32');
    expect(converter.format(bigNumberify(127.32789477847), 2, ' ', ',', BigNumber.ROUND_UP)).toEqual('127,33');
  });

  it('should handle decimal separator correctly', () => {
    expect(converter.format(bigNumberify(127.32), 2, ' ', ',')).toEqual('127,32');
  });

  it('should display decimals even if integer', () => {
    expect(converter.format(bigNumberify(127), 2, ' ', ',')).toEqual('127,00');
  });

  it('should handle one thousand separator correctly', () => {
    expect(converter.format(bigNumberify(1127.32), 2, ' ', ',')).toEqual('1 127,32');
  });

  it('should multiple thousand separator correctly', () => {
    expect(converter.format(bigNumberify(1221127.32), 2, ' ', ',')).toEqual('1 221 127,32');
  });
});
