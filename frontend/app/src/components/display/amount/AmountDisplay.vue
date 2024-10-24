<script setup lang="ts">
import { BigNumber } from '@rotki/common';
import { or } from '@vueuse/math';
import { displayAmountFormatter } from '@/data/amount-formatter';
import { CURRENCY_USD, type Currency, type ShownCurrency, useCurrencies } from '@/types/currencies';
import type { RoundingMode } from '@/types/settings/frontend-settings';
import type { AssetResolutionOptions } from '@/composables/assets/retrieval';

const props = withDefaults(
  defineProps<{
    value: BigNumber | undefined;
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
    noTruncate?: boolean;
    timestamp?: number;
    // Whether the `timestamp` prop is presented with `milliseconds` value or not
    milliseconds?: boolean;
    /**
     * Amount display text is really large
     */
    xl?: boolean;
    resolutionOptions?: AssetResolutionOptions;
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
    noTruncate: false,
    timestamp: -1,
    milliseconds: false,
    xl: false,
    resolutionOptions: () => ({}),
  },
);

const {
  amount,
  value,
  asset,
  fiatCurrency: sourceCurrency,
  priceOfAsset,
  priceAsset,
  integer,
  forceCurrency,
  noScramble,
  timestamp,
  milliseconds,
  loading,
  resolutionOptions,
} = toRefs(props);

const { t } = useI18n();

const { currency, currencySymbol: currentCurrency, floatingPrecision } = storeToRefs(useGeneralSettingsStore());

const { scrambleData, shouldShowAmount, scrambleMultiplier } = storeToRefs(useSessionSettingsStore());

const { exchangeRate, assetPrice } = useBalancePricesStore();

const {
  abbreviateNumber,
  minimumDigitToBeAbbreviated,
  thousandSeparator,
  decimalSeparator,
  currencyLocation,
  amountRoundingMode,
  valueRoundingMode,
} = storeToRefs(useFrontendSettingsStore());

const { findCurrency } = useCurrencies();

const { historicPriceInCurrentCurrency, isPending, createKey } = useHistoricCachePriceStore();

const { assetInfo } = useAssetInfoRetrieval();

const timestampToUse = computed(() => {
  const timestampVal = get(timestamp);
  return get(milliseconds) ? Math.floor(timestampVal / 1000) : timestampVal;
});

const evaluating = or(
  isPending(createKey(get(priceAsset), get(timestampToUse))),
  isPending(createKey(get(sourceCurrency) || '', get(timestampToUse))),
);

const latestFiatValue = computed<BigNumber>(() => {
  const currentValue = get(value);
  if (!currentValue)
    return Zero;

  const to = get(currentCurrency);
  const from = get(sourceCurrency);

  if (!from || to === from)
    return currentValue;

  const multiplierRate = to === CURRENCY_USD ? One : get(exchangeRate(to));
  const dividerRate = from === CURRENCY_USD ? One : get(exchangeRate(from));

  if (!multiplierRate || !dividerRate)
    return currentValue;

  return currentValue?.multipliedBy(multiplierRate).dividedBy(dividerRate) ?? Zero;
});

const internalValue = computed<BigNumber>(() => {
  // If there is no `sourceCurrency`, it means that no fiat currency, or the unit is asset not fiat, hence we should just show the `value` passed.
  // If `forceCurrency` is true, we should also just return the value.
  if (!isDefined(sourceCurrency) || get(forceCurrency))
    return get(value) ?? Zero;

  const sourceCurrencyVal = get(sourceCurrency);
  const currentCurrencyVal = get(currentCurrency);
  const priceAssetVal = get(priceAsset);
  const isCurrentCurrencyVal = get(currentCurrencyVal) === get(sourceCurrencyVal);
  const timestampVal = get(timestampToUse);

  // If `priceAsset` is defined, it means we will not use value from `value`, but calculate it ourselves from the price of `priceAsset`
  if (priceAssetVal) {
    if (priceAssetVal === currentCurrencyVal)
      return get(amount);

    // If `isCurrentCurrency` is true, we should calculate the value by `amount * priceOfAsset`
    if (isCurrentCurrencyVal && isDefined(priceOfAsset)) {
      const priceOfAssetVal = get(priceOfAsset) || get(assetPrice(priceAsset));
      return get(amount).multipliedBy(priceOfAssetVal);
    }
  }

  if (timestampVal > 0 && get(amount) && priceAssetVal) {
    const assetHistoricRate = get(historicPriceInCurrentCurrency(priceAssetVal, timestampVal));
    if (assetHistoricRate.isPositive())
      return get(amount).multipliedBy(assetHistoricRate);
  }

  // If `sourceCurrency` and `currentCurrency` is not equal, we should convert the value
  if (sourceCurrencyVal !== currentCurrencyVal) {
    let calculatedValue = get(latestFiatValue);

    if (timestampVal > 0) {
      const historicRate = get(historicPriceInCurrentCurrency(sourceCurrencyVal, timestampVal));

      if (historicRate.isPositive())
        calculatedValue = get(value)?.multipliedBy(historicRate) ?? Zero;
      else calculatedValue = Zero;
    }

    return calculatedValue;
  }

  return get(value) ?? Zero;
});

const displayValue: ComputedRef<BigNumber> = useNumberScrambler({
  value: internalValue,
  multiplier: scrambleMultiplier,
  enabled: computed(() => !get(noScramble) && (get(scrambleData) || !get(shouldShowAmount))),
});

// Check if the `realValue` is NaN
const isNaN = computed<boolean>(() => get(displayValue).isNaN());

// Decimal place of `realValue`
const decimalPlaces = computed<number>(() => get(displayValue).decimalPlaces() ?? 0);

// Set exponential notation when the `realValue` is too big
const showExponential = computed<boolean>(() => get(displayValue).gt(1e18));

const abbreviate = computed(
  () => get(abbreviateNumber) && get(displayValue).gte(10 ** (get(minimumDigitToBeAbbreviated) - 1)),
);

const rounding = computed<RoundingMode | undefined>(() => {
  if (isDefined(sourceCurrency))
    return get(valueRoundingMode);

  return get(amountRoundingMode);
});

const renderedValue = computed<string>(() => {
  const floatingPrecisionUsed = get(integer) ? 0 : get(floatingPrecision);

  if (get(isNaN))
    return '-';

  if (get(showExponential) && !get(abbreviate)) {
    return fixExponentialSeparators(
      get(displayValue).toExponential(floatingPrecisionUsed, get(rounding)),
      get(thousandSeparator),
      get(decimalSeparator),
    );
  }

  return displayAmountFormatter.format(
    get(displayValue),
    floatingPrecisionUsed,
    get(thousandSeparator),
    get(decimalSeparator),
    get(rounding),
    get(abbreviate),
  );
});

const tooltip = computed<string | null>(() => {
  if (get(decimalPlaces) > get(floatingPrecision) || get(showExponential) || get(abbreviate)) {
    const value = get(displayValue);
    return value.toFormat(value.decimalPlaces() ?? 0);
  }
  return null;
});

const displayCurrency = computed<Currency>(() => {
  const fiat = get(sourceCurrency);
  if (get(forceCurrency) && fiat)
    return findCurrency(fiat);

  return get(currency);
});

const comparisonSymbol = computed<'' | '<' | '>'>(() => {
  const value = get(displayValue);
  const floatingPrecisionUsed = get(integer) ? 0 : get(floatingPrecision);
  const decimals = get(decimalPlaces);
  const hiddenDecimals = decimals > floatingPrecisionUsed;

  if (hiddenDecimals && get(rounding) === BigNumber.ROUND_UP)
    return '<';
  else if (value.abs().lt(1) && hiddenDecimals && get(rounding) === BigNumber.ROUND_DOWN)
    return '>';

  return '';
});

const defaultShownCurrency = computed<ShownCurrency>(() => {
  const type = props.showCurrency;
  return type === 'none' && !!get(sourceCurrency) ? 'symbol' : type;
});

const shouldShowCurrency = computed<boolean>(
  () => !get(isNaN) && !!(get(defaultShownCurrency) !== 'none' || get(asset)),
);

// Copy
const copyValue = computed<string>(() => {
  if (get(isNaN))
    return '-';

  return get(displayValue).toString();
});

function fixExponentialSeparators(value: string, thousands: string, decimals: string) {
  if (thousands !== ',' || decimals !== '.') {
    return value.replace(/[,.]/g, ($1) => {
      if ($1 === ',')
        return thousands;

      if ($1 === '.')
        return decimals;

      return $1;
    });
  }
  return value;
}

const { copy, copied } = useCopy(copyValue);

const anyLoading = logicOr(loading, evaluating);
const info = assetInfo(asset, resolutionOptions);
const { isManualAssetPrice } = useBalancePricesStore();
const isManualPrice = isManualAssetPrice(priceAsset);

const displayAsset = computed(() => {
  const assetInfo = get(info);
  if (assetInfo && assetInfo.resolved)
    return assetInfo.symbol ?? '';

  const show = get(defaultShownCurrency);
  const value = get(displayCurrency);

  if (show === 'ticker')
    return value.tickerSymbol;
  else if (show === 'symbol')
    return value.unicodeSymbol;
  else if (show === 'name')
    return value.name;

  return '';
});

const [DefineSymbol, ReuseSymbol] = createReusableTemplate<{ name: string }>();
</script>

<template>
  <div class="inline-flex items-baseline">
    <DefineSymbol #default="{ name }">
      <span
        data-cy="display-currency"
        :class="{ 'truncate max-w-[5rem]': !noTruncate }"
      >
        {{ name }}
      </span>
    </DefineSymbol>

    <RuiTooltip
      v-if="timestamp < 0 && isManualPrice"
      :popper="{ placement: 'top' }"
      :open-delay="400"
      class="self-center mr-2 cursor-pointer"
    >
      <template #activator>
        <RuiIcon
          size="16"
          color="warning"
          name="sparkling-line"
        />
      </template>

      {{ t('amount_display.manual_tooltip') }}
    </RuiTooltip>

    <span
      :class="[
        {
          'blur': !shouldShowAmount,
          'text-rui-success': pnl && displayValue.gt(0),
          'text-rui-error': pnl && displayValue.lt(0),
          [$style.xl]: xl,
          [`skeleton min-w-[3.5rem] max-w-[4rem] ${$style.loading}`]: anyLoading,
        },
      ]"
      class="inline-flex items-center gap-1 transition duration-200 rounded-lg max-w-full"
      data-cy="amount-display"
    >
      <template v-if="!anyLoading">
        <template v-if="comparisonSymbol">
          {{ comparisonSymbol }}
        </template>

        <ReuseSymbol
          v-if="shouldShowCurrency && currencyLocation === 'before'"
          :name="displayAsset"
        />

        <CopyTooltip
          :copied="copied"
          :tooltip="tooltip"
          data-cy="display-amount"
          @click="copy()"
        >
          {{ renderedValue }}
        </CopyTooltip>

        <ReuseSymbol
          v-if="shouldShowCurrency && currencyLocation === 'after'"
          :name="displayAsset"
        />
      </template>
    </span>
  </div>
</template>

<style module lang="scss">
.xl {
  @apply text-[2.4rem] leading-[3rem];

  @screen sm {
    @apply text-[3.5rem] leading-[4rem];
  }
}

.loading {
  &:after {
    content: '\200B';
  }
}
</style>
