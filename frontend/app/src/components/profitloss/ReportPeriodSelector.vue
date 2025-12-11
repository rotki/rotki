<script setup lang="ts">
import type { PeriodChangedEvent, SelectionChangedEvent } from '@/types/reports';
import dayjs from 'dayjs';
import { Quarter } from '@/types/settings/frontend-settings';
import { convertToTimestamp } from '@/utils/date';

const props = defineProps<{
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

const { quarter, year } = toRefs(props);

const { t } = useI18n({ useScope: 'global' });

function updatePeriod(period: PeriodChangedEvent | null) {
  emit('update:period', period);
}

function updateSelection(change: SelectionChangedEvent) {
  emit('update:selection', change);
}

function startDateTime(selection: Quarter): number {
  const startDate = QUARTER_STARTS[selection];
  return convertToTimestamp(`${startDate}/${get(year)} 00:00`);
}

function isStartAfterNow(selection: Quarter) {
  const start = startDateTime(selection);
  return start > dayjs().unix();
}

const start = computed<number>(() => startDateTime(get(quarter)));
const isCustom = computed<boolean>(() => get(year) === 'custom');
const isAllTime = computed<boolean>(() => get(year) === 'all-time');
const end = computed<number>(() => {
  const endDate = QUARTER_ENDS[get(quarter)];
  return convertToTimestamp(`${endDate}/${get(year)} 23:59:59`);
});

const periodEventPayload = computed<PeriodChangedEvent>(() => ({
  end: get(end),
  start: get(start),
}));

onMounted(() => {
  updatePeriod(get(year) !== 'custom' ? get(periodEventPayload) : null);
});

watch([year, quarter], () => {
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

const isOlderYearSelected = computed<boolean>(() => get(olderPeriods).includes(get(year)));

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
  const yearVal = get(year);
  const quarterVal = get(quarter);
  updateSelection({
    quarter: change?.quarter ?? quarterVal,
    year: change?.year ?? yearVal,
  });
  updatePeriod(yearVal !== 'custom' ? get(periodEventPayload) : null);
}

const yearModel = computed({
  get() {
    return get(year);
  },
  set(year) {
    onChange({ year });
  },
});

const quarterModel = computed({
  get() {
    return get(quarter);
  },
  set(quarter) {
    onChange({ quarter });
  },
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <div>
      <div class="text-subtitle-1 font-bold mb-2">
        {{ t('generate.period') }}
      </div>
      <div class="flex gap-4">
        <RuiMenu :popper="{ placement: 'bottom-end' }">
          <template #activator="{ attrs }">
            <RuiButtonGroup
              v-model="yearModel"
              required
              class="flex-wrap justify-center"
              active-color="primary"
            >
              <RuiButton
                v-for="period in periods"
                :key="period"
                :color="year === period ? 'primary' : undefined"
                class="px-4"
                :model-value="period"
              >
                {{ period }}
              </RuiButton>
              <RuiButton
                v-bind="attrs"
                :color="isOlderYearSelected ? 'primary' : undefined"
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
            </RuiButtonGroup>
          </template>

          <div class="flex flex-col py-2">
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
          class="px-4"
          :color="isAllTime ? 'primary' : undefined"
          @click="selectAllTime()"
        >
          {{ t('generate.all_time') }}
        </RuiButton>

        <RuiButton
          class="px-4"
          :color="isCustom ? 'primary' : undefined"
          @click="yearModel = 'custom'"
        >
          {{ t('generate.custom_selection') }}
        </RuiButton>
      </div>
    </div>
    <div
      v-if="year !== 'custom' && year !== 'all-time'"
      class="pt-3.5"
    >
      <div class="text-subtitle-1 font-bold mb-2">
        {{ t('generate.sub_period_label') }}
      </div>
      <RuiButtonGroup
        v-model="quarterModel"
        required
        class="flex-wrap justify-center"
        active-color="primary"
      >
        <RuiButton
          v-for="subPeriod in subPeriods"
          :key="subPeriod.id"
          :color="quarter === subPeriod.id ? 'primary' : undefined"
          :model-value="subPeriod.id"
          :disabled="isStartAfterNow(subPeriod.id)"
        >
          {{ subPeriod.name }}
        </RuiButton>
      </RuiButtonGroup>
    </div>
  </div>
</template>
