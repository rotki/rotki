<script setup lang="ts">
import type { PeriodChangedEvent, SelectionChangedEvent } from '@/modules/reports/report-types';
import dayjs from 'dayjs';
import { convertToTimestamp } from '@/modules/core/common/data/date';
import { Quarter } from '@/modules/settings/types/frontend-settings';

const { year, quarter } = defineProps<{
  year: string | 'custom';
  quarter: Quarter;
}>();

const emit = defineEmits<{
  'update:period': [period: PeriodChangedEvent | null];
  'update:selection': [selection: SelectionChangedEvent];
}>();

const QUARTER_STARTS: { [quarter in Quarter]: string } = {
  [Quarter.ALL]: '01/01',
  [Quarter.Q1]: '01/01',
  [Quarter.Q2]: '01/04',
  [Quarter.Q3]: '01/07',
  [Quarter.Q4]: '01/10',
};

const QUARTER_ENDS: { [quarter in Quarter]: string } = {
  [Quarter.ALL]: '31/12',
  [Quarter.Q1]: '31/03',
  [Quarter.Q2]: '30/06',
  [Quarter.Q3]: '30/09',
  [Quarter.Q4]: '31/12',
};

const { t } = useI18n({ useScope: 'global' });

function updatePeriod(period: PeriodChangedEvent | null) {
  emit('update:period', period);
}

function updateSelection(change: SelectionChangedEvent) {
  emit('update:selection', change);
}

function startDateTime(selection: Quarter): number {
  const startDate = QUARTER_STARTS[selection];
  return convertToTimestamp(`${startDate}/${year} 00:00`);
}

function isStartAfterNow(selection: Quarter) {
  const start = startDateTime(selection);
  return start > dayjs().unix();
}

const start = computed<number>(() => startDateTime(quarter));
const isCustom = computed<boolean>(() => year === 'custom');
const isAllTime = computed<boolean>(() => year === 'all-time');
const end = computed<number>(() => {
  const endDate = QUARTER_ENDS[quarter];
  return convertToTimestamp(`${endDate}/${year} 23:59:59`);
});

const periodEventPayload = computed<PeriodChangedEvent>(() => ({
  end: get(end),
  start: get(start),
}));

onMounted(() => {
  updatePeriod(year !== 'custom' ? get(periodEventPayload) : null);
});

watch([() => year, () => quarter], () => {
  if (get(isCustom))
    updatePeriod(null);
  else if (get(isAllTime))
    updatePeriod({ end: dayjs().unix(), start: 0 });
  else
    updatePeriod(get(periodEventPayload));
});

const MIN_YEAR = 2016;

const periods = computed<string[]>(() => {
  const periods: string[] = [];
  const fullYear = new Date().getFullYear();
  for (let year = fullYear; year > fullYear - 5; year--)
    periods.push(year.toString());

  return periods;
});

const olderPeriods = computed<string[]>(() => {
  const periods: string[] = [];
  const fullYear = new Date().getFullYear();
  for (let year = fullYear - 5; year >= MIN_YEAR; year--)
    periods.push(year.toString());

  return periods;
});

const isOlderYearSelected = computed<boolean>(() => get(olderPeriods).includes(year));

function selectAllTime(): void {
  updateSelection({ quarter: Quarter.ALL, year: 'all-time' });
  updatePeriod({
    end: dayjs().unix(),
    start: 0,
  });
}

const subPeriods = [
  {
    id: Quarter.ALL,
    name: t('generate.sub_period.all'),
  },
  {
    id: Quarter.Q1,
    name: 'Q1',
  },
  {
    id: Quarter.Q2,
    name: 'Q2',
  },
  {
    id: Quarter.Q3,
    name: 'Q3',
  },
  {
    id: Quarter.Q4,
    name: 'Q4',
  },
];

function onChange(change: { year?: string; quarter?: Quarter }) {
  updateSelection({
    quarter: change?.quarter ?? quarter,
    year: change?.year ?? year,
  });
  updatePeriod(year !== 'custom' ? get(periodEventPayload) : null);
}

const yearModel = computed({
  get() {
    return year;
  },
  set(year) {
    onChange({ year });
  },
});

const quarterModel = computed({
  get() {
    return quarter;
  },
  set(quarter) {
    onChange({ quarter });
  },
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <div>
      <div class="text-subtitle-1 font-medium mb-2">
        {{ t('generate.period') }}
      </div>
      <div class="flex gap-4">
        <RuiMenu :popper="{ placement: 'bottom-end' }">
          <template #activator="{ attrs }">
            <RuiButtonGroup
              v-model="yearModel"
              required
              variant="outlined"
              active-color="primary"
              class="flex-wrap justify-center"
              data-cy="button-group-report-period-year"
            >
              <RuiButton
                v-for="period in periods"
                :key="period"
                class="[&:last-child]:!rounded-r-none"
                :model-value="period"
              >
                {{ period }}
              </RuiButton>
            </RuiButtonGroup>
            <RuiButton
              v-bind="attrs"
              variant="outlined"
              :color="isOlderYearSelected ? 'primary' : undefined"
              class="!rounded-l-none -ml-px"
              data-cy="button-older-years"
            >
              <div class="flex items-center gap-2">
                <template v-if="isOlderYearSelected">
                  {{ year }}
                </template>
                <RuiIcon
                  name="lu-chevron-down"
                  size="16"
                />
              </div>
            </RuiButton>
          </template>

          <div class="flex flex-col">
            <RuiButton
              v-for="period in olderPeriods"
              :key="period"
              class="!px-6"
              variant="list"
              @click="yearModel = period"
            >
              {{ period }}
            </RuiButton>
          </div>
        </RuiMenu>

        <RuiButton
          variant="outlined"
          :color="isAllTime ? 'primary' : undefined"
          data-cy="button-all-time"
          @click="selectAllTime()"
        >
          {{ t('generate.all_time') }}
        </RuiButton>

        <RuiButton
          variant="outlined"
          :color="isCustom ? 'primary' : undefined"
          data-cy="button-custom"
          @click="yearModel = 'custom'"
        >
          {{ t('generate.custom_selection') }}
        </RuiButton>
      </div>
    </div>
    <div v-if="year !== 'custom' && year !== 'all-time'">
      <div class="text-subtitle-1 font-medium mb-2">
        {{ t('generate.sub_period_label') }}
      </div>
      <RuiButtonGroup
        v-model="quarterModel"
        required
        variant="outlined"
        active-color="primary"
        class="flex-wrap justify-center"
        data-cy="button-group-quarter"
      >
        <RuiButton
          v-for="subPeriod in subPeriods"
          :key="subPeriod.id"
          :model-value="subPeriod.id"
          :disabled="isStartAfterNow(subPeriod.id)"
        >
          {{ subPeriod.name }}
        </RuiButton>
      </RuiButtonGroup>
    </div>
  </div>
</template>
