<script setup lang="ts">
import type { HistoryEventEntryType } from '@rotki/common';
import type { LocationQueryRaw } from 'vue-router';
import { startPromise } from '@shared/utils';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import HistoryEventActionPicker from '@/modules/history/events/action-picker/HistoryEventActionPicker.vue';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';

interface HistoryEventTypeFormProps {
  counterparty?: string | null;
  location?: string | null;
  disabled?: boolean;
  /**
   * Messages for the two fields this form owns, already resolved to strings. Deliberately not a
   * validator instance: the parent owns validation, this component only renders what it is given,
   * which is what lets Vuelidate and zod parents share it.
   */
  errorMessages: {
    eventType: string[];
    eventSubtype: string[];
  };
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
  errorMessages,
  disableWarning,
  entryType,
  showAccountingRuleLink = false,
  dirty = false,
} = defineProps<HistoryEventTypeFormProps>();

const emit = defineEmits<{
  touch: [];
}>();

const router = useRouter();
const { show } = useConfirmStore();
const { t } = useI18n({ useScope: 'global' });

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
    emit('touch');
  },
});

const { findEventTypeData } = useHistoryEventMappings();

const historyTypeCombination = computed(() => findEventTypeData({
  counterparty,
  eventSubtype: get(eventSubType) ?? 'none',
  eventType: get(eventType),
  location,
}, false));

/**
 * Gated on the pair being set rather than on it having been touched: a fresh form has nothing to
 * warn about yet, and an existing event with an unrecognised combination should say so on sight.
 */
const showHistoryEventTypeCombinationWarning = computed<boolean>(() => {
  if (!get(eventType) || !get(eventSubType))
    return false;

  return !get(historyTypeCombination).identifier;
});

const pickerErrorMessages = computed<string[]>(() => [
  ...errorMessages.eventType,
  ...errorMessages.eventSubtype,
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

  startPromise(router.push({ name: '/settings/accounting/', query }));
}

/** Navigating away discards unsaved edits, so a dirty form gets the dialog's prompt-on-close. */
function viewAccountingRule(): void {
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
