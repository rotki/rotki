import type { Balance, BigNumber, LiquityPoolDetailEntry, LiquityStatisticDetails } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { LUSD_ID } from '@/modules/staking/liquity/liquity-assets';
import {
  calculatePnl,
  orOne,
  repriceStatistic,
  StatisticView,
} from '@/modules/staking/liquity/liquity-statistics';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseLiquityStatisticsOptions {
  /** The aggregated stability pool position, which profit and loss is measured against. */
  pool: MaybeRefOrGetter<LiquityPoolDetailEntry | null>;
  /** The recorded statistics to display, as the backend returned them. */
  statistic: MaybeRefOrGetter<LiquityStatisticDetails | null>;
}

interface UseLiquityStatisticsReturn {
  loading: ComputedRef<boolean>;
  modelSelection: Ref<StatisticView>;
  statisticWithAdjustedPrice: ComputedRef<LiquityStatisticDetails | null>;
  totalDepositedStabilityPoolBalance: ComputedRef<Balance | null>;
  totalPnl: ComputedRef<BigNumber | null>;
  totalWithdrawnStabilityPoolBalance: ComputedRef<Balance | null>;
}

export function useLiquityStatistics(options: UseLiquityStatisticsOptions): UseLiquityStatisticsReturn {
  const { pool, statistic } = options;

  const { getAssetPrice, useAssetPrice } = usePriceUtils();
  const { useIsActive } = useTaskCenter();

  const modelSelection = shallowRef<StatisticView>(StatisticView.HISTORICAL);
  const loading = useIsActive(ActivityKind.LIQUITY, ActivityPart.STATISTICS);

  const lusdPrice = useAssetPrice(LUSD_ID);
  const lusdPriceOrOne = computed<BigNumber>(() => orOne(get(lusdPrice)));

  const statisticWithAdjustedPrice = computed<LiquityStatisticDetails | null>(() => {
    const current = toValue(statistic);
    if (!current)
      return null;

    return repriceStatistic(current, get(modelSelection), getAssetPrice, get(lusdPriceOrOne));
  });

  const totalDepositedStabilityPoolBalance = computed<Balance | null>(() => {
    const data = get(statisticWithAdjustedPrice);
    if (!data)
      return null;

    return { amount: data.totalDepositedStabilityPool, value: data.totalDepositedStabilityPoolValue };
  });

  const totalWithdrawnStabilityPoolBalance = computed<Balance | null>(() => {
    const data = get(statisticWithAdjustedPrice);
    if (!data)
      return null;

    return { amount: data.totalWithdrawnStabilityPool, value: data.totalWithdrawnStabilityPoolValue };
  });

  const totalPnl = computed<BigNumber | null>(() => {
    const currentStatistic = toValue(statistic);
    const currentPool = toValue(pool);
    if (!currentStatistic || !currentPool)
      return null;

    return calculatePnl(currentStatistic, currentPool, getAssetPrice, get(lusdPriceOrOne));
  });

  return {
    loading,
    modelSelection,
    statisticWithAdjustedPrice,
    totalDepositedStabilityPoolBalance,
    totalPnl,
    totalWithdrawnStabilityPoolBalance,
  };
}
