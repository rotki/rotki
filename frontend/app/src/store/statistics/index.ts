import type { MaybeRef } from 'vue';
import type { NetValueChartData } from '@/modules/dashboard/graph/types';
import { type AssetBalanceWithPriceAndChains, type BigNumber, type NetValue, One, type TimeFramePeriod, timeframes, TimeUnit, Zero } from '@rotki/common';
import dayjs from 'dayjs';
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';
import { useNumberScrambler } from '@/composables/utils/useNumberScrambler';
import { CURRENCY_USD, type SupportedCurrency } from '@/modules/amount-display/currencies';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { millisecondsToSeconds } from '@/modules/common/data/date';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSessionSettingsStore } from '@/store/settings/session';

function defaultNetValue(): NetValue {
  return {
    data: [],
    times: [],
  };
}

interface Overall {
  currency: SupportedCurrency;
  delta: string;
  netWorth: string;
  percentage: string;
  period: TimeFramePeriod;
  up?: boolean;
}

export const useStatisticsStore = defineStore('statistics', () => {
  const netValue = ref<NetValue>(defaultNetValue());

  const { nftsInNetValue, scrambleData, scrambleMultiplier, shouldShowAmount, valueRoundingMode } = storeToRefs(useFrontendSettingsStore());
  const { currencySymbol, floatingPrecision } = storeToRefs(useGeneralSettingsStore());
  const { nonFungibleTotalValue } = storeToRefs(useBalancesStore());
  const { timeframe } = storeToRefs(useSessionSettingsStore());
  const { getExchangeRate } = usePriceUtils();

  const { getBalances, getLiabilities } = useAggregatedBalances();

  /**
   * Calculates the sum of balances using the `value` field (already in main currency)
   */
  function calculateSum(items: AssetBalanceWithPriceAndChains[]): BigNumber {
    return items.reduce((sum, item) => sum.plus(item.value), Zero);
  }

  const calculateTotalValue = (includeNft: MaybeRef<boolean> = false): ComputedRef<BigNumber> => computed<BigNumber>(() => {
    const aggregatedBalances = getBalances();
    const totalLiabilities = getLiabilities();
    const nftTotal = get(includeNft) ? get(nonFungibleTotalValue) : Zero;
    const mainCurrency = get(currencySymbol);
    const rate = getExchangeRate(mainCurrency, One);
    const assetValue = calculateSum(aggregatedBalances);
    const liabilityValue = calculateSum(totalLiabilities);
    // NFT value is still in USD, so we convert it
    return assetValue.plus(nftTotal.multipliedBy(rate)).minus(liabilityValue);
  });

  const totalNetWorth = calculateTotalValue(nftsInNetValue);

  const scrambleEnabled = logicOr(scrambleData, logicNot(shouldShowAmount));

  const balanceDelta = computed<BigNumber>(() => {
    const selectedTimeframe = get(timeframe);
    const allTimeframes = timeframes((unit, amount) => dayjs().subtract(amount, unit).startOf(TimeUnit.DAY).unix());
    const startingDate = allTimeframes[selectedTimeframe].startingDate();
    const data = getNetValue(startingDate).data;
    let start = data[0];
    if (start?.isZero()) {
      for (let i = 1; i < data.length; i++) {
        if (data[i].gt(0)) {
          start = data[i];
          break;
        }
      }
    }
    return get(totalNetWorth).minus(start ?? Zero);
  });

  const scrambledNetWorth = useNumberScrambler({
    enabled: scrambleEnabled,
    multiplier: scrambleMultiplier,
    value: totalNetWorth,
  });

  const scrambledBalanceDelta = useNumberScrambler({
    enabled: scrambleEnabled,
    multiplier: scrambleMultiplier,
    value: balanceDelta,
  });

  const overall = computed<Overall>(() => {
    const currency = get(currencySymbol);
    const selectedTimeframe = get(timeframe);
    const delta = get(balanceDelta);

    const percentage = ((): string => {
      const starting = get(totalNetWorth).minus(delta);
      const pct = delta.div(starting).multipliedBy(100);
      return pct.isFinite() ? pct.toFormat(2) : '-';
    })();

    let up: boolean | undefined;
    if (delta.isGreaterThan(0))
      up = true;
    else if (delta.isLessThan(0))
      up = false;

    const floatPrecision = get(floatingPrecision);
    const rounding = get(valueRoundingMode);

    return {
      currency,
      delta: get(scrambledBalanceDelta).toFormat(floatPrecision, rounding),
      netWorth: get(scrambledNetWorth).toFormat(floatPrecision, rounding),
      percentage,
      period: selectedTimeframe,
      up,
    };
  });

  const totalNetWorthUsd = calculateTotalValue(true);

  function getNetValue(startingDate: number): NetValueChartData {
    const currency = get(currencySymbol);
    const rate = getExchangeRate(currency, One);

    const convert = (value: BigNumber): BigNumber => (currency === CURRENCY_USD ? value : value.multipliedBy(rate));

    const { data, times } = get(netValue);

    const now = millisecondsToSeconds(Date.now());
    const netWorth = get(totalNetWorth);

    if (times.length === 0 && data.length === 0) {
      const oneDayTimestamp = 24 * 60 * 60;

      return {
        data: [Zero, netWorth],
        snapshotCount: 0,
        times: [now - oneDayTimestamp, now],
      };
    }

    const nv: NetValue = { data: [], times: [] };

    for (const [i, time] of times.entries()) {
      if (time < startingDate)
        continue;

      nv.times.push(time);
      nv.data.push(convert(data[i]));
    }

    return {
      data: [...nv.data, netWorth],
      snapshotCount: nv.data.length,
      times: [...nv.times, now],
    };
  }

  function useNetValue(startingDate: number): ComputedRef<NetValueChartData> {
    return computed<NetValueChartData>(() => getNetValue(startingDate));
  }

  return {
    getNetValue,
    netValue,
    useNetValue,
    overall,
    totalNetWorth,
    totalNetWorthUsd,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useStatisticsStore, import.meta.hot));
