import dayjs from 'dayjs';
import { describe, expect, it } from 'vitest';
import { useWrappedFormatters } from '@/modules/statistics/wrapped/use-wrapped-formatters';

describe('useWrappedFormatters', () => {
  const { calculateFontSize, formatDate, hasSectionData } = useWrappedFormatters();

  describe('hasSectionData', () => {
    it('should return false for undefined data', () => {
      expect(hasSectionData(undefined)).toBe(false);
    });

    it('should return false for an empty array', () => {
      expect(hasSectionData([])).toBe(false);
    });

    it('should return true for a non-empty array', () => {
      expect(hasSectionData([1])).toBe(true);
    });

    it('should return false for an empty object', () => {
      expect(hasSectionData({})).toBe(false);
    });

    it('should return true for a non-empty object', () => {
      expect(hasSectionData({ a: 1 })).toBe(true);
    });
  });

  describe('formatDate', () => {
    it('should format a unix timestamp as a full date', () => {
      const timestamp = dayjs('2023-06-15T12:00:00Z').unix();
      expect(formatDate(timestamp)).toBe(dayjs(timestamp * 1000).format('dddd, MMMM D, YYYY'));
    });
  });

  describe('calculateFontSize', () => {
    it('should shrink the font size as the symbol grows', () => {
      expect(calculateFontSize('A')).toBe('1.4em');
      expect(calculateFontSize('AB')).toBe('1em');
      expect(calculateFontSize('ABC')).toBe('0.5999999999999999em');
    });
  });
});
