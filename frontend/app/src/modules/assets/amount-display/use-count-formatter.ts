import { bigNumberify } from '@rotki/common';
import { getBnFormat } from '@/modules/assets/amount-display/amount-formatter';
import { useAmountDisplaySettings } from '@/modules/assets/amount-display/use-amount-display-settings';

interface UseCountFormatterReturn {
  formatCount: (count: number) => string;
}

/**
 * Formats a whole count (events, validators, notes) with the user's separators, so a count in a
 * sentence groups its digits the same way every amount in the app does.
 *
 * @remarks
 * Not an amount: no currency, rounding, abbreviation, or privacy scrambling applies.
 */
export function useCountFormatter(): UseCountFormatterReturn {
  const { decimalSeparator, thousandSeparator } = useAmountDisplaySettings();

  function formatCount(count: number): string {
    return bigNumberify(count).toFormat(0, getBnFormat(get(thousandSeparator), get(decimalSeparator)));
  }

  return { formatCount };
}
