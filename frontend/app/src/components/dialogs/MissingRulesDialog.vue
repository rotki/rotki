<script setup lang="ts">
import {
  type EvmChainAndTxHash,
  type HistoryEventEntry
} from '@/types/history/events';
import { toEvmChainAndTxHash } from '@/utils/history';

const props = withDefaults(
  defineProps<{
    value: boolean;
    event: HistoryEventEntry | null;
  }>(),
  {
    event: null,
    value: false
  }
);

const emit = defineEmits<{
  (e: 're-decode', event: EvmChainAndTxHash | null): void;
  (e: 'edit', event: HistoryEventEntry | null): void;
  (e: 'add-rule'): void;
  (e: 'input', value: boolean): void;
}>();

const { t } = useI18n();

const { event } = toRefs(props);

const isEvm = computed(() => {
  const entry = get(event);

  if (!entry) {
    return false;
  }

  return isEvmEvent(entry);
});

const onRedecode = () => {
  const entry = get(event);

  if (!entry) {
    return false;
  }

  emit('re-decode', toEvmChainAndTxHash(entry));
  emit('input', false);
};
</script>

<template>
  <VDialogTransition>
    <VDialog
      :value="value"
      :max-width="500"
      @keydown.esc.stop="emit('input', false)"
      @input="emit('input', false)"
    >
      <RuiCard data-cy="missing-rules-dialog">
        <template #header>
          <span class="text-h5" data-cy="dialog-title">
            {{ t('actions.history_events.missing_rule.title') }}
          </span>
        </template>

        <p class="text-body-1">
          {{ t('actions.history_events.missing_rule.message') }}
        </p>

        <div class="flex flex-col items-start gap-3">
          <RuiButton v-if="isEvm" variant="text" @click="onRedecode()">
            <template #prepend>
              <RuiIcon color="info" name="restart-line" />
            </template>
            {{ t('actions.history_events.missing_rule.re_decode') }}
          </RuiButton>
          <RuiButton v-else variant="text" @click="emit('edit', event)">
            <template #prepend>
              <RuiIcon color="info" name="pencil-line" />
            </template>
            {{ t('actions.history_events.missing_rule.edit') }}
          </RuiButton>
          <RuiButton variant="text" @click="emit('add-rule')">
            <template #prepend>
              <RuiIcon color="info" name="add-line" />
            </template>
            {{ t('actions.history_events.missing_rule.add_rule') }}
          </RuiButton>
        </div>

        <template #footer>
          <div class="grow" />
          <RuiButton
            color="primary"
            data-cy="button-ok"
            @click="emit('input', false)"
          >
            {{ t('common.actions.ok') }}
          </RuiButton>
        </template>
      </RuiCard>
    </VDialog>
  </VDialogTransition>
</template>
