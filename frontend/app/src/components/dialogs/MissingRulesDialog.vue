<script setup lang="ts">
import { toEvmChainAndTxHash } from '@/utils/history';
import type { AccountingRuleEntry } from '@/types/settings/accounting';
import type {
  EvmChainAndTxHash,
  HistoryEventEntry,
} from '@/types/history/events';

const props = withDefaults(
  defineProps<{
    modelValue: boolean;
    event: HistoryEventEntry;
  }>(),
  {
    event: undefined,
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
  (e: 'update:model-value', value: boolean): void;
}>();

const { t } = useI18n();

const { event } = toRefs(props);

const model = useSimpleVModel(props, emit);

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
  emit('update:model-value', false);
}

function onEdit() {
  const entry = get(event);

  if (!entry)
    return false;

  emit('edit', entry);
  emit('update:model-value', false);
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

  emit('update:model-value', false);
}
</script>

<template>
  <RuiDialog
    v-model="model"
    :max-width="500"
    @keydown.esc.stop="model = false"
  >
    <RuiCard data-cy="missing-rules-dialog">
      <template #header>
        <span
          class="text-h5"
          data-cy="dialog-title"
        >
          {{ t('actions.history_events.missing_rule.title') }}
        </span>
      </template>

      <p class="text-body-1 text-rui-text-secondary">
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
          @click="model = false"
        >
          {{ t('common.actions.ok') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
