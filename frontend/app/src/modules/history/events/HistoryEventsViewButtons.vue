<script setup lang="ts">
import type { HistoryRefreshEventData } from '@/modules/history/refresh/types';
import HistoryEventsActionsCenter from '@/modules/history/events/actions-center/HistoryEventsActionsCenter.vue';
import { DIALOG_TYPES, type DialogShowOptions } from '@/modules/history/events/dialog-types';
import HistoryRefreshButton from '@/modules/history/refresh/HistoryRefreshButton.vue';

defineProps<{
  processing: boolean;
  loading: boolean;
  includeEvmEvents: boolean;
}>();

const emit = defineEmits<{
  'refresh': [payload?: HistoryRefreshEventData];
  'show:dialog': [options: DialogShowOptions];
}>();

const { t } = useI18n({ useScope: 'global' });

const menuOpen = ref<boolean>(false);
</script>

<template>
  <HistoryEventsActionsCenter @show:dialog="emit('show:dialog', $event)" />

  <HistoryRefreshButton
    :processing="processing"
    @refresh="emit('refresh', $event)"
  />

  <RuiButton
    color="primary"
    size="lg"
    class="[&>span]:!hidden lg:[&>span]:!inline"
    data-testid="history-events-add"
    @click="emit('show:dialog', { type: DIALOG_TYPES.EVENT_FORM, data: { type: 'add', nextSequenceId: '0' } })"
  >
    <template #prepend>
      <RuiIcon name="lu-plus" />
    </template>
    {{ t('transactions.actions.add_event') }}
  </RuiButton>

  <RuiMenu
    v-model="menuOpen"
    :options="{ placement: 'bottom-end' }"
    :class-names="{ menu: 'max-w-[24rem]' }"
    close-on-content-click
  >
    <template #activator="{ attrs }">
      <RuiBadge
        :model-value="loading"
        color="primary"
        dot
        placement="top"
        offset-y="12"
        offset-x="-12"
      >
        <RuiButton
          variant="text"
          icon
          size="lg"
          v-bind="attrs"
        >
          <RuiIcon name="lu-ellipsis-vertical" />
        </RuiButton>
      </RuiBadge>
    </template>

    <template v-if="includeEvmEvents">
      <RuiButton
        variant="list"
        @click="emit('show:dialog', { type: DIALOG_TYPES.DECODING_STATUS })"
      >
        <template #prepend>
          <RuiBadge
            :model-value="loading"
            color="primary"
            dot
            placement="top"
            offset-y="4"
            offset-x="-4"
          >
            <RuiIcon name="lu-scroll-text" />
          </RuiBadge>
        </template>

        {{ t('transactions.events_decoding.title') }}
      </RuiButton>
    </template>

    <RuiButton
      variant="list"
      data-testid="history-events-add-by-tx-hash"
      :disabled="loading"
      @click="emit('show:dialog', { type: DIALOG_TYPES.ADD_TRANSACTION })"
    >
      <template #prepend>
        <RuiIcon name="lu-plus" />
      </template>
      {{ t('transactions.dialog.add_tx') }}
    </RuiButton>

    <RuiButton
      variant="list"
      data-testid="history-events-repulling-transactions"
      :disabled="loading"
      @click="emit('show:dialog', { type: DIALOG_TYPES.REPULLING_TRANSACTION })"
    >
      <template #prepend>
        <RuiIcon name="lu-clock-arrow-up" />
      </template>
      {{ t('transactions.repulling.action') }}
    </RuiButton>
  </RuiMenu>
</template>
