<script setup lang="ts">
import type { PeriodChangedEvent, SelectionChangedEvent } from '@/types/reports';
import useVuelidate from '@vuelidate/core';
import { helpers, requiredIf } from '@vuelidate/validators';
import dayjs from 'dayjs';
import ReportPeriodSelector from '@/components/profitloss/ReportPeriodSelector.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';

const modelValue = defineModel<{ start: number; end: number }>({ required: true });

const emit = defineEmits<{
  (e: 'update:valid', valid: boolean): void;
}>();

const store = useFrontendSettingsStore();
const { profitLossReportPeriod } = storeToRefs(store);
const invalidRange = computed(
  () => {
    const model = get(modelValue);
    return !!model
      && !!model.start
      && !!model.end
      && model.start > model.end;
  },
);

const year = computed(() => get(profitLossReportPeriod).year);
const quarter = computed(() => get(profitLossReportPeriod).quarter);
const custom = computed(() => get(year) === 'custom');

const start = useRefPropVModel(modelValue, 'start');
const end = useRefPropVModel(modelValue, 'end');

function input(data: { start: number; end: number }) {
  set(modelValue, data);
}

function updateValid(valid: boolean) {
  emit('update:valid', valid);
}

async function onChanged(event: SelectionChangedEvent) {
  if (event.year === 'custom')
    input({ end: 0, start: 0 });

  await store.updateSetting({
    profitLossReportPeriod: event,
  });
}

function onPeriodChange(period: PeriodChangedEvent | null) {
  if (period === null) {
    input({ end: 0, start: 0 });
    return;
  }

  const start = period.start;
  let end = period.end;
  const now = dayjs().unix();
  end = Math.min(end, now);
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
        <RuiDateTimePicker
          v-model="start"
          :label="t('generate.labels.start_date')"
          allow-empty
          color="primary"
          variant="outlined"
          type="epoch"
          :max-date="end"
          :error-messages="toMessages(v$.start)"
        />
      </div>
      <div>
        <RuiDateTimePicker
          v-model="end"
          :min-date="start"
          :label="t('generate.labels.end_date')"
          max-date="now"
          type="epoch"
          color="primary"
          variant="outlined"
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
