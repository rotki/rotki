<script setup lang="ts">
import type { HistoryEventEntryType } from '@rotki/common';
import type { Validation } from '@vuelidate/core';
import { toMessages } from '@/modules/core/common/validation/validation';
import HistoryEventActionPicker from '@/modules/history/events/action-picker/HistoryEventActionPicker.vue';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';

interface HistoryEventTypeFormProps {
  counterparty?: string | null;
  location?: string | null;
  disabled?: boolean;
  v$: Validation;
  disableWarning?: boolean;
  entryType?: HistoryEventEntryType;
}

const eventType = defineModel<string>('eventType', { required: true });
const eventSubType = defineModel<string | undefined>('eventSubtype', { required: true });

const {
  counterparty = null,
  location = null,
  disabled,
  v$,
  disableWarning,
  entryType,
} = defineProps<HistoryEventTypeFormProps>();

const pickerValue = computed<{ eventType: string; eventSubtype: string } | undefined>({
  get: () => {
    const t = get(eventType);
    const s = get(eventSubType);
    if (!t || !s)
      return undefined;

    return { eventSubtype: s, eventType: t };
  },
  set: (value) => {
    set(eventType, value?.eventType ?? '');
    set(eventSubType, value?.eventSubtype);
    v$.eventType.$touch();
    v$.eventSubtype.$touch();
  },
});

const { findEventTypeData } = useHistoryEventMappings();

const historyTypeCombination = computed(() => findEventTypeData({
  counterparty,
  eventSubtype: get(eventSubType) ?? 'none',
  eventType: get(eventType),
  location,
}, false));

const showHistoryEventTypeCombinationWarning = computed<boolean>(() => {
  if (!v$.eventType.$dirty && !v$.eventSubtype.$dirty)
    return false;

  return !get(historyTypeCombination).identifier;
});

const pickerErrorMessages = computed<string[]>(() => [
  ...toMessages(v$.eventType),
  ...toMessages(v$.eventSubtype),
]);

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div>
    <HistoryEventActionPicker
      v-model="pickerValue"
      :entry-type="entryType"
      :disabled="disabled"
      required
      :hint="t('transactions.events.form.action.hint')"
      :error-messages="pickerErrorMessages"
    />
    <RuiAlert
      v-if="!disableWarning && showHistoryEventTypeCombinationWarning"
      class="mt-2 mb-6"
      type="warning"
      variant="filled"
      :description="t('transactions.events.form.resulting_combination.unknown')"
    />
  </div>
</template>
