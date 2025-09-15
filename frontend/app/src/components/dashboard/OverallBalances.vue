<script setup lang="ts">
import { assert, TimeFramePeriod, TimeFramePersist, timeframes, type TimeFrameSetting, TimeUnit } from '@rotki/common';
import dayjs from 'dayjs';
import SnapshotActionButton from '@/components/dashboard/SnapshotActionButton.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import TimeframeSelector from '@/components/helper/TimeframeSelector.vue';
import { usePremium } from '@/composables/premium';
import NetWorthChart from '@/modules/dashboard/graph/NetWorthChart.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSessionSettingsStore } from '@/store/settings/session';
import { useStatisticsStore } from '@/store/statistics';
import { useStatusStore } from '@/store/status';
import { Section } from '@/types/status';
import { isPeriodAllowed } from '@/utils/settings';

const { t } = useI18n({ useScope: 'global' });
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const sessionStore = useSessionSettingsStore();
const { update } = sessionStore;
const { timeframe } = storeToRefs(sessionStore);
const premium = usePremium();
const statistics = useStatisticsStore();
const { getNetValue } = statistics;
const { totalNetWorth } = storeToRefs(statistics);
const frontendStore = useFrontendSettingsStore();
const { visibleTimeframes } = storeToRefs(frontendStore);

const { isLoading: isSectionLoading, shouldShowLoadingScreen } = useStatusStore();

const isLoading = logicOr(
  shouldShowLoadingScreen(Section.BLOCKCHAIN),
  isSectionLoading(Section.BLOCKCHAIN),
);

const allTimeframes = computed(() =>
  timeframes((unit, amount) => dayjs().subtract(amount, unit).startOf(TimeUnit.DAY).unix()),
);

const timeframeData = computed(() => {
  const all = get(allTimeframes);
  const selection = get(timeframe);
  const startingDate = all[selection].startingDate();
  return get(getNetValue(startingDate));
});

const startingValue = computed(() => {
  const data = get(timeframeData).data;
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
});

const balanceDelta = computed(() => get(totalNetWorth).minus(get(startingValue)));

const percentage = computed(() => {
  const bigNumber = get(balanceDelta).div(get(startingValue)).multipliedBy(100);
  return bigNumber.isFinite() ? bigNumber.toFormat(2) : '-';
});

const indicator = computed(() => {
  const delta = get(balanceDelta);
  if (delta.isNegative())
    return 'lu-arrow-down';

  if (delta.isZero())
    return 'lu-git-commit-horizontal';

  return 'lu-arrow-up';
});

const balanceClass = computed(() => {
  const delta = get(balanceDelta);
  if (delta.isNegative())
    return '!text-rui-error-lighter';

  if (delta.isZero())
    return '!text-rui-grey-500';

  return '!text-rui-success';
});

async function setTimeframe(value: TimeFrameSetting) {
  assert(value !== TimeFramePersist.REMEMBER);
  sessionStore.update({ timeframe: value });
  await frontendStore.updateSetting({ lastKnownTimeframe: value });
}

onMounted(() => {
  const isPremium = get(premium);
  const selectedTimeframe = get(timeframe);
  if (!isPremium && !isPeriodAllowed(selectedTimeframe))
    update({ timeframe: TimeFramePeriod.TWO_WEEKS });
});
</script>

<template>
  <RuiCard
    class="overall-balances"
    content-class="grid grid-cols-1 lg:grid-cols-12 p-2 gap-4 overflow-hidden"
  >
    <div
      class="lg:col-span-4 flex flex-col justify-start lg:p-4"
    >
      <div class="text-rui-text-secondary">
        {{ t('overall_balances.total_balance') }}
      </div>
      <div
        class="font-medium"
        data-cy="overall-balances__net-worth"
      >
        <AmountDisplay
          xl
          no-truncate
          show-currency="symbol"
          :fiat-currency="currencySymbol"
          :value="totalNetWorth"
        />
      </div>

      <RuiSkeletonLoader
        v-if="isLoading"
        class="w-48 h-8"
      />
      <div
        v-else
        :class="balanceClass"
        class="flex flex-row items-center gap-2 rounded-full font-medium"
      >
        <RuiIcon
          :name="indicator"
          size="16"
        />
        <PercentageDisplay
          v-if="!isLoading"
          class="pr-4"
          :value="percentage"
        />
        <span>
          (
          <AmountDisplay
            v-if="!isLoading"
            show-currency="symbol"
            :fiat-currency="currencySymbol"
            :value="balanceDelta"
          />
          )
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
        <NetWorthChart :chart-data="timeframeData" />
        <div
          v-if="isLoading"
          class="absolute top-0 h-full w-full flex flex-col gap-3 items-center justify-center text-caption text-rui-text-secondary bg-white/[0.8] dark:bg-[#1e1e1e]/[0.9] z-[6]"
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
