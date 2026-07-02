<script setup lang="ts">
import type { HistoryEventEntryType } from '@rotki/common';
import type { Validation } from '@vuelidate/core';
import type { LocationQueryRaw } from 'vue-router';
import { startPromise } from '@shared/utils';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { toMessages } from '@/modules/core/common/validation/validation';
import HistoryEventActionPicker from '@/modules/history/events/action-picker/HistoryEventActionPicker.vue';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';
import { Routes } from '@/router/routes';

interface HistoryEventTypeFormProps {
  counterparty?: string | null;
  location?: string | null;
  disabled?: boolean;
  v$: Validation;
  disableWarning?: boolean;
  entryType?: HistoryEventEntryType;
  showAccountingRuleLink?: boolean;
  dirty?: boolean;
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
  showAccountingRuleLink = false,
  dirty = false,
} = defineProps<HistoryEventTypeFormProps>();

const router = useRouter();
const { show } = useConfirmStore();

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

const canLinkToAccountingRule = computed<boolean>(() =>
  showAccountingRuleLink && !!get(eventType) && !!get(eventSubType),
);

function navigateToAccountingRule(): void {
  const query: LocationQueryRaw = {
    eventSubtypes: get(eventSubType),
    eventTypes: get(eventType),
  };
  if (counterparty)
    query.counterparties = counterparty;

  startPromise(router.push({ path: Routes.SETTINGS_ACCOUNTING.toString(), query }));
}

function viewAccountingRule(): void {
  // Leaving the editor discards unsaved edits, so confirm first when the form
  // is dirty (mirrors the dialog's prompt-on-close behaviour).
  if (dirty) {
    show({
      message: t('big_dialog.prompt_close.message'),
      primaryAction: t('big_dialog.prompt_close.actions.discard'),
      title: t('big_dialog.prompt_close.title'),
    }, navigateToAccountingRule);
    return;
  }

  navigateToAccountingRule();
}

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
    <RuiButton
      v-if="canLinkToAccountingRule"
      variant="text"
      color="primary"
      size="sm"
      class="-mt-2 mb-4"
      data-testid="view-accounting-rule"
      @click="viewAccountingRule()"
    >
      <template #prepend>
        <RuiIcon
          name="lu-scale"
          size="16"
        />
      </template>
      {{ t('transactions.events.form.view_accounting_rule') }}
    </RuiButton>
  </div>
</template>
