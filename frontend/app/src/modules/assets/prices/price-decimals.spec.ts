import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { priceDecimals } from '@/modules/assets/prices/price-decimals';

describe('priceDecimals', () => {
  it('should keep the minimum for a price of 1 or more', () => {
    expect(priceDecimals(bigNumberify('3000.1234'))).toBe(2);
    expect(priceDecimals(bigNumberify('1'))).toBe(2);
  });

  it('should show four digits past the leading zeros of a price below 1', () => {
    expect(priceDecimals(bigNumberify('0.0327114'))).toBe(5);
    expect(priceDecimals(bigNumberify('0.000412345'))).toBe(7);
  });

  it('should not pad a short price out with zeros', () => {
    expect(priceDecimals(bigNumberify('0.5'))).toBe(2);
    expect(priceDecimals(bigNumberify('0.032'))).toBe(3);
  });

  it('should stop at the maximum for a tiny price', () => {
    expect(priceDecimals(bigNumberify('0.000000000000012345'))).toBe(12);
  });

  it('should keep the minimum for zero and for a value that is not a number', () => {
    expect(priceDecimals(bigNumberify('0'))).toBe(2);
    expect(priceDecimals(bigNumberify('NaN'))).toBe(2);
  });
});
