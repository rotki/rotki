<script setup lang="ts">
import type { ShowEventForm } from '@/modules/history/management/forms/form-types';
import type { HistoryRefreshEventData } from '@/modules/history/refresh/types';
import HistoryRefreshButton from '@/modules/history/refresh/HistoryRefreshButton.vue';

const openDecodingDialog = defineModel<boolean>('openDecodingDialog', { required: true });

defineProps<{
  processing: boolean;
  loading: boolean;
  includeEvmEvents: boolean;
}>();

const emit = defineEmits<{
  'refresh': [payload?: HistoryRefreshEventData];
  'show:form': [payload: ShowEventForm];
  'show:add-transaction-form': [];
  'show:repulling-transactions-form': [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <HistoryRefreshButton
    :processing="processing"
    @refresh="emit('refresh', $event)"
  />

  <RuiButton
    color="primary"
    data-cy="history-events__add"
    @click="emit('show:form', { type: 'event', data: { type: 'add', nextSequenceId: '0' } })"
  >
    <template #prepend>
      <RuiIcon name="lu-plus" />
    </template>
    {{ t('transactions.actions.add_event') }}
  </RuiButton>

  <RuiMenu
    :popper="{ placement: 'bottom-end' }"
    menu-class="max-w-[24rem]"
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
          size="sm"
          class="!p-2"
          v-bind="attrs"
        >
          <RuiIcon name="lu-ellipsis-vertical" />
        </RuiButton>
      </RuiBadge>
    </template>

    <div class="py-2">
      <template v-if="includeEvmEvents">
        <RuiButton
          variant="list"
          @click="openDecodingDialog = true"
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
        data-cy="history-events__add_by_tx_hash"
        :disabled="loading"
        @click="emit('show:add-transaction-form')"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('transactions.dialog.add_tx') }}
      </RuiButton>

      <RuiButton
        variant="list"
        data-cy="history-events__repulling-transactions"
        :disabled="loading"
        @click="emit('show:repulling-transactions-form')"
      >
        <template #prepend>
          <RuiIcon name="lu-clock-arrow-up" />
        </template>
        {{ t('transactions.repulling.title') }}
      </RuiButton>
    </div>
  </RuiMenu>
</template>
