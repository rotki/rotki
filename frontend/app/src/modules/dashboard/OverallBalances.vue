<script setup lang="ts">
import type { NetValueChartData } from '@/modules/dashboard/graph/types';
import type { SourceKind } from '@/modules/dashboard/holdings/core/holdings-types';
import { assert, type BigNumber, TimeFramePeriod, TimeFramePersist, timeframes, type TimeFrameSetting, TimeUnit } from '@rotki/common';
import dayjs from 'dayjs';
import { useBalancesLoading } from '@/modules/balances/use-balance-loading';
import { computeNetValueDelta, type NetValueZoomRange } from '@/modules/dashboard/graph/net-value-stats';
import NetWorthChart from '@/modules/dashboard/graph/NetWorthChart.vue';
import AssetsBySource from '@/modules/dashboard/holdings/components/AssetsBySource.vue';
import NetWorthHeadline from '@/modules/dashboard/NetWorthHeadline.vue';
import SnapshotActionButton from '@/modules/dashboard/SnapshotActionButton.vue';
import { useNetWorthLoading } from '@/modules/dashboard/use-net-worth-loading';
import { usePremium } from '@/modules/premium/use-premium';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { isPeriodAllowed } from '@/modules/settings/settings-utils';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import TimeframeSelector from '@/modules/statistics/TimeframeSelector.vue';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

const selectedKind = defineModel<SourceKind | undefined>('selectedKind');

const { t } = useI18n({ useScope: 'global' });

const netWorthChart = useTemplateRef<InstanceType<typeof NetWorthChart>>('netWorthChart');

const settingsRepo = useSettingsRepo();
const statisticsStore = useStatisticsStore();
const timeframe = useSetting('timeframe');
const { netValueError, totalNetWorth } = storeToRefs(statisticsStore);
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

const { fetchNetValue } = useStatisticsDataFetching();

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
    <NetWorthHeadline
      class="lg:col-span-4 lg:px-4 lg:pt-4"
      :net-worth="totalNetWorth"
      :balance-delta="balanceDelta"
      :percentage="percentage"
      :loading-net-worth="loadingNetWorth"
      :busy="isBusy"
    />
    <div class="lg:col-span-8 lg:row-span-2 flex flex-col">
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
        <div
          v-else-if="netValueError"
          class="absolute top-0 h-full w-full flex flex-col gap-3 items-center justify-center px-4 text-center bg-white/[0.8] dark:bg-dark-elevated/[0.9] z-[6]"
          data-testid="net-value-error"
        >
          <div class="text-rui-text-secondary text-caption">
            {{ t('overall_balances.net_value_error') }}
          </div>
          <div class="text-rui-text-secondary text-caption break-all">
            {{ netValueError }}
          </div>
          <RuiButton
            size="sm"
            color="primary"
            variant="outlined"
            data-testid="net-value-retry"
            @click="fetchNetValue()"
          >
            {{ t('common.actions.retry') }}
          </RuiButton>
        </div>
      </div>
    </div>
    <AssetsBySource
      v-model:selected-kind="selectedKind"
      class="lg:col-span-4 lg:col-start-1 lg:row-start-2 lg:px-4 lg:pb-4 self-start"
    />
  </RuiCard>
</template>
