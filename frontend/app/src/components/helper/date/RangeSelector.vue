<template>
  <div class="range-selector">
    <report-period-selector
      :year="year"
      :quarter="quarter"
      @update:period="onPeriodChange"
      @update:selection="onChanged"
    />
    <v-row v-if="custom">
      <v-col cols="12" md="6">
        <date-time-picker
          :value="value.start"
          outlined
          label="Start Date"
          limit-now
          :rules="startRules"
          @input="$emit('input', { start: $event, end: value.end })"
        />
      </v-col>
      <v-col cols="12" md="6">
        <date-time-picker
          :value="value.end"
          outlined
          label="End Date"
          limit-now
          :rules="endRules"
          @input="$emit('input', { start: value.start, end: $event })"
        />
      </v-col>
    </v-row>
    <v-alert v-model="invalidRange" type="error" dense>
      {{ t('generate.validation.end_after_start') }}
    </v-alert>
  </div>
</template>

<script setup lang="ts">
import dayjs from 'dayjs';

import ReportPeriodSelector from '@/components/profitloss/ReportPeriodSelector.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { PeriodChangedEvent, SelectionChangedEvent } from '@/types/reports';
import { convertToTimestamp } from '@/utils/date';

defineProps({
  value: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['input']);
const store = useFrontendSettingsStore();
const { profitLossReportPeriod } = storeToRefs(store);
const invalidRange = computed(
  ({ value }) =>
    !!value &&
    !!value.start &&
    !!value.end &&
    convertToTimestamp(value.start) > convertToTimestamp(value.end)
);

const year = computed(() => get(profitLossReportPeriod).year);
const quarter = computed(() => get(profitLossReportPeriod).quarter);
const custom = computed(() => get(year) === 'custom');

const onChanged = async (event: SelectionChangedEvent) => {
  if (event.year === 'custom') {
    emit('input', { start: '', end: '' });
  }

  await store.updateSetting({
    profitLossReportPeriod: event
  });
};

const onPeriodChange = (period: PeriodChangedEvent | null) => {
  if (period === null) {
    emit('input', { start: '', end: '' });
    return;
  }

  const start = period.start;
  let end = period.end;
  if (convertToTimestamp(period.end) > dayjs().unix()) {
    end = dayjs().format('DD/MM/YYYY HH:mm:ss');
  }
  emit('input', { start, end });
};

const { t } = useI18n();

const startRules = [
  (v: string) => !!v || t('generate.validation.empty_start_date').toString()
];
const endRules = [
  (v: string) => !!v || t('generate.validation.empty_end_date').toString()
];
</script>
