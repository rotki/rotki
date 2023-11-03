<script setup lang="ts">
import { TimeUnit } from '@rotki/common/lib/settings';
import {
  TimeFramePeriod,
  TimeFramePersist,
  type TimeFrameSetting,
  timeframes
} from '@rotki/common/lib/settings/graphs';
import dayjs from 'dayjs';
import { Section } from '@/types/status';

const { t } = useI18n();
const { currencySymbol, floatingPrecision } = storeToRefs(
  useGeneralSettingsStore()
);
const sessionStore = useSessionSettingsStore();
const { update } = sessionStore;
const { timeframe } = storeToRefs(sessionStore);
const { premium } = storeToRefs(usePremiumStore());
const statistics = useStatisticsStore();
const { fetchNetValue, getNetValue } = statistics;
const { totalNetWorth } = storeToRefs(statistics);
const frontendStore = useFrontendSettingsStore();
const { visibleTimeframes } = storeToRefs(frontendStore);

const { isLoading: isSectionLoading } = useStatusStore();

const isLoading = logicOr(
  isSectionLoading(Section.BLOCKCHAIN_ETH),
  isSectionLoading(Section.BLOCKCHAIN_BTC)
);

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

const adjustedTotalNetWorthFontSize = computed(() => {
  const digits = get(totalNetWorth)
    .toFormat(get(floatingPrecision))
    .replace(/\./g, '')
    .replace(/,/g, '').length;

  // this number adjusted visually
  // when we use max floating precision (8), it won't overlap
  return Math.min(1, 12 / digits);
});

const allTimeframes = computed(() =>
  timeframes((unit, amount) =>
    dayjs().subtract(amount, unit).startOf(TimeUnit.DAY).unix()
  )
);

const balanceDelta = computed(() =>
  get(totalNetWorth).minus(get(startingValue))
);

const timeframeData = computed(() => {
  const all = get(allTimeframes);
  const selection = get(timeframe);
  const startingDate = all[selection].startingDate();
  return get(getNetValue(startingDate));
});

const percentage = computed(() => {
  const bigNumber = get(balanceDelta).div(get(startingValue)).multipliedBy(100);

  return bigNumber.isFinite() ? bigNumber.toFormat(2) : '-';
});

const indicator = computed(() => {
  const delta = get(balanceDelta);
  if (delta.isNegative()) {
    return 'arrow-down-line';
  }
  if (delta.isZero()) {
    return 'git-commit-line';
  }
  return 'arrow-up-line';
});

const balanceClass = computed(() => {
  const delta = get(balanceDelta);
  if (delta.isNegative()) {
    return 'bg-rui-error-lighter';
  }
  if (delta.isZero()) {
    return 'bg-rui-grey-500';
  }
  return 'bg-rui-success';
});

const setTimeframe = async (value: TimeFrameSetting) => {
  assert(value !== TimeFramePersist.REMEMBER);
  sessionStore.update({ timeframe: value });
  await frontendStore.updateSetting({ lastKnownTimeframe: value });
};

const { logged } = storeToRefs(useSessionAuthStore());

watch(premium, async () => {
  if (get(logged)) {
    await fetchNetValue();
  }
});

onMounted(() => {
  const isPremium = get(premium);
  const selectedTimeframe = get(timeframe);
  if (!isPremium && !isPeriodAllowed(selectedTimeframe)) {
    update({ timeframe: TimeFramePeriod.TWO_WEEKS });
  }
});

const { showGraphRangeSelector } = storeToRefs(useFrontendSettingsStore());
const chartSectionHeight = computed<string>(() => {
  const height = 208 + (get(showGraphRangeSelector) ? 60 : 0);
  return `${height}px`;
});

const { dark } = useTheme();
</script>

<template>
  <RuiCard class="overall-balances">
    <div class="grid md:grid-cols-2 lg:grid-cols-12 p-2 gap-4 overflow-hidden">
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
        <div class="flex justify-center items-baseline">
          <span v-if="isLoading" class="rounded-full overflow-hidden">
            <VSkeletonLoader width="170" height="32" type="image" />
          </span>
          <span
            v-else
            :class="[balanceClass, !dark ? 'white--text' : 'black--text']"
            class="pa-1 px-3 flex flex-row rounded-full min-h-[2rem] min-w-[170px]"
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
          :value="timeframe"
          :visible-timeframes="visibleTimeframes"
          @input="setTimeframe($event)"
        />
      </div>
      <div
        class="lg:col-span-7 flex justify-center items-center overall-balances__net-worth-chart"
      >
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
          <RuiProgress circular variant="indeterminate" color="primary" />
          <div class="pt-5 text-caption">
            {{ t('overall_balances.loading') }}
          </div>
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
