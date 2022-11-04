<template>
  <div class="d-inline-block">
    <div class="d-flex flex-row align-baseline">
      <div v-if="isManualPrice" class="mr-2 d-inline-block">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <v-icon class="mr-1" small color="warning" v-on="on">
              mdi-auto-fix
            </v-icon>
          </template>
          <span>{{ t('amount_display.manual_tooltip') }}</span>
        </v-tooltip>
      </div>
      <span
        class="amount-display"
        :class="{
          'blur-content': !shouldShowAmount,
          'amount-display--profit': pnl && realValue.gt(0),
          'amount-display--loss': pnl && realValue.lt(0)
        }"
        @click="copy()"
      >
        <v-skeleton-loader
          :loading="loading"
          min-width="60"
          max-width="70"
          class="d-flex flex-row align-baseline"
          type="text"
        >
          <span
            v-if="comparisonSymbol"
            class="mr-1 amount-display__comparison-symbol"
            data-cy="display-comparison-symbol"
          >
            {{ comparisonSymbol }}
          </span>
          <div
            v-if="shouldShowCurrency && currencyLocation === 'before'"
            class="mr-1"
          >
            <amount-currency
              class="amount-display__currency"
              :show-currency="shownCurrency"
              :currency="currency"
              :asset="symbol"
            />
          </div>
          <span>
            <v-tooltip top open-delay="200ms">
              <template #activator="{ on, attrs }">
                <span
                  data-cy="display-amount"
                  class="amount-display__value text-no-wrap"
                  v-bind="attrs"
                  v-on="on"
                >
                  {{ renderedValue }}
                </span>
              </template>
              <div class="text-center">
                <div
                  v-if="showTooltipValue"
                  class="amount-display__full-value"
                  data-cy="display-full-value"
                >
                  {{ tooltipValue }}
                </div>
                <div class="amount-display__copy-instruction">
                  <div
                    class="amount-display__copy-instruction__wrapper text-uppercase font-weight-bold text-caption"
                    :class="{
                      'amount-display__copy-instruction__wrapper--copied':
                        copied
                    }"
                  >
                    <div>
                      {{ t('amount_display.click_to_copy') }}
                    </div>
                    <div class="green--text text--lighten-2">
                      {{ t('amount_display.copied') }}
                    </div>
                  </div>
                </div>
              </div>
            </v-tooltip>
          </span>
          <div
            v-if="shouldShowCurrency && currencyLocation === 'after'"
            class="ml-1"
          >
            <amount-currency
              :asset-padding="assetPadding"
              class="amount-display__currency"
              :show-currency="shownCurrency"
              :currency="renderedCurrency"
              :asset="symbol"
            />
          </div>
        </v-skeleton-loader>
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { BigNumber } from '@rotki/common';
import { MaybeRef } from '@vueuse/core';
import { ComputedRef, PropType } from 'vue';
import AmountCurrency from '@/components/display/AmountCurrency.vue';
import { displayAmountFormatter } from '@/data/amount_formatter';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSessionSettingsStore } from '@/store/settings/session';
import { Currency, CURRENCY_USD, useCurrencies } from '@/types/currencies';
import { One } from '@/utils/bignumbers';
import RoundingMode = BigNumber.RoundingMode;

const CurrencyType = ['none', 'ticker', 'symbol', 'name'] as const;
type ShownCurrency = typeof CurrencyType[number];

const { t } = useI18n();

const props = defineProps({
  value: { required: true, type: BigNumber },
  loading: { required: false, type: Boolean, default: false },
  amount: {
    required: false,
    type: BigNumber,
    default: () => One
  },

  // This is what the fiat currency is `value` in. If it is null, it means we want to show it the way it is, no conversion, e.g. amount of an asset.
  fiatCurrency: {
    required: false,
    type: String as PropType<string | null>,
    default: null
  },
  showCurrency: {
    required: false,
    default: 'none',
    type: String as PropType<ShownCurrency>
  },
  forceCurrency: { required: false, type: Boolean, default: false },
  asset: { required: false, type: String, default: '' },

  // This is price of `priceAsset`
  priceOfAsset: { required: false, type: BigNumber, default: null },

  // This is asset we want to calculate the value from, instead get it directly from `value`
  priceAsset: { required: false, type: String, default: '' },
  integer: { required: false, type: Boolean, default: false },
  assetPadding: {
    required: false,
    type: Number,
    default: 0,
    validator: (chars: number) => chars >= 0 && chars <= 5
  },

  // This prop to give color to the text based on the value
  pnl: { required: false, type: Boolean, default: false }
});

const {
  amount,
  value,
  asset,
  fiatCurrency: sourceCurrency,
  showCurrency,
  priceOfAsset,
  priceAsset,
  integer,
  forceCurrency
} = toRefs(props);

const {
  currency,
  currencySymbol: currentCurrency,
  floatingPrecision
} = storeToRefs(useGeneralSettingsStore());

const { scrambleData, shouldShowAmount } = storeToRefs(
  useSessionSettingsStore()
);

const { exchangeRate, assetPrice } = useBalancePricesStore();

const {
  thousandSeparator,
  decimalSeparator,
  currencyLocation,
  amountRoundingMode,
  valueRoundingMode
} = storeToRefs(useFrontendSettingsStore());

const { isManualAssetPrice, isAssetPriceInCurrentCurrency } =
  useBalancePricesStore();

const isManualPrice = isManualAssetPrice(priceAsset);
const isCurrentCurrency = isAssetPriceInCurrentCurrency(priceAsset);

const { assetSymbol } = useAssetInfoRetrieval();
const { findCurrency } = useCurrencies();

const symbol = computed<string>(() => {
  const identifier = get(asset);
  if (!identifier) {
    return '';
  }

  return get(assetSymbol(identifier));
});

const convertFiat = (
  value: MaybeRef<BigNumber>,
  to: MaybeRef<string>,
  from: MaybeRef<string> = CURRENCY_USD
): BigNumber => {
  const valueVal = get(value);
  const toVal = get(to);
  const fromVal = get(from);

  if (toVal === fromVal) return valueVal;
  const multiplierRate = to === CURRENCY_USD ? One : get(exchangeRate(toVal));
  const dividerRate = from === CURRENCY_USD ? One : get(exchangeRate(fromVal));

  if (!multiplierRate || !dividerRate) return valueVal;
  return valueVal.multipliedBy(multiplierRate).dividedBy(dividerRate);
};

const realValue = computed<BigNumber>(() => {
  // Return a random number if scrambleData is on
  if (get(scrambleData) || !get(shouldShowAmount)) {
    const multiplier = [10, 100, 1000];

    return BigNumber.random().multipliedBy(
      multiplier[Math.floor(Math.random() * multiplier.length)]
    );
  }

  // If there is no `sourceCurrency`, it means that no fiat currency, or the unit is asset not fiat, hence we should just show the `value` passed.
  // If `forceCurrency` is true, we should also just return the value.
  if (!get(sourceCurrency) || get(forceCurrency)) return get(value);

  const sourceCurrencyVal = get(sourceCurrency)!;
  const currentCurrencyVal = get(currentCurrency);
  const priceAssetVal = get(priceAsset);
  const isCurrentCurrencyVal = get(isCurrentCurrency);

  // If `priceAsset` is defined, it means we will not use value from `value`, but calculate it ourself from the price of `priceAsset`
  if (priceAssetVal) {
    if (priceAssetVal === currentCurrencyVal) {
      return get(amount);
    }

    // If `isCurrentCurrency` is true, we should calculate the value by `amount * priceOfAsset`
    if (isCurrentCurrencyVal) {
      const priceOfAssetVal = get(priceOfAsset) || get(assetPrice(priceAsset));
      return get(amount).multipliedBy(priceOfAssetVal);
    }
  }

  // If `sourceCurrency` and `currentCurrency` is not equal, we should convert the value
  if (sourceCurrencyVal !== currentCurrencyVal) {
    return convertFiat(value, currentCurrencyVal, sourceCurrencyVal);
  }

  return get(value);
});

// Check if the `realValue` is NaN
const isNaN: ComputedRef<boolean> = computed(() => get(realValue).isNaN());

// Decimal place of `realValue`
const decimalPlaces = computed<number>(
  () => get(realValue).decimalPlaces() ?? 0
);

// Set exponential notation when the `realValue` is too big
const showExponential = computed<boolean>(() => {
  return get(realValue).gt(1e15);
});

const rounding = computed<RoundingMode | undefined>(() => {
  const isValue = get(sourceCurrency);
  if (isValue) {
    return get(valueRoundingMode);
  }
  return get(amountRoundingMode);
});

const renderedValue: ComputedRef<string> = computed(() => {
  const floatingPrecisionUsed = get(integer) ? 0 : get(floatingPrecision);

  if (get(isNaN)) return '-';

  if (get(showExponential)) {
    let exponentialValue = get(realValue).toExponential(
      floatingPrecisionUsed,
      get(rounding)
    );

    if (get(thousandSeparator) !== ',' || get(decimalSeparator) !== '.') {
      exponentialValue = exponentialValue.replace(/[,.]/g, $1 => {
        if ($1 === ',') return get(thousandSeparator);
        if ($1 === '.') return get(decimalSeparator);
        return $1;
      });
    }

    return exponentialValue;
  }

  return displayAmountFormatter.format(
    get(realValue),
    floatingPrecisionUsed,
    get(thousandSeparator),
    get(decimalSeparator),
    get(rounding)
  );
});

const tooltipValue: ComputedRef<string> = computed(() => {
  const value = get(realValue);
  return value.toFormat(value.decimalPlaces() ?? 0);
});

const renderedCurrency = computed<Currency>(() => {
  const fiat = get(sourceCurrency);
  if (get(forceCurrency) && fiat) {
    return findCurrency(fiat);
  }

  return get(currency);
});

const comparisonSymbol = computed(() => {
  const realValueVal = get(realValue);
  const floatingPrecisionUsed = get(integer) ? 0 : get(floatingPrecision);
  const decimals = get(decimalPlaces);
  const hiddenDecimals = decimals > floatingPrecisionUsed;

  if (hiddenDecimals && get(rounding) === BigNumber.ROUND_UP) {
    return '<';
  } else if (
    realValueVal.abs().lt(1) &&
    hiddenDecimals &&
    get(rounding) === BigNumber.ROUND_DOWN
  ) {
    return '>';
  }

  return '';
});

const showTooltipValue: ComputedRef<boolean> = computed(() => {
  return get(decimalPlaces) > get(floatingPrecision) || get(showExponential);
});

const shownCurrency = computed<ShownCurrency>(() => {
  const show = get(showCurrency);
  return show === 'none' && !!get(sourceCurrency) ? 'symbol' : show;
});

const shouldShowCurrency: ComputedRef<boolean> = computed(() => {
  return !get(isNaN) && !!(get(shownCurrency) !== 'none' || get(symbol));
});

// Copy
const realValueInString: ComputedRef<string> = computed(() => {
  if (get(isNaN)) return '-';
  return get(realValue).toString();
});

const { copy: copyText } = useClipboard({
  source: realValueInString
});

const copied = ref<boolean>(false);
const { start, stop, isPending } = useTimeoutFn(
  () => {
    set(copied, false);
  },
  4000,
  { immediate: false }
);

const { start: startAnimation } = useTimeoutFn(
  () => {
    set(copied, true);
    start();
  },
  100,
  { immediate: false }
);

const copy = async () => {
  await copyText();
  if (get(isPending)) {
    stop();
    set(copied, false);
  }
  startAnimation();
};
</script>

<style scoped lang="scss">
.amount-display {
  display: inline-block;

  span {
    display: inline-block;
  }

  &:hover {
    cursor: pointer;
  }

  &--profit {
    color: var(--v-rotki-gain-base);
  }

  &--loss {
    color: var(--v-rotki-loss-base);
  }

  &__copy-instruction {
    height: 20px;
    overflow: hidden;

    &__wrapper {
      transition: 0.2s all;

      &--copied {
        margin-top: -20px;
      }
    }
  }
}

.blur-content {
  filter: blur(0.75em);
}
</style>
