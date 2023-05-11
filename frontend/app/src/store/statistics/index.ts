import { type BigNumber } from '@rotki/common';
import { TimeUnit } from '@rotki/common/lib/settings';
import { timeframes } from '@rotki/common/lib/settings/graphs';
import { type NetValue } from '@rotki/common/lib/statistics';
import dayjs from 'dayjs';
import { type ComputedRef } from 'vue';
import { CURRENCY_USD } from '@/types/currencies';

const defaultNetValue = (): NetValue => ({
  times: [],
  data: []
});

export const useStatisticsStore = defineStore('statistics', () => {
  const netValue = ref<NetValue>(defaultNetValue());

  const settingsStore = useFrontendSettingsStore();
  const { nftsInNetValue } = storeToRefs(settingsStore);
  const { notify } = useNotificationsStore();
  const { currencySymbol, floatingPrecision } = storeToRefs(
    useGeneralSettingsStore()
  );
  const { balances, liabilities } = useAggregatedBalances();
  const { nonFungibleTotalValue } = storeToRefs(useNonFungibleBalancesStore());
  const { timeframe } = storeToRefs(useSessionSettingsStore());
  const { exchangeRate } = useBalancePricesStore();

  const { lpTotal } = useLiquidityPosition();

  const { t } = useI18n();

  const calculateTotalValue = (includeNft = false): ComputedRef<BigNumber> =>
    computed(() => {
      const aggregatedBalances = get(balances());
      const totalLiabilities = get(liabilities());
      const nftTotal = includeNft ? get(nonFungibleTotalValue) : 0;

      const lpTotalBalance = get(lpTotal(includeNft));

      const assetValue = aggregatedBalances.reduce(
        (sum, value) => sum.plus(value.usdValue),
        Zero
      );

      const liabilityValue = totalLiabilities.reduce(
        (sum, value) => sum.plus(value.usdValue),
        Zero
      );

      return assetValue
        .plus(nftTotal)
        .plus(lpTotalBalance)
        .minus(liabilityValue);
    });

  const totalNetWorth = computed(() => {
    const mainCurrency = get(currencySymbol);
    const rate = get(exchangeRate(mainCurrency)) ?? One;
    return get(calculateTotalValue(get(nftsInNetValue))).multipliedBy(rate);
  });

  const totalNetWorthUsd = computed(() => get(calculateTotalValue(true)));

  const overall = computed(() => {
    const currency = get(currencySymbol);
    const rate = get(exchangeRate(currency)) ?? One;
    const selectedTimeframe = get(timeframe);
    const allTimeframes = timeframes((unit, amount) =>
      dayjs().subtract(amount, unit).startOf(TimeUnit.DAY).unix()
    );
    const startingDate = allTimeframes[selectedTimeframe].startingDate();
    const startingValue: () => BigNumber = () => {
      const data = get(getNetValue(startingDate)).data;
      let start = data[0];
      if (start === 0) {
        for (let i = 1; i < data.length; i++) {
          if (data[i] > 0) {
            start = data[i];
            break;
          }
        }
      }
      return bigNumberify(start);
    };

    const starting = startingValue();
    const totalNW = get(totalNetWorth);
    const balanceDelta = totalNW.minus(starting);
    const percentage = balanceDelta.div(starting).multipliedBy(100);

    let up: boolean | undefined = undefined;
    if (balanceDelta.isGreaterThan(0)) {
      up = true;
    } else if (balanceDelta.isLessThan(0)) {
      up = false;
    }

    const floatPrecision = get(floatingPrecision);
    const delta = balanceDelta.multipliedBy(rate).toFormat(floatPrecision);

    return {
      period: selectedTimeframe,
      currency,
      netWorth: totalNW.toFormat(floatPrecision),
      delta,
      percentage: percentage.isFinite() ? percentage.toFormat(2) : '-',
      up
    };
  });

  const api = useStatisticsApi();
  const fetchNetValue = async (): Promise<void> => {
    try {
      set(netValue, await api.queryNetValueData(get(nftsInNetValue)));
    } catch (e: any) {
      notify({
        title: t('actions.statistics.net_value.error.title').toString(),
        message: t('actions.statistics.net_value.error.message', {
          message: e.message
        }).toString(),
        display: false
      });
    }
  };

  const getNetValue = (startingDate: number): ComputedRef<NetValue> =>
    computed(() => {
      const currency = get(currencySymbol);
      const rate = get(exchangeRate(currency)) ?? One;

      const convert = (value: string | number | BigNumber): number => {
        const bigNumber =
          typeof value === 'string' || typeof value === 'number'
            ? bigNumberify(value)
            : value;
        const convertedValue =
          currency === CURRENCY_USD ? bigNumber : bigNumber.multipliedBy(rate);
        return convertedValue.toNumber();
      };

      const { times, data } = get(netValue);
      const nv: NetValue = { times: [], data: [] };
      if (times.length === 0 && data.length === 0) {
        return nv;
      }

      for (const [i, time] of times.entries()) {
        if (time < startingDate) {
          continue;
        }
        nv.times.push(time);
        nv.data.push(convert(data[i]));
      }

      const now = Math.floor(Date.now() / 1000);
      const netWorth = get(totalNetWorth).toNumber();
      return {
        times: [...nv.times, now],
        data: [...nv.data, netWorth]
      };
    });

  return {
    netValue,
    totalNetWorth,
    totalNetWorthUsd,
    overall,
    fetchNetValue,
    getNetValue
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useStatisticsStore, import.meta.hot));
}
