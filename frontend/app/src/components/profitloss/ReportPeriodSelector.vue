<script setup lang="ts">
import type { PeriodChangedEvent, SelectionChangedEvent } from '@/types/reports';
import { Quarter } from '@/types/settings/frontend-settings';
import dayjs from 'dayjs';

const props = defineProps<{
  year: string | 'custom';
  quarter: Quarter;
}>();

const emit = defineEmits<{
  (e: 'update:period', period: PeriodChangedEvent | null): void;
  (e: 'update:selection', selection: SelectionChangedEvent): void;
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

function startDateTime(selection: Quarter): string {
  const startDate = QUARTER_STARTS[selection];
  return `${startDate}/${get(year)} 00:00`;
}

function isStartAfterNow(selection: Quarter) {
  const start = startDateTime(selection);
  return dayjs(start, 'DD/MM/YYYY HH:mm').isAfter(dayjs());
}

const start = computed(() => startDateTime(get(quarter)));
const isCustom = computed(() => get(year) === 'custom');
const end = computed(() => {
  const endDate = QUARTER_ENDS[get(quarter)];
  return `${endDate}/${get(year)} 23:59:59`;
});

const periodEventPayload = computed<PeriodChangedEvent>(() => ({
  end: get(end),
  start: get(start),
}));

onMounted(() => {
  updatePeriod(get(year) !== 'custom' ? get(periodEventPayload) : null);
});

watch([year, quarter], () => {
  updatePeriod(get(isCustom) ? null : get(periodEventPayload));
});

const periods = computed(() => {
  const periods: string[] = [];
  const fullYear = new Date().getFullYear();
  for (let year = fullYear; year > fullYear - 5; year--) periods.push(year.toString());

  return periods;
});

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
      <RuiButtonGroup
        v-model="yearModel"
        required
        gap="md"
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
          model-value="custom"
          class="px-4"
          :color="isCustom ? 'primary' : undefined"
        >
          {{ t('generate.custom_selection') }}
        </RuiButton>
      </RuiButtonGroup>
    </div>
    <div
      v-if="year !== 'custom'"
      class="pt-3.5"
    >
      <div class="text-subtitle-1 font-bold mb-2">
        {{ t('generate.sub_period_label') }}
      </div>
      <RuiButtonGroup
        v-model="quarterModel"
        required
        gap="md"
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
