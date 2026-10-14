<script setup lang="ts">
import { REMINDER_UNITS, type ReminderUnit, UNIT_LABELS } from '@/modules/calendar/reminder-forms';
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
  <div class="flex items-start gap-3">
    <AmountInput
      ref="amountInputWrapper"
      v-model="amount"
      :label="t('calendar.reminder.labels.amount')"
      label-placement="hidden"
      class="w-28"
      integer
      :error-messages="errorMessages"
      dense
      data-testid="reminder-amount"
      @blur="emit('commit')"
    />
    <div class="w-40">
      <RuiMenuSelect
        v-model="unit"
        :label="t('calendar.reminder.labels.unit')"
        label-placement="hidden"
        :options="unitOptions"
        key-attr="key"
        text-attr="label"
        dense
        data-testid="reminder-unit"
        @update:model-value="emit('commit')"
      />
    </div>

    <div class="flex h-8 items-center text-sm text-rui-text-secondary">
      {{ t('calendar.reminder.before_event') }}
    </div>
    <RuiButton
      icon
      color="error"
      variant="text"
      size="sm"
      class="ml-auto size-8!"
      :aria-label="t('common.actions.delete')"
      data-testid="reminder-delete"
      @click="emit('delete')"
    >
      <RuiIcon
        size="16"
        name="lu-trash-2"
      />
    </RuiButton>
  </div>
</template>
