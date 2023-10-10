<script setup lang="ts">
import { BigNumber } from '@rotki/common';
import { type ComputedRef } from 'vue';
import { or } from '@vueuse/math';
import { displayAmountFormatter } from '@/data/amount_formatter';
import { CURRENCY_USD, type Currency, useCurrencies } from '@/types/currencies';
import { type RoundingMode } from '@/types/settings/frontend-settings';

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
const CurrencyType = ['none', 'ticker', 'symbol', 'name'] as const;

type ShownCurrency = (typeof CurrencyType)[number];

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

const {
  currency,
  currencySymbol: currentCurrency,
  floatingPrecision
} = storeToRefs(useGeneralSettingsStore());

const { scrambleData, shouldShowAmount, scrambleMultiplier } = storeToRefs(
  useSessionSettingsStore()
);

const { exchangeRate, assetPrice, isAssetPriceInCurrentCurrency } =
  useBalancePricesStore();

const {
  abbreviateNumber,
  thousandSeparator,
  decimalSeparator,
  currencyLocation,
  amountRoundingMode,
  valueRoundingMode
} = storeToRefs(useFrontendSettingsStore());

const isCurrentCurrency = isAssetPriceInCurrentCurrency(priceAsset);

const { findCurrency } = useCurrencies();

const { historicPriceInCurrentCurrency, isPending } =
  useHistoricCachePriceStore();

const evaluating = or(
  isPending(`${get(priceAsset)}#${get(timestamp)}`),
  isPending(`${get(sourceCurrency)}#${get(timestamp)}`)
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
  const timestampVal = get(timestamp);

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

  if (timestampVal > 0 && get(amount) && priceAssetVal) {
    const assetHistoricRate = get(
      historicPriceInCurrentCurrency(priceAssetVal, timestampVal)
    );
    if (assetHistoricRate.isPositive()) {
      return get(amount).multipliedBy(assetHistoricRate);
    }
  }

  // If `sourceCurrency` and `currentCurrency` is not equal, we should convert the value
  if (sourceCurrencyVal !== currentCurrencyVal) {
    let calculatedValue = get(latestFiatValue);

    if (timestampVal > 0) {
      const historicRate = get(
        historicPriceInCurrentCurrency(sourceCurrencyVal, timestampVal)
      );

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
  if (
    get(decimalPlaces) > get(floatingPrecision) ||
    get(showExponential) ||
    get(abbreviateNumber)
  ) {
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
  <div class="inline-block">
    <div class="flex flex-row items-baseline">
      <ManualPriceIndicator v-if="timestamp < 0" :price-asset="priceAsset" />
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
        <VSkeletonLoader
          :loading="loading || evaluating"
          min-width="60"
          max-width="70"
          class="flex flex-row items-baseline"
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
            <AmountCurrency
              :show-currency="shownCurrency"
              :currency="displayCurrency"
              :asset="asset"
              :xl="xl"
            />
          </div>
          <div>
            <CopyTooltip
              :copied="copied"
              :value="renderedValue"
              :tooltip="tooltip"
            />
          </div>
          <div
            v-if="shouldShowCurrency && currencyLocation === 'after'"
            class="ml-1"
          >
            <AmountCurrency
              :asset-padding="assetPadding"
              :show-currency="shownCurrency"
              :currency="displayCurrency"
              :asset="asset"
              :xl="xl"
            />
          </div>
        </VSkeletonLoader>
      </span>
    </div>
  </div>
</template>

<style module lang="scss">
.profit {
  color: var(--v-rotki-success-base);
}

.loss {
  color: var(--v-rotki-error-base);
}

.display {
  display: inline-block;
  cursor: pointer;

  span {
    display: inline-block;
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
