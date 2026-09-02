<script setup lang="ts">
/**
 * Displays a fiat value in the user's currency.
 *
 * @remarks
 * `from` converts out of a source currency; without it the value is taken as already being in the
 * user's. `currency` overrides which symbol is shown. Values are scrambled for privacy when the
 * setting is on.
 *
 * Pairing `from` with a snapshot value means pairing it with the snapshot's timestamp too, or the
 * conversion silently uses today's rate. `SnapshotFiatDisplay` is the safe spelling for that case.
 *
 * @example
 * ```vue
 * <FiatDisplay :value="valueInUserCurrency" />
 * <FiatDisplay :value="usdValue" from="USD" />
 * <FiatDisplay :value="profit" from="USD" pnl />
 * <FiatDisplay :value="reportValue" :currency="report.profitCurrency" />
 * ```
 */
import type { BigNumber } from '@rotki/common';
import type { SymbolDisplay, Timestamp } from '@/modules/assets/amount-display/types';
import { createReusableTemplate } from '@vueuse/core';
import { useAmountDisplaySettings, useFiatConversion, useOracleInfo, useScrambledValue } from '@/modules/assets/amount-display';
import { type Currency, useCurrencies } from '@/modules/assets/amount-display/currencies';
import AmountDisplayBase from './AmountDisplayBase.vue';
import ManualPriceIndicator from './ManualPriceIndicator.vue';
import OracleBadge from './OracleBadge.vue';

interface Props {
  /** The fiat value to display */
  value: BigNumber | undefined;
  /** Source currency code - if omitted, no conversion is performed */
  from?: string;
  /** Timestamp for historic rate lookup */
  timestamp?: Timestamp;
  /** Apply PnL coloring (green positive, red negative) */
  pnl?: boolean;
  /** Loading state */
  loading?: boolean;
  /** How to display the currency: 'symbol' (default, e.g. €), 'ticker' (e.g. EUR), or 'none' */
  symbol?: SymbolDisplay;
  /** Override the displayed currency (e.g., 'USD', 'EUR'). If omitted, uses user's main currency. */
  currency?: string;
  /** Skip scrambling even when privacy mode is enabled */
  noScramble?: boolean;
  /** Asset identifier for price display - skips scrambling and shows manual price indicator if applicable */
  priceAsset?: string;
}

defineOptions({
  inheritAttrs: false,
});

const {
  from = '',
  timestamp,
  value,
  loading: loadingProp,
  noScramble: noScrambleProp,
  priceAsset,
  currency: currencyProp,
  symbol: symbolProp = 'symbol',
} = defineProps<Props>();

const [DefineAmountDisplay, ReuseAmountDisplay] = createReusableTemplate();

const { converted, loading } = useFiatConversion({
  from: () => from,
  timestamp: () => timestamp,
  value: () => value,
});
const { currency: userCurrency } = useAmountDisplaySettings();
const { findCurrency } = useCurrencies();

const hasPriceAsset = computed<boolean>(() => !!priceAsset);
const noScramble = computed<boolean>(() => noScrambleProp || get(hasPriceAsset));
const { scrambledValue } = useScrambledValue({ value: converted, noScramble });

const { assetOracle, isManualPrice } = useOracleInfo({
  isAssetPrice: hasPriceAsset,
  priceAsset: computed<string>(() => priceAsset ?? ''),
});

const showManualIndicator = computed<boolean>(() =>
  get(hasPriceAsset) && get(isManualPrice),
);

const showAssetOracle = computed<boolean>(() =>
  get(hasPriceAsset) && isDefined(assetOracle),
);

const resolvedCurrency = computed<Currency>(() => {
  if (currencyProp)
    return findCurrency(currencyProp);
  return get(userCurrency);
});

const displaySymbol = computed<string>(() => {
  const currency = get(resolvedCurrency);
  switch (symbolProp) {
    case 'none':
      return '';
    case 'ticker':
      return currency.tickerSymbol;
    case 'symbol':
    default:
      return currency.unicodeSymbol;
  }
});
</script>

<template>
  <DefineAmountDisplay>
    <AmountDisplayBase
      :value="scrambledValue"
      :symbol="displaySymbol"
      :loading="loading || loadingProp"
      :pnl="pnl"
      v-bind="$attrs"
    >
      <template
        v-if="showAssetOracle"
        #tooltip
      >
        <OracleBadge
          v-if="assetOracle"
          :oracle="assetOracle"
        />
      </template>
    </AmountDisplayBase>
  </DefineAmountDisplay>

  <div
    v-if="showManualIndicator"
    class="inline-flex items-baseline"
  >
    <ManualPriceIndicator />
    <ReuseAmountDisplay />
  </div>
  <ReuseAmountDisplay v-else />
</template>
