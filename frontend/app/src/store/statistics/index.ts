import { type BigNumber, type NetValue, type TimeFramePeriod, TimeUnit, timeframes } from '@rotki/common';
import dayjs from 'dayjs';
import { CURRENCY_USD, type SupportedCurrency } from '@/types/currencies';

function defaultNetValue(): NetValue {
  return {
    times: [],
    data: [],
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

  const { t } = useI18n();

  const settingsStore = useFrontendSettingsStore();
  const { nftsInNetValue } = storeToRefs(settingsStore);
  const { notify } = useNotificationsStore();
  const { currencySymbol, floatingPrecision } = storeToRefs(useGeneralSettingsStore());
  const { nonFungibleTotalValue } = storeToRefs(useNonFungibleBalancesStore());
  const { timeframe } = storeToRefs(useSessionSettingsStore());
  const { exchangeRate } = useBalancePricesStore();

  const api = useStatisticsApi();
  const { lpTotal } = useLiquidityPosition();
  const { balances, liabilities } = useAggregatedBalances();

  const calculateTotalValue = (includeNft = false): ComputedRef<BigNumber> => computed<BigNumber>(() => {
    const aggregatedBalances = get(balances());
    const totalLiabilities = get(liabilities());
    const nftTotal = includeNft ? get(nonFungibleTotalValue) : 0;

    const lpTotalBalance = get(lpTotal(false));

    const assetValue = aggregatedBalances.reduce((sum, value) => sum.plus(value.value), Zero);
    const liabilityValue = totalLiabilities.reduce((sum, value) => sum.plus(value.value), Zero);

    return assetValue.plus(nftTotal).plus(lpTotalBalance).minus(liabilityValue);
  });

  const totalNetWorth = computed<BigNumber>(() => {
    const mainCurrency = get(currencySymbol);
    const rate = get(exchangeRate(mainCurrency)) ?? One;
    return get(calculateTotalValue(get(nftsInNetValue))).multipliedBy(rate);
  });

  const overall = computed<Overall>(() => {
    const currency = get(currencySymbol);
    const rate = get(exchangeRate(currency)) ?? One;
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
    const percentage = balanceDelta.div(starting).multipliedBy(100);

    let up: boolean | undefined;
    if (balanceDelta.isGreaterThan(0))
      up = true;
    else if (balanceDelta.isLessThan(0))
      up = false;

    const floatPrecision = get(floatingPrecision);
    const delta = balanceDelta.multipliedBy(rate).toFormat(floatPrecision);

    return {
      period: selectedTimeframe,
      currency,
      netWorth: totalNW.toFormat(floatPrecision),
      delta,
      percentage: percentage.isFinite() ? percentage.toFormat(2) : '-',
      up,
    };
  });

  const totalNetWorthUsd = calculateTotalValue(true);

  function getNetValue(startingDate: number): ComputedRef<NetValue> {
    return computed<NetValue>(() => {
      const currency = get(currencySymbol);
      const rate = get(exchangeRate(currency)) ?? One;

      const convert = (value: BigNumber): BigNumber => (currency === CURRENCY_USD ? value : value.multipliedBy(rate));

      const { times, data } = get(netValue);

      const now = Math.floor(Date.now() / 1000);
      const netWorth = get(totalNetWorth);

      if (times.length === 0 && data.length === 0) {
        const oneDayTimestamp = 24 * 60 * 60;

        return {
          times: [now - oneDayTimestamp, now],
          data: [Zero, netWorth],
        };
      }

      const nv: NetValue = { times: [], data: [] };

      for (const [i, time] of times.entries()) {
        if (time < startingDate)
          continue;

        nv.times.push(time);
        nv.data.push(convert(data[i]));
      }

      return {
        times: [...nv.times, now],
        data: [...nv.data, netWorth],
      };
    });
  }

  const fetchNetValue = async (): Promise<void> => {
    try {
      set(netValue, await api.queryNetValueData(get(nftsInNetValue)));
    }
    catch (error: any) {
      notify({
        title: t('actions.statistics.net_value.error.title'),
        message: t('actions.statistics.net_value.error.message', {
          message: error.message,
        }),
        display: false,
      });
    }
  };

  return {
    netValue,
    totalNetWorth,
    totalNetWorthUsd,
    overall,
    fetchNetValue,
    getNetValue,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useStatisticsStore, import.meta.hot));
