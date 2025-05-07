<script setup lang="ts">
import NetWorthChart from '@/components/dashboard/NetWorthChart.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import TimeframeSelector from '@/components/helper/TimeframeSelector.vue';
import { usePremium } from '@/composables/premium';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSessionSettingsStore } from '@/store/settings/session';
import { useStatisticsStore } from '@/store/statistics';
import { useStatusStore } from '@/store/status';
import { Section } from '@/types/status';
import { isPeriodAllowed } from '@/utils/settings';
import { assert, TimeFramePeriod, TimeFramePersist, timeframes, type TimeFrameSetting, TimeUnit } from '@rotki/common';
import dayjs from 'dayjs';

const { t } = useI18n({ useScope: 'global' });
const { currencySymbol, floatingPrecision } = storeToRefs(useGeneralSettingsStore());
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

const adjustedTotalNetWorthFontSize = computed(() => {
  const digits = get(totalNetWorth).toFormat(get(floatingPrecision)).replace(/\./g, '').replace(/,/g, '').length;

  // this number adjusted visually
  // when we use max floating precision (8), it won't overlap
  return Math.min(1, 12 / digits);
});

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
    return 'bg-rui-error-lighter';

  if (delta.isZero())
    return 'bg-rui-grey-500';

  return 'bg-rui-success';
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

const { showGraphRangeSelector } = storeToRefs(useFrontendSettingsStore());
const chartSectionHeight = computed<string>(() => {
  const height = 208 + (get(showGraphRangeSelector) ? 60 : 0);
  return `${height}px`;
});
</script>

<template>
  <RuiCard
    class="overall-balances"
    content-class="grid md:grid-cols-2 lg:grid-cols-12 p-2 gap-4 overflow-hidden"
  >
    <div class="lg:col-span-5 flex flex-col items-center justify-center">
      <div
        class="text-center font-medium mb-2 flex"
        data-cy="overall-balances__net-worth"
        :style="`font-size: ${adjustedTotalNetWorthFontSize}em`"
      >
        <AmountDisplay
          class="ps-4"
          xl
          show-currency="symbol"
          :fiat-currency="currencySymbol"
          :value="totalNetWorth"
        />
      </div>
      <div class="flex justify-center items-center">
        <RuiSkeletonLoader
          v-if="isLoading"
          class="w-[10.625rem] h-8"
          rounded="full"
        />
        <span
          v-else
          :class="balanceClass"
          class="py-1 px-3 flex flex-row rounded-full min-h-[2rem] min-w-[170px] text-white dark:text-rui-light-text"
        >
          <span>
            <RuiIcon :name="indicator" />
          </span>
          <AmountDisplay
            v-if="!isLoading"
            class="px-3"
            show-currency="symbol"
            :fiat-currency="currencySymbol"
            :value="balanceDelta"
          />
          <PercentageDisplay
            v-if="!isLoading"
            class="pr-2 opacity-80"
            :value="percentage"
          />
        </span>
      </div>
      <TimeframeSelector
        class="pt-6"
        :model-value="timeframe"
        :visible-timeframes="visibleTimeframes"
        @update:model-value="setTimeframe($event)"
      />
    </div>
    <div class="lg:col-span-7 flex justify-center items-center overall-balances__net-worth-chart">
      <NetWorthChart
        v-if="!isLoading"
        :chart-data="timeframeData"
        :timeframe="timeframe"
        :timeframes="allTimeframes"
      />
      <div
        v-else
        class="overall-balances__net-worth-chart__loader flex h-full flex flex-col text-center justify-center items-center"
      >
        <RuiProgress
          circular
          variant="indeterminate"
          color="primary"
        />
        <div class="pt-5 text-caption">
          {{ t('overall_balances.loading') }}
        </div>
      </div>
    </div>
  </RuiCard>
</template>

<style scoped lang="scss">
.overall-balances {
  &__net-worth-chart {
    &__loader {
      min-height: v-bind(chartSectionHeight);
    }
  }
}
</style>
