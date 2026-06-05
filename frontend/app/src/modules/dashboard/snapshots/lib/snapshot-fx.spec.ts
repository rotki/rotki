import { bigNumberify, One } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { convertFiatToUsd, convertUsdToFiat } from '@/modules/dashboard/snapshots/lib/snapshot-fx';

describe('modules/dashboard/snapshots/lib/snapshot-fx', () => {
  describe('convertUsdToFiat', () => {
    it('should multiply the USD value by the rate', () => {
      expect(convertUsdToFiat(bigNumberify(100), bigNumberify(0.85)).toNumber()).toBe(85);
    });

    it('should be the identity when the rate is one', () => {
      expect(convertUsdToFiat(bigNumberify(123.45), One).toNumber()).toBe(123.45);
    });

    it('should return zero for a zero value', () => {
      expect(convertUsdToFiat(bigNumberify(0), bigNumberify(0.85)).toNumber()).toBe(0);
    });
  });

  describe('convertFiatToUsd', () => {
    it('should divide the fiat value by the rate', () => {
      expect(convertFiatToUsd(bigNumberify(85), bigNumberify(0.85)).toNumber()).toBe(100);
    });

    it('should be the identity when the rate is one', () => {
      expect(convertFiatToUsd(bigNumberify(123.45), One).toNumber()).toBe(123.45);
    });
  });

  describe('round-trip', () => {
    it('should recover the original USD value', () => {
      const rate = bigNumberify(0.9234);
      const usd = bigNumberify(1234.56);
      const back = convertFiatToUsd(convertUsdToFiat(usd, rate), rate);
      expect(back.toNumber()).toBeCloseTo(1234.56, 8);
    });
  });
});
