import type { ComputedRef, MaybeRef } from 'vue';
import type { RoundingType } from '@/modules/amount-display/types';
import { BigNumber, bigNumberify } from '@rotki/common';
import { displayAmountFormatter } from '@/data/amount-formatter';
import { useAmountDisplaySettings } from './use-amount-display-settings';

export interface NumberParts {
  full?: string;
  whole?: string;
  separator?: string;
  leadingZeros?: string;
  significantDigits?: string;
}

export interface AmountFormatterOptions {
  value: MaybeRef<BigNumber>;
  integer?: MaybeRef<boolean>;
  /**
   * Which rounding mode to use from frontend settings.
   * - 'value' (default): Uses valueRoundingMode setting (typically ROUND_DOWN)
   * - 'amount': Uses amountRoundingMode setting (typically ROUND_UP)
   */
  rounding?: MaybeRef<RoundingType>;
}

export interface AmountFormatterReturn {
  renderedValue: ComputedRef<string>;
  tooltip: ComputedRef<string | null>;
  comparisonSymbol: ComputedRef<'' | '<' | '>'>;
  shouldUseSubscript: ComputedRef<boolean>;
  numberParts: ComputedRef<NumberParts>;
  isNaN: ComputedRef<boolean>;
  showExponential: ComputedRef<boolean>;
  abbreviate: ComputedRef<boolean>;
}

function fixExponentialSeparators(value: string, thousands: string, decimals: string): string {
  if (!(thousands !== ',' || decimals !== '.')) {
    return value;
  }

  return value.replace(/[,.]/g, ($1) => {
    if ($1 === ',') {
      return thousands;
    }
    if ($1 === '.') {
      return decimals;
    }
    return $1;
  });
}

export function useAmountFormatter(options: AmountFormatterOptions): AmountFormatterReturn {
  const { integer = false, rounding = 'value', value } = options;

  const {
    abbreviateNumber,
    amountRoundingMode,
    decimalSeparator,
    floatingPrecision,
    minimumDigitToBeAbbreviated,
    subscriptDecimals,
    thousandSeparator,
    valueRoundingMode,
  } = useAmountDisplaySettings();

  const displayValue = computed<BigNumber>(() => get(value));

  const isNaN = computed<boolean>(() => get(displayValue).isNaN());

  const decimalPlaces = computed<number>(() => get(displayValue).decimalPlaces() ?? 0);

  const showExponential = computed<boolean>(() => get(displayValue).gt(1e18));

  const abbreviate = computed<boolean>(
    () => get(abbreviateNumber) && get(displayValue).gte(10 ** (get(minimumDigitToBeAbbreviated) - 1)),
  );

  // Use valueRoundingMode for 'value' (default), amountRoundingMode for 'amount'
  const roundingMode = computed(() => (get(rounding) === 'amount' ? get(amountRoundingMode) : get(valueRoundingMode)));

  const renderedValue = computed<string>(() => {
    const floatingPrecisionUsed = get(integer) ? 0 : get(floatingPrecision);

    if (get(isNaN)) {
      return '-';
    }

    if (get(showExponential) && !get(abbreviate)) {
      return fixExponentialSeparators(
        get(displayValue).toExponential(floatingPrecisionUsed, get(subscriptDecimals) ? undefined : get(roundingMode)),
        get(thousandSeparator),
        get(decimalSeparator),
      );
    }

    return displayAmountFormatter.format(
      get(displayValue),
      floatingPrecisionUsed,
      get(thousandSeparator),
      get(decimalSeparator),
      get(subscriptDecimals) ? undefined : get(roundingMode),
      get(abbreviate),
    );
  });

  const tooltip = computed<string | null>(() => {
    if (get(decimalPlaces) > get(floatingPrecision) || get(showExponential) || get(abbreviate)) {
      const val = get(displayValue);
      return val.toFormat(val.decimalPlaces() ?? 0);
    }
    return null;
  });

  const comparisonSymbol = computed<'' | '<' | '>'>(() => {
    if (get(subscriptDecimals)) {
      return '';
    }

    const val = get(displayValue);
    const floatingPrecisionUsed = get(integer) ? 0 : get(floatingPrecision);
    const decimals = get(decimalPlaces);
    const hiddenDecimals = decimals > floatingPrecisionUsed;

    if (hiddenDecimals && get(roundingMode) === BigNumber.ROUND_UP) {
      return '<';
    }
    else if (val.abs().lt(1) && hiddenDecimals && get(roundingMode) === BigNumber.ROUND_DOWN) {
      return '>';
    }

    return '';
  });

  const shouldUseSubscript = computed<boolean>(() => {
    if (!get(subscriptDecimals) || get(showExponential) || get(abbreviate)) {
      return false;
    }

    const val = get(displayValue);

    if (!val.lt(1) || !val.gt(0) || val.isZero() || val.isNaN()) {
      return false;
    }

    const valueString = val.toFormat(val.decimalPlaces() || 0);
    const [, decimalPart = ''] = valueString.split(get(decimalSeparator));
    const leadingZeros = decimalPart.match(/^0+/)?.[0]?.length || 0;

    return leadingZeros >= 2;
  });

  const numberParts = computed<NumberParts>(() => {
    if (!get(shouldUseSubscript)) {
      return { full: get(renderedValue) };
    }

    const val = get(displayValue);
    const precision = get(integer) ? 0 : get(floatingPrecision);
    const [wholePart, decimalPart = ''] = val.toFormat(val.decimalPlaces() || 0).split(get(decimalSeparator));

    if (!decimalPart || wholePart !== '0') {
      return { full: get(renderedValue) };
    }

    const match = decimalPart.match(/^(0+)(\d+)$/);
    if (!match) {
      return { full: get(renderedValue) };
    }

    const [, zeros, significantPart] = match;
    const zeroCount = zeros.length;

    let digits: string;
    if (significantPart.length > precision) {
      digits = displayAmountFormatter.format(
        bigNumberify(`0.${significantPart}`),
        precision,
        get(thousandSeparator),
        get(decimalSeparator),
        undefined,
        false,
      ).split(get(decimalSeparator))[1];
    }
    else {
      digits = significantPart;
    }

    return {
      leadingZeros: zeroCount.toString(),
      separator: get(decimalSeparator),
      significantDigits: digits || significantPart[0],
      whole: wholePart,
    };
  });

  return {
    abbreviate,
    comparisonSymbol,
    isNaN,
    numberParts,
    renderedValue,
    shouldUseSubscript,
    showExponential,
    tooltip,
  };
}
