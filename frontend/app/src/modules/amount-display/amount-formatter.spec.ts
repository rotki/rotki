import { BigNumber, bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { AmountFormatter } from '@/modules/amount-display/amount-formatter';

describe('amount-formatter', () => {
  const converter = new AmountFormatter();

  it('should handle decimal precision correctly', () => {
    expect(converter.format(bigNumberify(127.32189477847), 2, ' ', ',')).toBe('127,32');
    expect(converter.format(bigNumberify(127.32789477847), 2, ' ', ',')).toBe('127,32');
    expect(converter.format(bigNumberify(127.32789477847), 2, ' ', ',', BigNumber.ROUND_UP)).toBe('127,33');
  });

  it('should handle decimal separator correctly', () => {
    expect(converter.format(bigNumberify(127.32), 2, ' ', ',')).toBe('127,32');
  });

  it('should display decimals even if integer', () => {
    expect(converter.format(bigNumberify(127), 2, ' ', ',')).toBe('127,00');
  });

  it('should handle one thousand separator correctly', () => {
    expect(converter.format(bigNumberify(1127.32), 2, ' ', ',')).toBe('1 127,32');
  });

  it('should multiple thousand separator correctly', () => {
    expect(converter.format(bigNumberify(1221127.32), 2, ' ', ',')).toBe('1 221 127,32');
  });
});
