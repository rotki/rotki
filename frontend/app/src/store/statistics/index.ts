import type { MaybeRef } from 'vue';
import { type AssetBalanceWithPriceAndChains, type BigNumber, type NetValue, One, type TimeFramePeriod, timeframes, TimeUnit, Zero } from '@rotki/common';
import dayjs from 'dayjs';
import { useStatisticsApi } from '@/composables/api/statistics/statistics-api';
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';
import { usePremium } from '@/composables/premium';
import { useNumberScrambler } from '@/composables/utils/useNumberScrambler';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useNotificationsStore } from '@/store/notifications';
import { useSessionAuthStore } from '@/store/session/auth';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSessionSettingsStore } from '@/store/settings/session';
import { CURRENCY_USD, type SupportedCurrency } from '@/types/currencies';
import { millisecondsToSeconds } from '@/utils/date';

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

  const { t } = useI18n({ useScope: 'global' });

  const { nftsInNetValue, scrambleData, scrambleMultiplier: scrambleMultiplierRef, shouldShowAmount, valueRoundingMode } = storeToRefs(useFrontendSettingsStore());
  const notificationsStore = useNotificationsStore();
  const { notify } = notificationsStore;
  const { currencySymbol, floatingPrecision } = storeToRefs(useGeneralSettingsStore());
  const { nonFungibleTotalValue } = storeToRefs(useBalancesStore());
  const { timeframe } = storeToRefs(useSessionSettingsStore());
  const { useExchangeRate } = usePriceUtils();

  const scrambleMultiplier = ref<number>(get(scrambleMultiplierRef) ?? 1);

  watchEffect(() => {
    const newValue = get(scrambleMultiplierRef);
    if (newValue !== undefined)
      set(scrambleMultiplier, newValue);
  });

  const premium = usePremium();

  const api = useStatisticsApi();
  const { balances, liabilities } = useAggregatedBalances();
  const { logged } = storeToRefs(useSessionAuthStore());

  /**
   * Calculates the sum of balances using the `value` field (already in main currency)
   */
  function calculateSum(items: AssetBalanceWithPriceAndChains[]): BigNumber {
    return items.reduce((sum, item) => sum.plus(item.value), Zero);
  }

  const calculateTotalValue = (includeNft: MaybeRef<boolean> = false): ComputedRef<BigNumber> => computed<BigNumber>(() => {
    const aggregatedBalances = get(balances());
    const totalLiabilities = get(liabilities());
    const nftTotal = get(includeNft) ? get(nonFungibleTotalValue) : Zero;
    const mainCurrency = get(currencySymbol);
    const rate = get(useExchangeRate(mainCurrency)) ?? One;
    const assetValue = calculateSum(aggregatedBalances);
    const liabilityValue = calculateSum(totalLiabilities);
    // NFT value is still in USD, so we convert it
    return assetValue.plus(nftTotal.multipliedBy(rate)).minus(liabilityValue);
  });

  const totalNetWorth = calculateTotalValue(nftsInNetValue);

  const overall = computed<Overall>(() => {
    const currency = get(currencySymbol);
    const selectedTimeframe = get(timeframe);
    const allTimeframes = timeframes((unit, amount) => dayjs().subtract(amount, unit).startOf(TimeUnit.DAY).unix());
    const startingDate = allTimeframes[selectedTimeframe].startingDate();

    const startingValue: () => BigNumber = () => {
      const data = get(getNetValue(startingDate)).data;
      let start = data[0];
      if (start.isZero()) {
        for (let i = 1; i < data.length; i++) {
          if (data[i].gt(0)) {
            start = data[i];
            break;
          }
        }
      }
      return start;
    };

    const starting = startingValue();
    const totalNW = get(totalNetWorth);
    const balanceDelta = totalNW.minus(starting);

    // Apply scrambling to net worth for tray display
    const scrambledNetWorth = get(useNumberScrambler({
      enabled: logicOr(scrambleData, logicNot(shouldShowAmount)),
      multiplier: scrambleMultiplier,
      value: computed(() => totalNW),
    }));

    const scrambledBalanceDelta = get(useNumberScrambler({
      enabled: logicOr(scrambleData, logicNot(shouldShowAmount)),
      multiplier: scrambleMultiplier,
      value: computed(() => balanceDelta),
    }));

    const percentage = balanceDelta.div(starting).multipliedBy(100);

    let up: boolean | undefined;
    if (balanceDelta.isGreaterThan(0))
      up = true;
    else if (balanceDelta.isLessThan(0))
      up = false;

    const floatPrecision = get(floatingPrecision);
    const rounding = get(valueRoundingMode);

    const delta = scrambledBalanceDelta.toFormat(floatPrecision, rounding);
    const netWorth = scrambledNetWorth.toFormat(floatPrecision, rounding);

    return {
      currency,
      delta,
      netWorth,
      percentage: percentage.isFinite() ? percentage.toFormat(2) : '-',
      period: selectedTimeframe,
      up,
    };
  });

  const totalNetWorthUsd = calculateTotalValue(true);

  function getNetValue(startingDate: number): ComputedRef<NetValue> {
    return computed<NetValue>(() => {
      const currency = get(currencySymbol);
      const rate = get(useExchangeRate(currency)) ?? One;

      const convert = (value: BigNumber): BigNumber => (currency === CURRENCY_USD ? value : value.multipliedBy(rate));

      const { data, times } = get(netValue);

      const now = millisecondsToSeconds(Date.now());
      const netWorth = get(totalNetWorth);

      if (times.length === 0 && data.length === 0) {
        const oneDayTimestamp = 24 * 60 * 60;

        return {
          data: [Zero, netWorth],
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
        times: [...nv.times, now],
      };
    });
  }

  const fetchNetValue = async (): Promise<void> => {
    try {
      set(netValue, await api.queryNetValueData(get(nftsInNetValue)));
    }
    catch (error: any) {
      notify({
        display: false,
        message: t('actions.statistics.net_value.error.message', {
          message: error.message,
        }),
        title: t('actions.statistics.net_value.error.title'),
      });
    }
  };

  watch(premium, async () => {
    if (get(logged))
      await fetchNetValue();
  });

  return {
    fetchNetValue,
    getNetValue,
    netValue,
    overall,
    totalNetWorth,
    totalNetWorthUsd,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useStatisticsStore, import.meta.hot));
