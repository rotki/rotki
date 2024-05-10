<script setup lang="ts">
import type { AccountingRuleEntry } from '@/types/settings/accounting';
import type {
  EvmChainAndTxHash,
  HistoryEventEntry,
} from '@/types/history/events';

const props = withDefaults(
  defineProps<{
    value: boolean;
    event: HistoryEventEntry;
  }>(),
  {
    event: undefined,
    value: false,
  },
);

const emit = defineEmits<{
  (e: 're-decode', data: EvmChainAndTxHash): void;
  (e: 'edit', event?: HistoryEventEntry): void;
  (
    e: 'add-rule',
    data: Pick<
      AccountingRuleEntry,
      'eventType' | 'eventSubtype' | 'counterparty'
    >
  ): void;
  (e: 'input', value: boolean): void;
}>();

const { t } = useI18n();

const { event } = toRefs(props);

const isEvm = computed(() => {
  const entry = get(event);

  if (!entry)
    return false;

  return isEvmEvent(entry);
});

function onRedecode() {
  const entry = get(event);

  if (!entry)
    return false;

  emit('re-decode', toEvmChainAndTxHash(entry));
  close();
}

function onEdit() {
  const entry = get(event);

  if (!entry)
    return false;

  emit('edit', entry);
  close();
}

function onAddRule() {
  const entry = get(event);

  if (!entry)
    return false;

  const { eventType, eventSubtype } = entry;

  if ('counterparty' in entry) {
    emit('add-rule', {
      eventSubtype,
      eventType,
      counterparty: entry.counterparty,
    });
  }
  else {
    emit('add-rule', { eventSubtype, eventType, counterparty: null });
  }

  close();
}

function close() {
  emit('input', false);
}
</script>

<template>
  <RuiDialog
    :value="value"
    :max-width="500"
    @closed="close()"
  >
    <RuiCard data-cy="missing-rules-dialog">
      <template #header>
        {{ t('actions.history_events.missing_rule.title') }}
      </template>

      <p class="text-body-1 text-rui-text-secondary mb-2">
        {{ t('actions.history_events.missing_rule.message') }}
      </p>

      <div class="flex flex-col gap-1">
        <RuiButton
          v-if="isEvm"
          size="lg"
          class="justify-start"
          variant="text"
          @click="onRedecode()"
        >
          <template #prepend>
            <RuiIcon
              color="secondary"
              name="restart-line"
            />
          </template>
          {{ t('actions.history_events.missing_rule.re_decode') }}
        </RuiButton>
        <RuiButton
          size="lg"
          class="justify-start"
          variant="text"
          @click="onEdit()"
        >
          <template #prepend>
            <RuiIcon
              color="secondary"
              name="pencil-line"
            />
          </template>
          {{ t('actions.history_events.missing_rule.edit') }}
        </RuiButton>
        <RuiButton
          size="lg"
          class="justify-start"
          variant="text"
          @click="onAddRule()"
        >
          <template #prepend>
            <RuiIcon
              color="secondary"
              name="add-line"
            />
          </template>
          {{ t('actions.history_events.missing_rule.add_rule') }}
        </RuiButton>
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
