<script setup lang="ts">
import type { AccountingRuleEntry } from '@/types/settings/accounting';
import type { EvmChainAndTxHash, HistoryEventEntry } from '@/types/history/events';

const emit = defineEmits<{
  'redecode': [data: EvmChainAndTxHash];
  'edit-event': [event: HistoryEventEntry];
  'add': [rule: Pick<AccountingRuleEntry, 'eventType' | 'eventSubtype' | 'counterparty'>];
  'dismiss': [];
}>();

const modelValue = defineModel<HistoryEventEntry | undefined>({ required: true });

const { t } = useI18n();

const options = computed(() => [
  {
    icon: 'restart-line',
    action: onRedecode,
    label: t('actions.history_events.missing_rule.re_decode'),
    show: isDefined(modelValue) ? isEvmEvent(get(modelValue)) : false,
  },
  {
    icon: 'pencil-line',
    action: onEdit,
    label: t('actions.history_events.missing_rule.edit'),
    show: true,
  },
  {
    icon: 'add-line',
    action: onAddRule,
    label: t('actions.history_events.missing_rule.add_rule'),
    show: true,
  },
] as const);

function close() {
  emit('dismiss');
}

function onRedecode(event: HistoryEventEntry) {
  emit('redecode', toEvmChainAndTxHash(event));
  close();
}

function onEdit(event: HistoryEventEntry) {
  emit('edit-event', event);
  close();
}

function onAddRule(event: HistoryEventEntry) {
  const { eventType, eventSubtype } = event;

  emit('add', {
    eventSubtype,
    eventType,
    counterparty: 'counterparty' in event ? event.counterparty : null,
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
