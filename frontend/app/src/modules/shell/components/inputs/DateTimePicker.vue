<script setup lang="ts">
import type { RuiDateTimePicker } from '@rotki/ui-library';
import type { RuiDateTimePickerProps } from '@rotki/ui-library/components';

import type { ForwardedProps } from '@/modules/core/common/forwarded-props';
import dayjs, { type ManipulateType } from 'dayjs';

/** The picker's model is a number, so a `Date` shape is not on offer. */
type EpochPickerProps = Omit<RuiDateTimePickerProps, 'type'> & { type?: 'epoch' | 'epoch-ms' };

interface QuickOption {
  label: string;
  unit: ManipulateType;
  value: number;
}

const modelValue = defineModel<number>({ required: true });

const {
  accuracy,
  allowEmpty,
  dense,
  disabled,
  errorMessages,
  details,
  format,
  hint,
  label,
  maxDate,
  minDate,
  readonly,
  required,
  successMessages,
  type,
} = defineProps<EpochPickerProps & /* @vue-ignore */ ForwardedProps<typeof RuiDateTimePicker, RuiDateTimePickerProps>>();

const { t } = useI18n({ useScope: 'global' });

const quickOptions = computed<QuickOption[]>(() => [
  { label: t('date_time_picker.one_day_before'), unit: 'day', value: 1 },
  { label: t('date_time_picker.week_before'), unit: 'week', value: 1 },
  { label: t('date_time_picker.month_before'), unit: 'month', value: 1 },
  { label: t('date_time_picker.days_before', { days: 90 }), unit: 'day', value: 90 },
  { label: t('date_time_picker.months_before', { months: 6 }), unit: 'month', value: 6 },
  { label: t('date_time_picker.year_before'), unit: 'year', value: 1 },
]);

const useMilliseconds = computed<boolean>(() => accuracy === 'millisecond');

/** The picker only reports no date when `allowEmpty` lets it be cleared; the model keeps its date then. */
function pick(value: number | undefined): void {
  if (value !== undefined)
    set(modelValue, value);
}

function applyQuickOption(option: QuickOption): void {
  const currentValue = get(modelValue);
  const currentDate = get(useMilliseconds) ? dayjs(currentValue) : dayjs.unix(currentValue);
  const date = currentDate.subtract(option.value, option.unit);
  set(modelValue, get(useMilliseconds) ? date.valueOf() : date.unix());
}
</script>

<template>
  <RuiDateTimePicker
    :model-value="modelValue"
    :accuracy="accuracy"
    :allow-empty="allowEmpty"
    :dense="dense"
    :disabled="disabled"
    :details="details"
    :error-messages="errorMessages"
    :format="format"
    :hint="hint"
    :label="label"
    :max-date="maxDate"
    :min-date="minDate"
    :readonly="readonly"
    :required="required"
    :success-messages="successMessages"
    :type="type"
    @update:model-value="pick($event)"
  >
    <template #menu-content>
      <div class="border-t border-default flex flex-col pt-2">
        <RuiButton
          v-for="option in quickOptions"
          :key="`${option.value}-${option.unit}`"
          variant="list"
          size="sm"
          @click="applyQuickOption(option)"
        >
          {{ option.label }}
        </RuiButton>
      </div>
    </template>
  </RuiDateTimePicker>
</template>
