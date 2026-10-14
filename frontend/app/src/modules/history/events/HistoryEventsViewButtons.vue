<script setup lang="ts">
import type { DecodeScope } from '@/modules/history/events/event-payloads';
import type { HistoryRefreshEventData } from '@/modules/history/refresh/types';
import { DIALOG_TYPES, type DialogShowOptions } from '@/modules/history/events/dialog-types';
import HistoryRedecodeButton from '@/modules/history/redecode/HistoryRedecodeButton.vue';
import HistoryRefreshButton from '@/modules/history/refresh/HistoryRefreshButton.vue';

defineProps<{
  processing: boolean;
  loading: boolean;
}>();

const emit = defineEmits<{
  'redecode': [scope: DecodeScope];
  'refresh': [payload?: HistoryRefreshEventData];
  'show:dialog': [options: DialogShowOptions];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <HistoryRefreshButton
    :processing="processing"
    @refresh="emit('refresh', $event)"
    @repull="emit('show:dialog', { type: DIALOG_TYPES.REPULLING_TRANSACTION })"
  />

  <HistoryRedecodeButton
    :processing="processing"
    @redecode="emit('redecode', $event)"
  />

  <RuiButtonGroup color="primary">
    <RuiButton
      color="primary"
      class="rounded-r-none [&>span]:hidden! lg:[&>span]:inline!"
      data-testid="history-events-add"
      @click="emit('show:dialog', { type: DIALOG_TYPES.EVENT_FORM, data: { type: 'add', nextSequenceId: '0' } })"
    >
      <template #prepend>
        <RuiIcon name="lu-plus" />
      </template>
      {{ t('transactions.actions.add_event') }}
    </RuiButton>
    <RuiMenu
      :options="{ placement: 'bottom-end' }"
      close-on-content-click
    >
      <template #activator="{ attrs }">
        <RuiButton
          color="primary"
          class="h-9 px-2.5 rounded-l-none border-l border-rui-primary-darker"
          :aria-label="t('common.actions.more')"
          data-testid="history-events-add-menu"
          v-bind="attrs"
        >
          <RuiIcon
            name="lu-chevron-down"
            size="16"
          />
        </RuiButton>
      </template>
      <RuiButton
        variant="list"
        data-testid="history-events-add-by-tx-hash"
        :disabled="loading"
        @click="emit('show:dialog', { type: DIALOG_TYPES.ADD_TRANSACTION })"
      >
        <template #prepend>
          <RuiIcon name="lu-hash" />
        </template>
        {{ t('transactions.dialog.add_tx') }}
      </RuiButton>
    </RuiMenu>
  </RuiButtonGroup>
</template>
