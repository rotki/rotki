import { BigNumber, bigNumberify } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { beforeEach, describe, expect, it } from 'vitest';
import { useAmountFormatter } from '@/modules/amount-display/composables/use-amount-formatter';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

describe('modules/amount-display/composables/use-amount-formatter', () => {
  beforeEach(() => {
    setActivePinia(createPinia());

    const frontendStore = useFrontendSettingsStore();

    updateGeneralSettings({ uiFloatingPrecision: 2 });

    frontendStore.update({
      abbreviateNumber: false,
      amountRoundingMode: BigNumber.ROUND_DOWN,
      decimalSeparator: '.',
      minimumDigitToBeAbbreviated: 4,
      subscriptDecimals: false,
      thousandSeparator: ',',
      valueRoundingMode: BigNumber.ROUND_DOWN,
    });
  });

  describe('renderedValue', () => {
    it('should format a simple number correctly', () => {
      const value = ref(bigNumberify(1234.5678));
      const formatter = useAmountFormatter({ value });

      expect(get(formatter.renderedValue)).toBe('1,234.56');
    });

    it('should return "-" for NaN values', () => {
      const value = ref(bigNumberify(NaN));
      const formatter = useAmountFormatter({ value });

      expect(get(formatter.renderedValue)).toBe('-');
      expect(get(formatter.isNaN)).toBe(true);
    });

    it('should format integer values when integer option is true', () => {
      const value = ref(bigNumberify(1234.5678));
      const formatter = useAmountFormatter({ integer: true, value });

      expect(get(formatter.renderedValue)).toBe('1,234');
    });

    it('should handle exponential notation for large numbers', () => {
      const value = ref(bigNumberify('1e20'));
      const formatter = useAmountFormatter({ value });

      expect(get(formatter.showExponential)).toBe(true);
      expect(get(formatter.renderedValue)).toContain('e');
    });
  });

  describe('tooltip', () => {
    it('should return null when no truncation occurs', () => {
      const value = ref(bigNumberify(1.12));
      const formatter = useAmountFormatter({ value });

      expect(get(formatter.tooltip)).toBeNull();
    });

    it('should return full value when decimals are truncated', () => {
      const value = ref(bigNumberify(1.123456));
      const formatter = useAmountFormatter({ value });

      expect(get(formatter.tooltip)).toBe('1.123456');
    });
  });

  describe('comparisonSymbol', () => {
    it('should return empty string when no hidden decimals', () => {
      const value = ref(bigNumberify(1.12));
      const formatter = useAmountFormatter({ value });

      expect(get(formatter.comparisonSymbol)).toBe('');
    });

    it('should return ">" for small numbers with hidden decimals when rounding down', () => {
      const value = ref(bigNumberify(0.123456));
      const formatter = useAmountFormatter({ value });

      expect(get(formatter.comparisonSymbol)).toBe('>');
    });
  });

  describe('abbreviation', () => {
    it('should abbreviate large numbers when enabled', () => {
      setActivePinia(createPinia());
      const frontendStore = useFrontendSettingsStore();
      frontendStore.update({
        abbreviateNumber: true,
        minimumDigitToBeAbbreviated: 4,
      });

      const value = ref(bigNumberify(1000000));
      const formatter = useAmountFormatter({ value });

      expect(get(formatter.abbreviate)).toBe(true);
      expect(get(formatter.renderedValue)).toContain('M');
    });

    it('should not abbreviate when disabled', () => {
      const value = ref(bigNumberify(1000000));
      const formatter = useAmountFormatter({ value });

      expect(get(formatter.abbreviate)).toBe(false);
      expect(get(formatter.renderedValue)).toBe('1,000,000.00');
    });
  });

  describe('subscript decimals', () => {
    it('should not use subscript when disabled', () => {
      const value = ref(bigNumberify(0.00012345));
      const formatter = useAmountFormatter({ value });

      expect(get(formatter.shouldUseSubscript)).toBe(false);
      expect(get(formatter.numberParts).full).toBeDefined();
    });

    it('should use subscript for small decimals when enabled', () => {
      const frontendStore = useFrontendSettingsStore();
      frontendStore.update({ subscriptDecimals: true });

      const value = ref(bigNumberify(0.00012345));
      const formatter = useAmountFormatter({ value });

      expect(get(formatter.shouldUseSubscript)).toBe(true);
      expect(get(formatter.numberParts)).toEqual({
        leadingZeros: '3',
        separator: '.',
        significantDigits: '12',
        whole: '0',
      });
    });

    it('should not use subscript for values >= 1', () => {
      const frontendStore = useFrontendSettingsStore();
      frontendStore.update({ subscriptDecimals: true });

      const value = ref(bigNumberify(1.00012345));
      const formatter = useAmountFormatter({ value });

      expect(get(formatter.shouldUseSubscript)).toBe(false);
    });

    it('should not use subscript for values with less than 2 leading zeros', () => {
      const frontendStore = useFrontendSettingsStore();
      frontendStore.update({ subscriptDecimals: true });

      const value = ref(bigNumberify(0.12345));
      const formatter = useAmountFormatter({ value });

      expect(get(formatter.shouldUseSubscript)).toBe(false);
    });
  });

  describe('rounding modes', () => {
    it('should use amountRoundingMode when rounding is "amount"', () => {
      const frontendStore = useFrontendSettingsStore();
      frontendStore.update({
        amountRoundingMode: BigNumber.ROUND_UP,
        valueRoundingMode: BigNumber.ROUND_DOWN,
      });

      const value = ref(bigNumberify(1.999));
      const formatter = useAmountFormatter({ rounding: 'amount', value });

      expect(get(formatter.renderedValue)).toBe('2.00');
    });

    it('should use valueRoundingMode when rounding is "value" (default)', () => {
      const frontendStore = useFrontendSettingsStore();
      frontendStore.update({
        amountRoundingMode: BigNumber.ROUND_UP,
        valueRoundingMode: BigNumber.ROUND_DOWN,
      });

      const value = ref(bigNumberify(1.999));
      const formatter = useAmountFormatter({ rounding: 'value', value });

      expect(get(formatter.renderedValue)).toBe('1.99');
    });
  });

  describe('reactivity', () => {
    it('should update when value changes', () => {
      const value = ref(bigNumberify(100));
      const formatter = useAmountFormatter({ value });

      expect(get(formatter.renderedValue)).toBe('100.00');

      set(value, bigNumberify(200));
      expect(get(formatter.renderedValue)).toBe('200.00');
    });

    it('should update when settings change', () => {
      const value = ref(bigNumberify(1234.5678));
      const formatter = useAmountFormatter({ value });

      expect(get(formatter.renderedValue)).toBe('1,234.56');

      updateGeneralSettings({ uiFloatingPrecision: 4 });

      expect(get(formatter.renderedValue)).toBe('1,234.5678');
    });
  });
});
