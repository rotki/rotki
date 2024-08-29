<script setup lang="ts">
import type { EvmChainAndTxHash, ShowEventForm } from '@/types/history/events';

defineProps<{
  processing: boolean;
  loading: boolean;
  includeEvmEvents: boolean;
}>();

const emit = defineEmits<{
  'refresh': [];
  'reload': [payload: EvmChainAndTxHash];
  'show:form': [payload: ShowEventForm];
}>();

const openDecodingDialog = defineModel<boolean>('openDecodingDialog', { required: true });

const { t } = useI18n();

const { setOpenDialog: setTxFormOpenDialog, setPostSubmitFunc: setTxFormPostSubmitFunc } = useHistoryTransactionsForm();

setTxFormPostSubmitFunc((payload) => {
  if (payload)
    emit('reload', payload);
});

function addTransactionHash(): void {
  setTxFormOpenDialog(true);
}
</script>

<template>
  <RuiTooltip :open-delay="400">
    <template #activator>
      <RuiButton
        :disabled="processing"
        variant="outlined"
        color="primary"
        @click="emit('refresh')"
      >
        <template #prepend>
          <RuiIcon name="refresh-line" />
        </template>
        {{ t('common.refresh') }}
      </RuiButton>
    </template>
    {{ t('transactions.refresh_tooltip') }}
  </RuiTooltip>

  <RuiButton
    color="primary"
    data-cy="history-events__add"
    @click="emit('show:form', { type: 'event', data: { nextSequenceId: '0' } })"
  >
    <template #prepend>
      <RuiIcon name="add-line" />
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
          <RuiIcon name="more-2-fill" />
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
              <RuiIcon name="file-info-line" />
            </RuiBadge>
          </template>

          {{ t('transactions.events_decoding.title') }}
        </RuiButton>
      </template>

      <RuiButton
        variant="list"
        data-cy="history-events__add_by_tx_hash"
        :disabled="loading"
        @click="addTransactionHash()"
      >
        <template #prepend>
          <RuiIcon name="add-line" />
        </template>
        {{ t('transactions.dialog.add_tx') }}
      </RuiButton>
    </div>
  </RuiMenu>
</template>
