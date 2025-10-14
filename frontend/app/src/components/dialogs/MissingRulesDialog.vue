<script setup lang="ts">
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import type { LocationAndTxHash } from '@/types/history/events';
import type { AccountingRuleEntry } from '@/types/settings/accounting';
import { isEventDecodable } from '@/modules/history/management/forms/form-guards';
import { toLocationAndTxHash } from '@/utils/history';

const modelValue = defineModel<HistoryEventEditData | undefined>({ required: true });

const emit = defineEmits<{
  'redecode': [data: LocationAndTxHash];
  'edit-event': [event: HistoryEventEditData];
  'add': [rule: Pick<AccountingRuleEntry, 'eventType' | 'eventSubtype' | 'counterparty'>];
  'dismiss': [];
}>();

const { t } = useI18n({ useScope: 'global' });

function canRedecode(data?: HistoryEventEditData): boolean {
  if (!data || data.type === 'edit-group') {
    return false;
  }
  return !!isEventDecodable(data.event);
}

const options = computed(() => [{
  action: onRedecode,
  icon: 'lu-rotate-ccw',
  label: t('actions.history_events.missing_rule.re_decode'),
  show: canRedecode(get(modelValue)),
}, {
  action: onEdit,
  icon: 'lu-pencil',
  label: t('actions.history_events.missing_rule.edit'),
  show: true,
}, {
  action: onAddRule,
  icon: 'lu-plus',
  label: t('actions.history_events.missing_rule.add_rule'),
  show: true,
}] as const);

function close() {
  emit('dismiss');
}

function onRedecode(data: HistoryEventEditData) {
  const event = data.type === 'edit' ? data.event : data.eventsInGroup[0];
  const decodableEvent = isEventDecodable(event);
  if (decodableEvent) {
    emit('redecode', toLocationAndTxHash(decodableEvent));
  }
  close();
}

function onEdit(data: HistoryEventEditData) {
  emit('edit-event', data);
  close();
}

function onAddRule(data: HistoryEventEditData) {
  const event = data.type === 'edit' ? data.event : data.eventsInGroup[0];
  const { eventSubtype, eventType } = event;

  emit('add', {
    counterparty: 'counterparty' in event ? event.counterparty : null,
    eventSubtype,
    eventType,
  });
  close();
}
</script>

<template>
  <RuiDialog
    :model-value="!!modelValue"
    :max-width="500"
    @closed="close()"
  >
    <RuiCard
      v-if="modelValue"
      data-cy="missing-rules-dialog"
    >
      <template #header>
        {{ t('actions.history_events.missing_rule.title') }}
      </template>

      <p class="text-body-1 text-rui-text-secondary mb-2">
        {{ t('actions.history_events.missing_rule.message') }}
      </p>

      <div class="flex flex-col gap-1">
        <template
          v-for="{ action, icon, label, show } in options"
          :key="icon"
        >
          <RuiButton
            v-if="show"
            size="lg"
            class="justify-start"
            variant="text"
            @click="action(modelValue)"
          >
            <template #prepend>
              <RuiIcon
                color="secondary"
                :name="icon"
              />
            </template>

            {{ label }}
          </RuiButton>
        </template>
      </div>

      <template #footer>
        <div class="grow" />
        <RuiButton
          color="primary"
          data-cy="button-ok"
          @click="close()"
        >
          {{ t('common.actions.ok') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
