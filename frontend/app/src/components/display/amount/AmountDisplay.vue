<script setup lang="ts">
import type { RoundingMode } from '@/types/settings/frontend-settings';
import { BigNumber, bigNumberify, One, Zero } from '@rotki/common';
import { or } from '@vueuse/math';
import CopyTooltip from '@/components/helper/CopyTooltip.vue';
import { type AssetResolutionOptions, useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useNumberScrambler } from '@/composables/utils/useNumberScrambler';
import { displayAmountFormatter } from '@/data/amount-formatter';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useHistoricCachePriceStore } from '@/store/prices/historic';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { type Currency, CURRENCY_USD, type ShownCurrency, useCurrencies } from '@/types/currencies';
import { PriceOracle } from '@/types/settings/price-oracle';
import { millisecondsToSeconds } from '@/utils/date';
import { generateRandomScrambleMultiplier } from '@/utils/session';

export interface AmountInputProps {
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
  isAssetPrice?: boolean;
  noTruncate?: boolean;
  timestamp?: number;
  // Whether the `timestamp` prop is presented with `milliseconds` value or not
  milliseconds?: boolean;
  /**
   * Amount display text is really large
   */
  xl?: boolean;
  resolutionOptions?: AssetResolutionOptions;
}

const props = withDefaults(
  defineProps<AmountInputProps>(),
  {
    amount: () => One,
    asset: '',
    assetPadding: 0,
    fiatCurrency: null,
    forceCurrency: false,
    integer: false,
    isAssetPrice: false,
    loading: false,
    milliseconds: false,
    noTruncate: false,
    pnl: false,
    priceAsset: '',
    priceOfAsset: null,
    resolutionOptions: () => ({}),
    showCurrency: 'none',
    timestamp: -1,
    xl: false,
  },
);

const {
  amount,
  asset,
  fiatCurrency: sourceCurrency,
  forceCurrency,
  integer,
  isAssetPrice,
  loading,
  milliseconds,
  priceAsset,
  priceOfAsset,
  resolutionOptions,
  timestamp,
  value,
} = toRefs(props);

const { t } = useI18n({ useScope: 'global' });

const { currency, currencySymbol: currentCurrency, floatingPrecision } = storeToRefs(useGeneralSettingsStore());

const { scrambleData, scrambleMultiplier: scrambleMultiplierRef, shouldShowAmount } = storeToRefs(useFrontendSettingsStore());

const scrambleMultiplier = ref<number>(get(scrambleMultiplierRef) ?? generateRandomScrambleMultiplier());

watchEffect(() => {
  const newValue = get(scrambleMultiplierRef);
  if (newValue !== undefined)
    set(scrambleMultiplier, newValue);
});

const { assetPrice, isAssetPriceInCurrentCurrency, useExchangeRate } = usePriceUtils();

const {
  abbreviateNumber,
  amountRoundingMode,
  currencyLocation,
  decimalSeparator,
  minimumDigitToBeAbbreviated,
  subscriptDecimals,
  thousandSeparator,
  valueRoundingMode,
} = storeToRefs(useFrontendSettingsStore());

const isCurrentCurrency = isAssetPriceInCurrentCurrency(priceAsset);

const { findCurrency } = useCurrencies();

const { createKey, historicPriceInCurrentCurrency, isPending } = useHistoricCachePriceStore();

const { assetInfo } = useAssetInfoRetrieval();

const timestampToUse = computed(() => {
  const timestampVal = get(timestamp);
  return get(milliseconds) ? millisecondsToSeconds(timestampVal) : timestampVal;
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

  const multiplierRate = to === CURRENCY_USD ? One : get(useExchangeRate(to));
  const dividerRate = from === CURRENCY_USD ? One : get(useExchangeRate(from));

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
  const isCurrentCurrencyVal = get(isCurrentCurrency);
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
    if (assetHistoricRate.gt(0))
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
  enabled: computed(() => !get(isAssetPrice) && (get(scrambleData) || !get(shouldShowAmount))),
  multiplier: scrambleMultiplier,
  value: internalValue,
});

// Check if the `realValue` is NaN
const isNaN = computed<boolean>(() => get(displayValue).isNaN());

// Decimal place of `realValue`
const decimalPlaces = computed<number>(() => get(displayValue).decimalPlaces() ?? 0);

const zeroDisplay = '0';
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
      get(displayValue).toExponential(floatingPrecisionUsed, get(subscriptDecimals) ? undefined : get(rounding)),
      get(thousandSeparator),
      get(decimalSeparator),
    );
  }

  return displayAmountFormatter.format(
    get(displayValue),
    floatingPrecisionUsed,
    get(thousandSeparator),
    get(decimalSeparator),
    get(subscriptDecimals) ? undefined : get(rounding),
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
  if (get(subscriptDecimals)) {
    return '';
  }

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

const shouldUseSubscript = computed(() => {
  if (!get(subscriptDecimals) || get(showExponential) || get(abbreviate)) {
    return false;
  }

  const value = get(displayValue);

  // only apply to decimal numbers between 0 and 1
  if (!value.lt(1) || !value.gt(0) || value.isZero() || value.isNaN()) {
    return false;
  }

  const valueString = value.toFormat(value.decimalPlaces() || 0);
  const [, decimalPart = ''] = valueString.split(get(decimalSeparator));

  const leadingZeros = decimalPart.match(/^0+/)?.[0]?.length || 0;

  // only use subscript for 2 or more leading zeros
  return leadingZeros >= 2;
});

const defaultShownCurrency = computed<ShownCurrency>(() => {
  const type = props.showCurrency;
  return type === 'none' && !!get(sourceCurrency) ? 'symbol' : type;
});

const numberParts = computed(() => {
  if (!get(shouldUseSubscript)) {
    return { full: get(renderedValue) };
  }

  const value = get(displayValue);
  const precision = get(integer) ? 0 : get(floatingPrecision);
  const [wholePart, decimalPart = ''] = value.toFormat(value.decimalPlaces() || 0).split(get(decimalSeparator));

  // only process decimal numbers
  if (!decimalPart || wholePart !== '0') {
    return { full: get(renderedValue) };
  }

  const match = decimalPart.match(/^(0+)(\d+)$/);
  if (!match) {
    return { full: get(renderedValue) };
  }

  const [, zeros, significantPart] = match;
  const zeroCount = zeros.length;

  let digits;
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

const anyLoading = logicOr(loading, evaluating);
const info = assetInfo(asset, resolutionOptions);
const { getAssetPriceOracle, isManualAssetPrice } = usePriceUtils();
const isManualPrice = isManualAssetPrice(priceAsset);

const assetOracle = computed<string | undefined>(() => {
  if (!get(isAssetPrice) || !get(priceAsset))
    return undefined;
  const oracleKey = get(getAssetPriceOracle(priceAsset));
  const mapping: Record<string, string> = {
    [PriceOracle.MANUALCURRENT]: t('oracles.manual_current'),
    [PriceOracle.UNISWAP2]: t('oracles.uniswap_v2'),
    [PriceOracle.UNISWAP3]: t('oracles.uniswap_v3'),
  };

  return mapping[oracleKey] || oracleKey;
});

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
          name="lu-sparkles"
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
          :disabled="!shouldShowAmount"
          :tooltip="tooltip"
          data-cy="display-amount"
          :value="copyValue"
        >
          <template v-if="numberParts.full">
            {{ numberParts.full }}
          </template>
          <template v-else>
            <span>{{ numberParts.whole }}</span>
            <span>{{ numberParts.separator }}</span>
            <span>{{ zeroDisplay }}</span>
            <span
              class="text-[0.8em] align-bottom relative top-[0.35em]"
              data-cy="amount-display-subscript"
            >
              {{ numberParts.leadingZeros }}
            </span>
            <span>
              {{ numberParts.significantDigits }}
            </span>
          </template>
          <template #tooltip>
            <RuiChip
              v-if="assetOracle"
              color="warning"
              content-class="!text-[10px]"
              class="font-bold leading-3 uppercase !p-0.5 mb-0.5 mt-0.5"
              size="sm"
            >
              <div class="flex gap-1">
                <RuiIcon
                  name="lu-info"
                  size="12"
                />
                {{ assetOracle }}
              </div>
            </RuiChip>
            <div v-if="tooltip">
              {{ tooltip }}
            </div>
          </template>
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
  @apply text-[2rem] leading-[3rem];

  @screen sm {
    @apply text-[3rem] leading-[4rem];
  }
}

.loading {
  &:after {
    content: '\200B';
  }
}
</style>
