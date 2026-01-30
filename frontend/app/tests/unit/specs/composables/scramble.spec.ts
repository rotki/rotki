import { consistOfNumbers, isValidEthAddress } from '@rotki/common';
import { beforeAll, describe, expect, it } from 'vitest';
import { useScramble } from '@/composables/scramble';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

describe('composables::scramble', () => {
  let store: ReturnType<typeof useFrontendSettingsStore>;

  beforeAll(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
    store = useFrontendSettingsStore();
  });

  describe('when scramble is disabled', () => {
    it('should not scramble address', () => {
      const { scrambleAddress } = useScramble();
      const hex = '0xabcdef';
      expect(scrambleAddress(hex)).toEqual(hex);
    });

    it('should not scramble identifier', () => {
      const { scrambleIdentifier } = useScramble();
      const numbers = '123456';
      expect(scrambleIdentifier(numbers)).toEqual(numbers);
    });

    it('should not scramble timestamp', () => {
      const { scrambleTimestamp } = useScramble();
      const timestamp = 1769751333;
      expect(scrambleTimestamp(timestamp)).toEqual(timestamp);
    });
  });

  describe('when scramble is enabled', () => {
    beforeAll(async () => {
      await store.updateSetting({ scrambleData: true, scrambleMultiplier: 7 });
    });

    it('should scramble hex address', () => {
      const { scrambleAddress } = useScramble();
      const address = '0x6A023CCd1ff6F2045C3309768eAd9E68F978f6e1';
      const result = scrambleAddress(address);

      expect(result).not.toEqual(address);
      expect(isValidEthAddress(result)).toBeTruthy();
    });

    it('should scramble identifier', () => {
      const { scrambleIdentifier } = useScramble();
      const identifier = '123456';
      const result = scrambleIdentifier(identifier);

      expect(result).not.toEqual(identifier);
      expect(consistOfNumbers(result)).toBeTruthy();
    });

    it('should scramble integer', () => {
      const { scrambleInteger } = useScramble();
      const result = scrambleInteger(42);
      expect(result).not.toEqual(42);
    });

    it('should scramble integer within bounds', () => {
      const { scrambleInteger } = useScramble();
      const min = 100;
      const max = 500;
      const result = scrambleInteger(42, min, max);

      expect(result).toBeGreaterThanOrEqual(min);
      expect(result).toBeLessThan(max);
    });

    describe('scrambleTimestamp', () => {
      it('should scramble timestamp in seconds', () => {
        const { scrambleTimestamp } = useScramble();
        const timestamp = 1769751333;
        const result = scrambleTimestamp(timestamp);

        expect(result).not.toEqual(timestamp);
      });

      it('should scramble timestamp in milliseconds', () => {
        const { scrambleTimestamp } = useScramble();
        const timestamp = 1769751333000;
        const result = scrambleTimestamp(timestamp, true);

        expect(result).not.toEqual(timestamp);
      });

      it('should preserve ordering: if A < B then scramble(A) < scramble(B)', () => {
        const { scrambleTimestamp } = useScramble();
        const nowSeconds = Math.round(Date.now() / 1000);

        // past dates
        const pastA = nowSeconds - 365 * 86400;
        const pastB = nowSeconds - 30 * 86400;

        expect(scrambleTimestamp(pastA)).toBeLessThan(scrambleTimestamp(pastB));

        // future dates
        const futureA = nowSeconds + 30 * 86400;
        const futureB = nowSeconds + 365 * 86400;

        expect(scrambleTimestamp(futureA)).toBeLessThan(scrambleTimestamp(futureB));

        // across past and future
        expect(scrambleTimestamp(pastA)).toBeLessThan(scrambleTimestamp(futureB));
      });

      it('should keep past dates in the past and future dates in the future', () => {
        const { scrambleTimestamp } = useScramble();
        const nowSeconds = Math.round(Date.now() / 1000);

        const pastTimestamps = [
          nowSeconds - 10 * 86400,
          nowSeconds - 365 * 86400,
          nowSeconds - 10 * 365 * 86400,
        ];

        const futureTimestamps = [
          nowSeconds + 10 * 86400,
          nowSeconds + 365 * 86400,
          nowSeconds + 10 * 365 * 86400,
        ];

        for (const ts of pastTimestamps) {
          expect(scrambleTimestamp(ts)).toBeLessThan(nowSeconds);
        }

        for (const ts of futureTimestamps) {
          expect(scrambleTimestamp(ts)).toBeGreaterThan(nowSeconds);
        }
      });

      it('should not produce dates that are unreasonably far from the original', () => {
        const { scrambleTimestamp } = useScramble();
        const nowSeconds = Math.round(Date.now() / 1000);

        const tenYearsAgo = nowSeconds - 10 * 365 * 86400;
        const tenYearsAhead = nowSeconds + 10 * 365 * 86400;

        const maxOffsetSeconds = 10 * 13 * 86400
          + 10 * 7 * 3600
          + 10 * 23 * 60
          + 10 * 37;

        const scrambledPast = scrambleTimestamp(tenYearsAgo);
        const scrambledFuture = scrambleTimestamp(tenYearsAhead);

        // The offset from original should not exceed the max possible offset (multiplier=10)
        expect(Math.abs(scrambledPast - tenYearsAgo)).toBeLessThanOrEqual(maxOffsetSeconds);
        expect(Math.abs(scrambledFuture - tenYearsAhead)).toBeLessThanOrEqual(maxOffsetSeconds);
      });
    });
  });
});
