<script setup lang="ts">
import type { PeriodChangedEvent, SelectionChangedEvent } from '@/types/reports';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import ReportPeriodSelector from '@/components/profitloss/ReportPeriodSelector.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { convertToTimestamp } from '@/utils/date';
import { useSimplePropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';
import useVuelidate from '@vuelidate/core';
import { helpers, requiredIf } from '@vuelidate/validators';
import dayjs from 'dayjs';

const props = defineProps<{ modelValue: { start: string; end: string } }>();

const emit = defineEmits<{
  (e: 'update:model-value', value: { start: string; end: string }): void;
  (e: 'update:valid', valid: boolean): void;
}>();

const store = useFrontendSettingsStore();
const { profitLossReportPeriod } = storeToRefs(store);
const invalidRange = computed(
  () =>
    !!props.modelValue
    && !!props.modelValue.start
    && !!props.modelValue.end
    && convertToTimestamp(props.modelValue.start) > convertToTimestamp(props.modelValue.end),
);

const year = computed(() => get(profitLossReportPeriod).year);
const quarter = computed(() => get(profitLossReportPeriod).quarter);
const custom = computed(() => get(year) === 'custom');

const start = useSimplePropVModel(props, 'start', emit);
const end = useSimplePropVModel(props, 'end', emit);

function input(data: { start: string; end: string }) {
  emit('update:model-value', data);
}

function updateValid(valid: boolean) {
  emit('update:valid', valid);
}

async function onChanged(event: SelectionChangedEvent) {
  if (event.year === 'custom')
    input({ end: '', start: '' });

  await store.updateSetting({
    profitLossReportPeriod: event,
  });
}

function onPeriodChange(period: PeriodChangedEvent | null) {
  if (period === null) {
    input({ end: '', start: '' });
    return;
  }

  const start = period.start;
  let end = period.end;
  if (convertToTimestamp(period.end) > dayjs().unix())
    end = dayjs().format('DD/MM/YYYY HH:mm:ss');

  input({ end, start });
}

const { t } = useI18n({ useScope: 'global' });

const rules = {
  end: {
    required: helpers.withMessage(t('generate.validation.empty_end_date'), requiredIf(custom)),
  },
  start: {
    required: helpers.withMessage(t('generate.validation.empty_start_date'), requiredIf(custom)),
  },
};

const v$ = useVuelidate(
  rules,
  {
    end,
    start,
  },
  { $autoDirty: false },
);

watchImmediate(v$, ({ $invalid }) => {
  updateValid(!$invalid);
});
</script>

<template>
  <div class="range-selector flex flex-col gap-4">
    <ReportPeriodSelector
      :year="year"
      :quarter="quarter"
      @update:period="onPeriodChange($event)"
      @update:selection="onChanged($event)"
    />
    <div
      v-if="custom"
      class="grid md:grid-cols-2 gap-4 mt-1.5"
    >
      <div>
        <DateTimePicker
          v-model="start"
          :label="t('generate.labels.start_date')"
          limit-now
          allow-empty
          :error-messages="toMessages(v$.start)"
        />
      </div>
      <div>
        <DateTimePicker
          v-model="end"
          :label="t('generate.labels.end_date')"
          limit-now
          :error-messages="toMessages(v$.end)"
        />
      </div>
    </div>
    <RuiAlert
      v-if="invalidRange"
      type="error"
    >
      <template #title>
        {{ t('generate.validation.end_after_start') }}
      </template>
    </RuiAlert>
  </div>
</template>
