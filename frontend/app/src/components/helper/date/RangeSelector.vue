<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, requiredIf } from '@vuelidate/validators';
import dayjs from 'dayjs';
import {
  type PeriodChangedEvent,
  type SelectionChangedEvent
} from '@/types/reports';

const props = defineProps<{ value: { start: string; end: string } }>();

const emit = defineEmits<{
  (e: 'input', value: { start: string; end: string }): void;
  (e: 'update:valid', valid: boolean): void;
}>();

const { value } = toRefs(props);

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

const input = (data: { start: string; end: string }) => {
  emit('input', data);
};

const updateValid = (valid: boolean) => {
  emit('update:valid', valid);
};

const onChanged = async (event: SelectionChangedEvent) => {
  if (event.year === 'custom') {
    input({ start: '', end: '' });
  }

  await store.updateSetting({
    profitLossReportPeriod: event
  });
};

const onPeriodChange = (period: PeriodChangedEvent | null) => {
  if (period === null) {
    input({ start: '', end: '' });
    return;
  }

  const start = period.start;
  let end = period.end;
  if (convertToTimestamp(period.end) > dayjs().unix()) {
    end = dayjs().format('DD/MM/YYYY HH:mm:ss');
  }
  input({ start, end });
};

const { t } = useI18n();

const rules = {
  start: {
    required: helpers.withMessage(
      t('generate.validation.empty_start_date').toString(),
      requiredIf(custom)
    )
  },
  end: {
    required: helpers.withMessage(
      t('generate.validation.empty_end_date').toString(),
      requiredIf(custom)
    )
  }
};

const v$ = useVuelidate(
  rules,
  {
    start: computed(() => get(value).start),
    end: computed(() => get(value).end)
  },
  { $autoDirty: false }
);

watch(v$, ({ $invalid }) => {
  updateValid(!$invalid);
});
</script>

<template>
  <div class="range-selector">
    <ReportPeriodSelector
      :year="year"
      :quarter="quarter"
      @update:period="onPeriodChange($event)"
      @update:selection="onChanged($event)"
    />
    <VRow v-if="custom">
      <VCol cols="12" md="6">
        <DateTimePicker
          :value="value.start"
          outlined
          label="Start Date"
          limit-now
          allow-empty
          :error-messages="v$.start.$errors.map(e => e.$message)"
          @input="$emit('input', { start: $event, end: value.end })"
        />
      </VCol>
      <VCol cols="12" md="6">
        <DateTimePicker
          :value="value.end"
          outlined
          label="End Date"
          limit-now
          :error-messages="v$.end.$errors.map(e => e.$message)"
          @input="$emit('input', { start: value.start, end: $event })"
        />
      </VCol>
    </VRow>
    <VAlert v-model="invalidRange" type="error" dense>
      {{ t('generate.validation.end_after_start') }}
    </VAlert>
  </div>
</template>
