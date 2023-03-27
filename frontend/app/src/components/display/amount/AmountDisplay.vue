<script setup lang="ts">
import { BigNumber } from '@rotki/common';
import { type ComputedRef, type Ref } from 'vue';
import { displayAmountFormatter } from '@/data/amount_formatter';
import { CURRENCY_USD, type Currency, useCurrencies } from '@/types/currencies';
import { One, Zero } from '@/utils/bignumbers';
import { type RoundingMode } from '@/types/frontend-settings';
import { assert } from '@/utils/assertions';
import { logger } from '@/utils/logging';

const CurrencyType = ['none', 'ticker', 'symbol', 'name'] as const;
type ShownCurrency = (typeof CurrencyType)[number];

const props = withDefaults(
  defineProps<{
    value: BigNumber;
    loading?: boolean;
    amount?: BigNumber;
    // This is what the fiat currency is `value` in. If it is null, it means we want to show it the way it is, no conversion, e.g. amount of an asset.
    fiatCurrency?: string | null;
    showCurrency?: ShownCurrency;
    forceCurrency?: boolean;
    asset?: string;
    // This is price of `priceAsset`
    priceOfAsset?: BigNumber | null;
    // This is asset we want to calculate the value from, instead get it directly from `value`
    priceAsset?: string;
    integer?: boolean;
    assetPadding?: number;
    // This prop to give color to the text based on the value
    pnl?: boolean;
    noScramble?: boolean;
    timestamp?: number;
    /**
     * Amount display text is really large
     */
    xl?: boolean;
  }>(),
  {
    loading: false,
    amount: () => One,
    fiatCurrency: null,
    showCurrency: 'none',
    forceCurrency: false,
    asset: '',
    priceOfAsset: null,
    priceAsset: '',
    integer: false,
    assetPadding: 0,
    pnl: false,
    noScramble: false,
    timestamp: -1,
    xl: false
  }
);

const {
  amount,
  value,
  asset,
  fiatCurrency: sourceCurrency,
  showCurrency,
  priceOfAsset,
  priceAsset,
  integer,
  forceCurrency,
  noScramble,
  timestamp
} = toRefs(props);

const evaluating: Ref<boolean> = ref(false);

const {
  currency,
  currencySymbol: currentCurrency,
  floatingPrecision
} = storeToRefs(useGeneralSettingsStore());

const { scrambleData, shouldShowAmount, scrambleMultiplier } = storeToRefs(
  useSessionSettingsStore()
);

const { exchangeRate, assetPrice, getHistoricPrice } = useBalancePricesStore();

const {
  abbreviateNumber,
  thousandSeparator,
  decimalSeparator,
  currencyLocation,
  amountRoundingMode,
  valueRoundingMode
} = storeToRefs(useFrontendSettingsStore());

const { isAssetPriceInCurrentCurrency } = useBalancePricesStore();

const isCurrentCurrency = isAssetPriceInCurrentCurrency(priceAsset);

const { findCurrency } = useCurrencies();

const priceHistoricRate = asyncComputed(
  async () => {
    assert(isDefined(priceAsset));
    return await getHistoricPrice({
      fromAsset: get(priceAsset),
      toAsset: get(currentCurrency),
      timestamp: get(timestamp)
    });
  },
  One.negated(),
  {
    lazy: true,
    evaluating,
    onError(e: any) {
      logger.error(e);
    }
  }
);

const historicExchangeRate = asyncComputed(
  async () => {
    assert(isDefined(sourceCurrency));
    return await getHistoricPrice({
      fromAsset: get(sourceCurrency),
      toAsset: get(currentCurrency),
      timestamp: get(timestamp)
    });
  },
  One.negated(),
  {
    lazy: true,
    evaluating,
    onError(e: any) {
      logger.error(e);
    }
  }
);

const latestFiatValue: ComputedRef<BigNumber> = computed(() => {
  const currentValue = get(value);
  const to = get(currentCurrency);
  const from = get(sourceCurrency);

  if (!from || to === from) {
    return currentValue;
  }
  const multiplierRate = to === CURRENCY_USD ? One : get(exchangeRate(to));
  const dividerRate = from === CURRENCY_USD ? One : get(exchangeRate(from));

  if (!multiplierRate || !dividerRate) {
    return currentValue;
  }
  return currentValue.multipliedBy(multiplierRate).dividedBy(dividerRate);
});

const internalValue: ComputedRef<BigNumber> = computed(() => {
  // If there is no `sourceCurrency`, it means that no fiat currency, or the unit is asset not fiat, hence we should just show the `value` passed.
  // If `forceCurrency` is true, we should also just return the value.
  if (!isDefined(sourceCurrency) || get(forceCurrency)) {
    return get(value);
  }

  const sourceCurrencyVal = get(sourceCurrency)!;
  const currentCurrencyVal = get(currentCurrency);
  const priceAssetVal = get(priceAsset);
  const isCurrentCurrencyVal = get(isCurrentCurrency);

  // If `priceAsset` is defined, it means we will not use value from `value`, but calculate it ourselves from the price of `priceAsset`
  if (priceAssetVal) {
    if (priceAssetVal === currentCurrencyVal) {
      return get(amount);
    }

    // If `isCurrentCurrency` is true, we should calculate the value by `amount * priceOfAsset`
    if (isCurrentCurrencyVal && isDefined(priceOfAsset)) {
      const priceOfAssetVal = get(priceOfAsset) || get(assetPrice(priceAsset));
      return get(amount).multipliedBy(priceOfAssetVal);
    }
  }

  if (get(timestamp) > 0 && get(amount) && get(priceAsset)) {
    const assetHistoricRate = get(priceHistoricRate);
    if (assetHistoricRate.isPositive()) {
      return get(amount).multipliedBy(assetHistoricRate);
    }
  }

  // If `sourceCurrency` and `currentCurrency` is not equal, we should convert the value
  if (sourceCurrencyVal !== currentCurrencyVal) {
    let calculatedValue = get(latestFiatValue);

    if (get(timestamp) > 0) {
      const historicRate = get(historicExchangeRate);
      if (historicRate.isPositive()) {
        calculatedValue = get(value).multipliedBy(historicRate);
      } else {
        calculatedValue = Zero;
      }
    }

    return calculatedValue;
  }

  return get(value);
});

const displayValue: ComputedRef<BigNumber> = useNumberScrambler({
  value: internalValue,
  multiplier: scrambleMultiplier,
  enabled: computed(
    () => !get(noScramble) && (get(scrambleData) || !get(shouldShowAmount))
  )
});

// Check if the `realValue` is NaN
const isNaN: ComputedRef<boolean> = computed(() => get(displayValue).isNaN());

// Decimal place of `realValue`
const decimalPlaces: ComputedRef<number> = computed(
  () => get(displayValue).decimalPlaces() ?? 0
);

// Set exponential notation when the `realValue` is too big
const showExponential: ComputedRef<boolean> = computed(() =>
  get(displayValue).gt(1e15)
);

const rounding: ComputedRef<RoundingMode | undefined> = computed(() => {
  if (isDefined(sourceCurrency)) {
    return get(valueRoundingMode);
  }
  return get(amountRoundingMode);
});

const renderedValue: ComputedRef<string> = computed(() => {
  const floatingPrecisionUsed = get(integer) ? 0 : get(floatingPrecision);

  if (get(isNaN)) {
    return '-';
  }

  if (get(showExponential)) {
    return fixExponentialSeparators(
      get(displayValue).toExponential(floatingPrecisionUsed, get(rounding)),
      get(thousandSeparator),
      get(decimalSeparator)
    );
  }

  return displayAmountFormatter.format(
    get(displayValue),
    floatingPrecisionUsed,
    get(thousandSeparator),
    get(decimalSeparator),
    get(rounding),
    get(abbreviateNumber)
  );
});

const tooltip: ComputedRef<string | null> = computed(() => {
  if (get(decimalPlaces) > get(floatingPrecision) || get(showExponential)) {
    const value = get(displayValue);
    return value.toFormat(value.decimalPlaces() ?? 0);
  }
  return null;
});

const displayCurrency: ComputedRef<Currency> = computed(() => {
  const fiat = get(sourceCurrency);
  if (get(forceCurrency) && fiat) {
    return findCurrency(fiat);
  }

  return get(currency);
});

const comparisonSymbol: ComputedRef<'' | '<' | '>'> = computed(() => {
  const value = get(displayValue);
  const floatingPrecisionUsed = get(integer) ? 0 : get(floatingPrecision);
  const decimals = get(decimalPlaces);
  const hiddenDecimals = decimals > floatingPrecisionUsed;

  if (hiddenDecimals && get(rounding) === BigNumber.ROUND_UP) {
    return '<';
  } else if (
    value.abs().lt(1) &&
    hiddenDecimals &&
    get(rounding) === BigNumber.ROUND_DOWN
  ) {
    return '>';
  }

  return '';
});

const shownCurrency: ComputedRef<ShownCurrency> = computed(() => {
  const show = get(showCurrency);
  return show === 'none' && !!get(sourceCurrency) ? 'symbol' : show;
});

const shouldShowCurrency: ComputedRef<boolean> = computed(
  () => !get(isNaN) && !!(get(shownCurrency) !== 'none' || get(asset))
);

// Copy
const copyValue: ComputedRef<string> = computed(() => {
  if (get(isNaN)) {
    return '-';
  }
  return get(displayValue).toString();
});

const fixExponentialSeparators = (
  value: string,
  thousands: string,
  decimals: string
) => {
  if (thousands !== ',' || decimals !== '.') {
    return value.replace(/[,.]/g, $1 => {
      if ($1 === ',') {
        return thousands;
      }
      if ($1 === '.') {
        return decimals;
      }
      return $1;
    });
  }
  return value;
};

const { copy, copied } = useCopy(copyValue);
const css = useCssModule();
</script>

<template>
  <div class="d-inline-block">
    <div class="d-flex flex-row align-baseline">
      <manual-price-indicator :price-asset="priceAsset" />
      <span
        :class="{
          [css.blur]: !shouldShowAmount,
          [css.profit]: pnl && displayValue.gt(0),
          [css.loss]: pnl && displayValue.lt(0),
          [css.display]: true,
          [css.xl]: xl
        }"
        data-cy="display-wrapper"
        @click="copy()"
      >
        <v-skeleton-loader
          :loading="loading || evaluating"
          min-width="60"
          max-width="70"
          class="d-flex flex-row align-baseline"
          type="text"
        >
          <span
            v-if="comparisonSymbol"
            class="mr-1"
            data-cy="display-comparison-symbol"
          >
            {{ comparisonSymbol }}
          </span>
          <div
            v-if="shouldShowCurrency && currencyLocation === 'before'"
            class="mr-1"
          >
            <amount-currency
              :show-currency="shownCurrency"
              :currency="displayCurrency"
              :asset="asset"
              :xl="xl"
            />
          </div>
          <copy-tooltip
            :copied="copied"
            :value="renderedValue"
            :tooltip="tooltip"
          />
          <div
            v-if="shouldShowCurrency && currencyLocation === 'after'"
            class="ml-1"
          >
            <amount-currency
              :asset-padding="assetPadding"
              :show-currency="shownCurrency"
              :currency="displayCurrency"
              :asset="asset"
              :xl="xl"
            />
          </div>
        </v-skeleton-loader>
      </span>
    </div>
  </div>
</template>

<style module lang="scss">
.profit {
  color: var(--v-rotki-gain-base);
}

.loss {
  color: var(--v-rotki-loss-base);
}

.display {
  display: inline-block;

  span {
    display: inline-block;
  }

  &:hover {
    cursor: pointer;
  }
}

.blur {
  filter: blur(0.75em);
}

.xl {
  font-size: 3.5em;
  line-height: 4rem;

  @media (max-width: 450px) {
    font-size: 2.4em;
    line-height: 2.4rem;
  }
}
</style>
