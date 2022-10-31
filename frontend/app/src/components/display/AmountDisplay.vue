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
          'amount-display--profit': pnl && value.gt(0),
          'amount-display--loss': pnl && value.lt(0)
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
                  {{ formattedValue }}
                </span>
              </template>
              <div class="text-center">
                <div
                  v-if="showFullValue"
                  class="amount-display__full-value"
                  data-cy="display-full-value"
                >
                  {{ fullFormattedValue }}
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
import { ComputedRef, PropType } from 'vue';
import AmountCurrency from '@/components/display/AmountCurrency.vue';
import { displayAmountFormatter } from '@/data/amount_formatter';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSessionSettingsStore } from '@/store/settings/session';
import { useCurrencies, Currency } from '@/types/currencies';
import { bigNumberify } from '@/utils/bignumbers';
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
    default: null
  },
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
  priceAsset: { required: false, type: String, default: '' },
  integer: { required: false, type: Boolean, default: false },
  assetPadding: {
    required: false,
    type: Number,
    default: 0,
    validator: (chars: number) => chars >= 0 && chars <= 5
  },
  pnl: { required: false, type: Boolean, default: false },
  tooltip: { required: false, type: Boolean, default: false }
});

const {
  amount,
  value,
  asset,
  fiatCurrency,
  showCurrency,
  priceAsset,
  integer,
  forceCurrency,
  tooltip
} = toRefs(props);
const { currency, currencySymbol, floatingPrecision } = storeToRefs(
  useGeneralSettingsStore()
);

const { scrambleData, shouldShowAmount } = storeToRefs(
  useSessionSettingsStore()
);

const { exchangeRate } = useBalancePricesStore();

const {
  thousandSeparator,
  decimalSeparator,
  currencyLocation,
  amountRoundingMode,
  valueRoundingMode
} = storeToRefs(useFrontendSettingsStore());

const { assetSymbol } = useAssetInfoRetrieval();
const { findCurrency } = useCurrencies();

const symbol = computed<string>(() => {
  const identifier = get(asset);
  if (!identifier) {
    return '';
  }

  return get(assetSymbol(identifier));
});

const copied = ref<boolean>(false);

const shownCurrency = computed<ShownCurrency>(() => {
  const show = get(showCurrency);
  return show === 'none' && !!get(fiatCurrency) ? 'symbol' : show;
});

const isPriceAsset = computed<boolean>(() => {
  return get(currencySymbol) === get(priceAsset);
});

const renderValue = computed<BigNumber>(() => {
  let valueToRender;

  // return a random number if scrambleData is on
  if (get(scrambleData) || !get(shouldShowAmount)) {
    const multiplier = [10, 100, 1000];

    return BigNumber.random().multipliedBy(
      multiplier[Math.floor(Math.random() * multiplier.length)]
    );
  }

  if (get(amount) && get(fiatCurrency) === get(currencySymbol)) {
    valueToRender = get(amount);
  } else {
    valueToRender = get(value);
  }

  // in certain cases where what is passed as a value is a string and not BigNumber, convert it
  if (typeof valueToRender === 'string') {
    return bigNumberify(valueToRender);
  }
  return valueToRender;
});

const isRenderValueNaN = computed<boolean>(() => get(renderValue).isNaN());

const renderValueDecimalPlaces = computed<number>(
  () => get(renderValue).decimalPlaces() ?? 0
);

const convertFiat = computed<boolean>(() => {
  return (
    !get(forceCurrency) &&
    !!get(fiatCurrency) &&
    get(fiatCurrency) !== get(currencySymbol)
  );
});

// Set exponential notation when the number is too big
const showExponential = computed<boolean>(() => {
  return get(renderValue).gt(1e15);
});

const formatValue = (value: BigNumber): string => {
  const floatingPrecisionUsed = get(integer) ? 0 : get(floatingPrecision);
  const price = get(convertFiat) ? convertValue(value) : value;

  if (price.isNaN()) {
    return '-';
  }
  let formattedValue = '';
  if (get(showExponential)) {
    let exponentialValue = price.toExponential(
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
    formattedValue = exponentialValue;
  } else {
    formattedValue = displayAmountFormatter.format(
      price,
      floatingPrecisionUsed,
      get(thousandSeparator),
      get(decimalSeparator),
      get(rounding)
    );
  }

  return formattedValue;
};

const comparisonSymbol = computed(() => {
  if (get(isPriceAsset)) {
    return '';
  }

  const value = get(renderValue);

  const floatingPrecisionUsed = get(integer) ? 0 : get(floatingPrecision);
  const price = get(convertFiat) ? convertValue(value) : value;
  const decimals = price.decimalPlaces() ?? 0;
  const hiddenDecimals = decimals > floatingPrecisionUsed;

  if (hiddenDecimals && get(rounding) === BigNumber.ROUND_UP) {
    return '<';
  } else if (
    price.abs().lt(1) &&
    hiddenDecimals &&
    get(rounding) === BigNumber.ROUND_DOWN
  ) {
    return '>';
  }

  return '';
});

const formattedValue = computed(() => {
  if (get(isPriceAsset)) {
    return bigNumberify(1).toFormat(get(floatingPrecision));
  }
  return formatValue(get(renderValue));
});

const convertValue = (value: BigNumber): BigNumber => {
  const rate = get(exchangeRate(get(currencySymbol)));
  return rate ? value.multipliedBy(rate) : value;
};

const fullValue = computed<BigNumber>(() => {
  return get(convertFiat) ? convertValue(get(renderValue)) : get(renderValue);
});

const fullFormattedValue = computed<string>(() => {
  const value = get(fullValue);
  return value.toFormat(value.decimalPlaces() ?? 0);
});

const rounding = computed<RoundingMode | undefined>(() => {
  const isValue = get(fiatCurrency);
  let rounding: RoundingMode | undefined = undefined;
  if (isValue) {
    rounding = get(valueRoundingMode);
  } else if (!get(convertFiat)) {
    rounding = get(amountRoundingMode);
  }
  return rounding;
});

const valueToCopy = computed<string>(() => {
  return get(fullValue).toString();
});

const { copy: copyText } = useClipboard({
  source: valueToCopy
});

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

const renderedCurrency = computed<Currency>(() => {
  const fiat = get(fiatCurrency);
  if (get(forceCurrency) && fiat) {
    return findCurrency(fiat);
  }

  return get(currency);
});

const { prices } = storeToRefs(useBalancePricesStore());

const isManualPrice: ComputedRef<boolean> = computed(() => {
  const asset = get(priceAsset);
  if (!asset) return false;
  return get(prices)[asset]?.isManualPrice || false;
});

const showFullValue: ComputedRef<boolean> = computed(() => {
  return (
    !(
      get(renderValueDecimalPlaces) <= get(floatingPrecision) && !get(tooltip)
    ) ||
    get(isPriceAsset) ||
    get(showExponential)
  );
});

const shouldShowCurrency: ComputedRef<boolean> = computed(() => {
  return (
    !get(isRenderValueNaN) && !!(get(shownCurrency) !== 'none' || get(symbol))
  );
});
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
