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

interface Props {
  modelValue: { start: number | null; end: number | null };
  valid: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: 'update:model-value', value: { start: number | null; end: number | null }): void;
  (e: 'update:valid', valid: boolean): void;
}>();

const store = useFrontendSettingsStore();
const { profitLossReportPeriod } = storeToRefs(store);

const invalidRange = computed(() => !!props.modelValue.start && !!props.modelValue.end && props.modelValue.start > props.modelValue.end);

const year = computed(() => get(profitLossReportPeriod).year);
const quarter = computed(() => get(profitLossReportPeriod).quarter);
const custom = computed(() => get(year) === 'custom');

const start = useSimplePropVModel(props, 'start', emit);
const end = useSimplePropVModel(props, 'end', emit);

function input(data: { start: number | null; end: number | null }) {
  emit('update:model-value', data);
}

function updateValid(valid: boolean) {
  emit('update:valid', valid);
}

async function onChanged(event: SelectionChangedEvent) {
  if (event.year === 'custom') {
    input({ end: null, start: null });
  }

  await store.updateSetting({
    profitLossReportPeriod: event,
  });
}

function onPeriodChange(period: PeriodChangedEvent | null) {
  if (period === null) {
    input({ end: null, start: null });
    return;
  }

  const start = convertToTimestamp(period.start);
  let end = convertToTimestamp(period.end);
  if (end > dayjs().unix())
    end = dayjs().valueOf();

  input({ end, start });
}

const { t } = useI18n();

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
        {{ t("generate.validation.end_after_start") }}
      </template>
    </RuiAlert>
  </div>
</template>
