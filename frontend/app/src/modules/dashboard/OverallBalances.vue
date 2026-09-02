<script setup lang="ts">
import type { NetValueChartData } from '@/modules/dashboard/graph/types';
import { assert, type BigNumber, TimeFramePeriod, TimeFramePersist, timeframes, type TimeFrameSetting, TimeUnit } from '@rotki/common';
import dayjs from 'dayjs';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { useBalancesLoading } from '@/modules/balances/use-balance-loading';
import { computeNetValueDelta, type NetValueZoomRange } from '@/modules/dashboard/graph/net-value-stats';
import NetWorthChart from '@/modules/dashboard/graph/NetWorthChart.vue';
import SnapshotActionButton from '@/modules/dashboard/SnapshotActionButton.vue';
import { useNetWorthLoading } from '@/modules/dashboard/use-net-worth-loading';
import { usePremium } from '@/modules/premium/use-premium';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { isPeriodAllowed } from '@/modules/settings/settings-utils';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import PercentageDisplay from '@/modules/shell/components/display/PercentageDisplay.vue';
import TimeframeSelector from '@/modules/statistics/TimeframeSelector.vue';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

const { t } = useI18n({ useScope: 'global' });

const netWorthChart = useTemplateRef<InstanceType<typeof NetWorthChart>>('netWorthChart');

const settingsRepo = useSettingsRepo();
const statisticsStore = useStatisticsStore();
const timeframe = useSetting('timeframe');
const { totalNetWorth } = storeToRefs(statisticsStore);
const visibleTimeframes = useSetting('visibleTimeframes');
const { getNetValue } = statisticsStore;

const premium = usePremium();
const { updateFrontendSetting } = useSettingsOperations();
const { loadingBlockchainBalances: isLoading } = useBalancesLoading();

const loadingNetWorth = useNetWorthLoading();

/**
 * Whether the delta and the chart have a total worth drawing.
 *
 * @remarks
 * Wider than the header's own latch, which waits for the first load only. A delta computed from a
 * half-loaded total is a number that is wrong while it moves, so these two wait for every load. The
 * latch is what carries them through the first frames, before any balance activity is submitted.
 */
const isBusy = computed<boolean>(() => get(loadingNetWorth) || get(isLoading));

const zoomRange = ref<NetValueZoomRange>();

const allTimeframes = computed(() =>
  timeframes((unit, amount) => dayjs().subtract(amount, unit).startOf(TimeUnit.DAY).unix()),
);

const timeframeData = computed<NetValueChartData>(() => {
  const all = get(allTimeframes);
  const selection = get(timeframe);
  const startingDate = all[selection].startingDate();
  return getNetValue(startingDate);
});

const stats = computed(() => {
  const { data, times } = get(timeframeData);
  return computeNetValueDelta(data, times, get(totalNetWorth), get(zoomRange));
});

const startingValue = computed<BigNumber>(() => get(stats).startingValue);
const balanceDelta = computed<BigNumber>(() => get(stats).balanceDelta);

const percentage = computed<string>(() => {
  const bigNumber = get(balanceDelta).div(get(startingValue)).multipliedBy(100);
  return bigNumber.isFinite() ? bigNumber.toFormat(2) : '-';
});

const indicator = computed<string>(() => {
  const delta = get(balanceDelta);
  if (delta.isNegative())
    return 'lu-arrow-down';

  if (delta.isZero())
    return 'lu-git-commit-horizontal';

  return 'lu-arrow-up';
});

const balanceClass = computed<string>(() => {
  const delta = get(balanceDelta);
  if (delta.isNegative())
    return '!text-rui-error-lighter';

  if (delta.isZero())
    return '!text-rui-grey-500';

  return '!text-rui-success';
});

async function setTimeframe(value: TimeFrameSetting): Promise<void> {
  assert(value !== TimeFramePersist.REMEMBER);
  settingsRepo.updateSession({ timeframe: value });
  get(netWorthChart)?.resetZoom();
  await updateFrontendSetting({ lastKnownTimeframe: value });
}

/**
 * Drops the zoom when the timeframe changes, so the header goes back to full-range numbers after
 * the user switches buttons. Watching the timeframe rather than the data leaves an active zoom
 * alone across routine balance refreshes.
 */
function clearZoomForNewTimeframe(): void {
  set(zoomRange, undefined);
}

watch(timeframe, clearZoomForNewTimeframe);

onMounted(() => {
  if (!get(premium) && !isPeriodAllowed(get(timeframe)))
    settingsRepo.updateSession({ timeframe: TimeFramePeriod.TWO_WEEKS });
});
</script>

<template>
  <RuiCard
    class="overall-balances"
    :class-names="{ content: 'grid grid-cols-1 lg:grid-cols-12 p-2 gap-4 overflow-hidden' }"
  >
    <div
      class="lg:col-span-4 flex flex-col justify-start lg:p-4"
    >
      <div class="text-rui-text-secondary">
        {{ t('overall_balances.total_balance') }}
      </div>
      <div
        class="font-medium"
        data-testid="overall-balances-net-worth"
      >
        <RuiSkeletonLoader
          v-if="loadingNetWorth"
          class="my-[0.5rem] w-56 h-[2rem] sm:my-[0.75rem] sm:w-72 sm:h-[2.5rem]"
          data-testid="overall-balances-net-worth-loading"
        />
        <FiatDisplay
          v-else
          class="text-[2rem] leading-[3rem] sm:text-[3rem] sm:leading-[4rem]"
          no-truncate
          :value="totalNetWorth"
        />
      </div>

      <RuiSkeletonLoader
        v-if="isBusy"
        class="w-48 h-8"
        data-testid="overall-balances-delta-loading"
      />
      <div
        v-else
        :class="balanceClass"
        class="flex items-center gap-2 rounded-full font-medium"
      >
        <RuiIcon
          :name="indicator"
          size="16"
        />
        <PercentageDisplay
          class="pr-4"
          :value="percentage"
        />
        <span class="whitespace-nowrap before:content-['('] after:content-[')']">
          <FiatDisplay :value="balanceDelta" />
        </span>
      </div>
    </div>
    <div class="lg:col-span-8 flex flex-col">
      <div class="flex justify-start lg:justify-end items-center md:pt-4 gap-4">
        <TimeframeSelector
          :model-value="timeframe"
          :visible-timeframes="visibleTimeframes"
          @update:model-value="setTimeframe($event)"
        />

        <SnapshotActionButton />
      </div>
      <div class="relative">
        <NetWorthChart
          ref="netWorthChart"
          v-model:zoom-range="zoomRange"
          :chart-data="timeframeData"
        />
        <div
          v-if="isBusy"
          class="absolute top-0 h-full w-full flex flex-col gap-3 items-center justify-center text-caption text-rui-text-secondary bg-white/[0.8] dark:bg-dark-elevated/[0.9] z-[6]"
        >
          <RuiProgress
            circular
            variant="indeterminate"
            color="primary"
            size="24"
            thickness="2"
          />
          {{ t('overall_balances.loading') }}
        </div>
      </div>
    </div>
  </RuiCard>
</template>
