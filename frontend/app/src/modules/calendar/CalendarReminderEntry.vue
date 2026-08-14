<script setup lang="ts">
import { REMINDER_UNITS, ReminderUnit } from '@/modules/calendar/reminder-forms';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

const amount = defineModel<string>('amount', { required: true });
const unit = defineModel<ReminderUnit>('unit', { required: true });

const { errorMessages = [], latest } = defineProps<{
  latest: boolean;
  errorMessages?: string[];
}>();

const emit = defineEmits<{
  /** The row is done being edited, so a valid value can be persisted. */
  commit: [];
  delete: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const UNIT_LABELS: Record<ReminderUnit, string> = {
  [ReminderUnit.DAYS]: 'calendar.reminder.units.days',
  [ReminderUnit.HOURS]: 'calendar.reminder.units.hours',
  [ReminderUnit.MINUTES]: 'calendar.reminder.units.minutes',
  [ReminderUnit.WEEKS]: 'calendar.reminder.units.weeks',
};

const unitOptions = computed<{ key: ReminderUnit; label: string }[]>(() =>
  REMINDER_UNITS.map(unit => ({ key: unit, label: t(UNIT_LABELS[unit]) })),
);

const amountInputWrapper = useTemplateRef<InstanceType<typeof AmountInput>>('amountInputWrapper');

onMounted(() => {
  if (latest) {
    const input = get(amountInputWrapper)?.$el.querySelector('input');
    input?.select();
  }
});
</script>

<template>
  <div class="flex gap-4">
    <AmountInput
      ref="amountInputWrapper"
      v-model="amount"
      :label="t('calendar.reminder.labels.amount')"
      integer
      variant="outlined"
      :error-messages="errorMessages"
      dense
      data-testid="reminder-amount"
      @blur="emit('commit')"
    />
    <div class="w-[10rem]">
      <RuiMenuSelect
        v-model="unit"
        :label="t('calendar.reminder.labels.unit')"
        :options="unitOptions"
        variant="outlined"
        key-attr="key"
        text-attr="label"
        dense
        data-testid="reminder-unit"
        @update:model-value="emit('commit')"
      />
    </div>

    <div class="pt-2 text-rui-text-secondary text-sm">
      {{ t('calendar.reminder.before_event') }}
    </div>
    <div>
      <RuiButton
        icon
        color="error"
        variant="text"
        class="!p-2"
        data-testid="reminder-delete"
        @click="emit('delete')"
      >
        <RuiIcon
          size="20"
          name="lu-trash-2"
        />
      </RuiButton>
    </div>
  </div>
</template>
