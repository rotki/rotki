<template>
  <div
    class="amount-display"
    :class="{
      'blur-content': !shouldShowAmount,
      'amount-display--profit': pnl && value.gt(0),
      'amount-display--loss': pnl && value.lt(0)
    }"
  >
    <v-skeleton-loader
      :loading="loading"
      min-width="60"
      max-width="70"
      class="d-flex flex-row align-baseline"
      type="text"
    >
      <amount-currency
        v-if="!isRenderValueNaN && currencyLocation === 'before'"
        class="mr-1 ml-1"
        :show-currency="shownCurrency"
        :currency="currency"
        :asset="symbol"
      />
      <span>
        <v-tooltip
          top
          open-delay="400ms"
          :disabled="
            ((!!fiatCurrency ||
              renderValueDecimalPlaces <= floatingPrecision) &&
              !tooltip) ||
            isPriceAsset
          "
        >
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
          <span class="amount-display__full-value">
            {{ fullValue }}
          </span>
        </v-tooltip>
      </span>
      <amount-currency
        v-if="!isRenderValueNaN && currencyLocation === 'after'"
        class="ml-1 amount-display__currency"
        :asset-padding="assetPadding"
        :show-currency="shownCurrency"
        :currency="currency"
        :asset="symbol"
      />
    </v-skeleton-loader>
  </div>
</template>

<script lang="ts">
import { BigNumber } from '@rotki/common';
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import AmountCurrency from '@/components/display/AmountCurrency.vue';
import {
  setupAssetInfoRetrieval,
  setupExchangeRateGetter
} from '@/composables/balances';
import { setupDisplayData, setupGeneralSettings } from '@/composables/session';
import { setupSettings } from '@/composables/settings';
import { displayAmountFormatter } from '@/data/amount_formatter';
import { bigNumberify } from '@/utils/bignumbers';
import RoundingMode = BigNumber.RoundingMode;

const shownCurrency = ['none', 'ticker', 'symbol', 'name'] as const;
type ShownCurrency = typeof shownCurrency[number];

export default defineComponent({
  components: {
    AmountCurrency
  },
  props: {
    value: { required: true, type: Object as PropType<BigNumber> },
    loading: { required: false, type: Boolean, default: false },
    amount: {
      required: false,
      type: Object as PropType<BigNumber>,
      default: null
    },
    fiatCurrency: { required: false, type: String, default: null },
    showCurrency: {
      required: false,
      default: 'none',
      type: String as PropType<ShownCurrency>,
      validator: (showCurrency: ShownCurrency) => {
        return shownCurrency.indexOf(showCurrency) > -1;
      }
    },
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
  },
  setup(props) {
    const {
      amount,
      value,
      asset,
      fiatCurrency,
      showCurrency,
      priceAsset,
      integer
    } = toRefs(props);
    const { currency, currencySymbol, floatingPrecision } =
      setupGeneralSettings();

    const { scrambleData, shouldShowAmount } = setupDisplayData();

    const exchangeRate = setupExchangeRateGetter();

    const {
      thousandSeparator,
      decimalSeparator,
      currencyLocation,
      amountRoundingMode,
      valueRoundingMode
    } = setupSettings();

    const { getAssetSymbol } = setupAssetInfoRetrieval();

    const symbol = computed<string>(() => {
      if (!asset.value) {
        return '';
      }

      return getAssetSymbol(asset.value);
    });

    const shownCurrency = computed<ShownCurrency>(() => {
      return showCurrency.value === 'none' && !!fiatCurrency.value
        ? 'symbol'
        : showCurrency.value;
    });

    const isPriceAsset = computed<boolean>(() => {
      return currencySymbol.value === priceAsset.value;
    });

    const renderValue = computed<BigNumber>(() => {
      const multiplier = [10, 100, 1000];
      let valueToRender;

      // return a random number if scrambeData is on
      if (scrambleData.value) {
        return BigNumber.random()
          .multipliedBy(
            multiplier[Math.floor(Math.random() * multiplier.length)]
          )
          .plus(BigNumber.random(2));
      }

      if (amount.value && fiatCurrency.value === currencySymbol.value) {
        valueToRender = amount.value;
      } else {
        valueToRender = value.value;
      }

      // in certain cases where what is passed as a value is a string and not BigNumber, convert it
      if (typeof valueToRender === 'string') {
        return bigNumberify(valueToRender);
      }
      return valueToRender;
    });

    const isRenderValueNaN = computed<boolean>(() => renderValue.value.isNaN());

    const renderValueDecimalPlaces = computed<number>(() =>
      renderValue.value.decimalPlaces()
    );

    const convertFiat = computed<boolean>(() => {
      return (
        !!fiatCurrency.value && fiatCurrency.value !== currencySymbol.value
      );
    });

    const formatValue = (value: BigNumber): string => {
      const floatingPrecisionUsed = integer.value ? 0 : floatingPrecision.value;
      const price = convertFiat.value ? convertValue(value) : value;

      if (price.isNaN()) {
        return '-';
      }

      const formattedValue = displayAmountFormatter.format(
        price,
        floatingPrecisionUsed,
        thousandSeparator.value,
        decimalSeparator.value,
        rounding.value
      );

      const hiddenDecimals = price.decimalPlaces() > floatingPrecisionUsed;
      if (hiddenDecimals && rounding.value === BigNumber.ROUND_UP) {
        return `< ${formattedValue}`;
      } else if (
        price.lt(1) &&
        hiddenDecimals &&
        rounding.value === BigNumber.ROUND_DOWN
      ) {
        return `> ${formattedValue}`;
      }
      return formattedValue;
    };

    const formattedValue = computed(() => {
      if (isPriceAsset.value) {
        return bigNumberify(1).toFormat(floatingPrecision.value);
      }
      return formatValue(renderValue.value);
    });

    const convertValue = (value: BigNumber): BigNumber => {
      const rate = exchangeRate(currencySymbol.value);
      return rate ? value.multipliedBy(rate) : value;
    };

    const fullValue = computed<string>(() => {
      const value = convertFiat.value
        ? convertValue(renderValue.value)
        : renderValue.value;

      return value.toFormat(value.decimalPlaces());
    });

    const rounding = computed<RoundingMode | undefined>(() => {
      const isValue = fiatCurrency.value === currencySymbol.value;
      let rounding: RoundingMode | undefined = undefined;
      if (isValue) {
        rounding = valueRoundingMode.value;
      } else if (!convertFiat.value) {
        rounding = amountRoundingMode.value;
      }
      return rounding;
    });

    return {
      currency,
      shouldShowAmount,
      isRenderValueNaN,
      renderValueDecimalPlaces,
      currencyLocation,
      shownCurrency,
      symbol,
      floatingPrecision,
      isPriceAsset,
      formattedValue,
      fullValue
    };
  }
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

  &__currency {
    font-size: 1rem;
  }
}

.blur-content {
  filter: blur(0.75em);
}
</style>
