<script setup lang="ts">
import dayjs from 'dayjs';
import { Quarter } from '@/types/settings/frontend-settings';
import {
  type PeriodChangedEvent,
  type SelectionChangedEvent
} from '@/types/reports';

const props = withDefaults(
  defineProps<{
    year: string | 'custom';
    quarter: Quarter;
  }>(),
  {
    year: () => new Date().getFullYear().toString()
  }
);

const emit = defineEmits<{
  (e: 'update:period', period: PeriodChangedEvent | null): void;
  (e: 'update:selection', selection: SelectionChangedEvent): void;
}>();

const QUARTER_STARTS: { [quarter in Quarter]: string } = {
  [Quarter.ALL]: '01/01',
  [Quarter.Q1]: '01/01',
  [Quarter.Q2]: '01/04',
  [Quarter.Q3]: '01/07',
  [Quarter.Q4]: '01/10'
};

const QUARTER_ENDS: { [quarter in Quarter]: string } = {
  [Quarter.Q1]: '31/03',
  [Quarter.Q2]: '30/06',
  [Quarter.Q3]: '30/09',
  [Quarter.Q4]: '31/12',
  [Quarter.ALL]: '31/12'
};

const { quarter, year } = toRefs(props);

const { t } = useI18n();

const updatePeriod = (period: PeriodChangedEvent | null) => {
  emit('update:period', period);
};

const updateSelection = (change: SelectionChangedEvent) => {
  emit('update:selection', change);
};

const startDateTime = (selection: Quarter): string => {
  const startDate = QUARTER_STARTS[selection];
  return `${startDate}/${year.value} 00:00`;
};

const isStartAfterNow = (selection: Quarter) => {
  const start = startDateTime(selection);
  return dayjs(start, 'DD/MM/YYYY HH:mm').isAfter(dayjs());
};

const onChange = (change: { year?: string; quarter?: Quarter }) => {
  updateSelection({
    year: change?.year ?? year.value,
    quarter: change?.quarter ?? quarter.value
  });
  updatePeriod(year.value !== 'custom' ? periodEventPayload.value : null);
};

const start = computed(() => startDateTime(quarter.value));
const isCustom = computed(() => year.value === 'custom');
const end = computed(() => {
  const endDate = QUARTER_ENDS[quarter.value];
  return `${endDate}/${year.value} 23:59:59`;
});

const periodEventPayload = computed<PeriodChangedEvent>(() => ({
  start: start.value,
  end: end.value
}));

onMounted(() => {
  updatePeriod(year.value !== 'custom' ? periodEventPayload.value : null);
});

watch([year, quarter], () => {
  updatePeriod(isCustom.value ? null : periodEventPayload.value);
});

const periods = computed(() => {
  const periods: string[] = [];
  const fullYear = new Date().getFullYear();
  for (let year = fullYear; year > fullYear - 5; year--) {
    periods.push(year.toString());
  }
  return periods;
});

const subPeriods = [
  {
    id: Quarter.ALL,
    name: t('generate.sub_period.all').toString()
  },
  {
    id: Quarter.Q1,
    name: 'Q1'
  },
  {
    id: Quarter.Q2,
    name: 'Q2'
  },
  {
    id: Quarter.Q3,
    name: 'Q3'
  },
  {
    id: Quarter.Q4,
    name: 'Q4'
  }
];
</script>

<template>
  <div class="flex flex-col gap-4">
    <div>
      <span class="text-subtitle-1 font-bold">{{ t('generate.period') }}</span>
      <VChipGroup
        :value="year"
        mandatory
        column
        @change="onChange({ year: $event })"
      >
        <VChip
          v-for="period in periods"
          :key="period"
          :color="year === period ? 'primary' : null"
          class="px-4"
          :value="period"
          label
        >
          {{ period }}
        </VChip>
        <VChip
          value="custom"
          class="px-4"
          label
          :color="isCustom ? 'primary' : null"
        >
          {{ t('generate.custom_selection') }}
        </VChip>
      </VChipGroup>
    </div>
    <div v-if="year !== 'custom'">
      <span class="text-subtitle-1 font-bold">
        {{ t('generate.sub_period_label') }}
      </span>
      <VChipGroup
        :value="quarter"
        mandatory
        @change="onChange({ quarter: $event })"
      >
        <VChip
          v-for="subPeriod in subPeriods"
          :key="subPeriod.id"
          :color="quarter === subPeriod.id ? 'primary' : null"
          :value="subPeriod.id"
          :disabled="isStartAfterNow(subPeriod.id)"
          label
          class="px-4"
        >
          {{ subPeriod.name }}
        </VChip>
      </VChipGroup>
    </div>
  </div>
</template>
