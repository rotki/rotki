<script setup lang="ts">
import type { HistoryRefreshEventData } from '@/modules/history/refresh/types';
import HistoryRefreshSelection from '@/modules/history/refresh/HistoryRefreshSelection.vue';
import { useConfirmStore } from '@/store/confirm';

defineProps<{
  processing: boolean;
}>();

const emit = defineEmits<{ refresh: [payload?: HistoryRefreshEventData] }>();

const { t } = useI18n({ useScope: 'global' });

const { show } = useConfirmStore();

function confirmRefresh() {
  show({
    message: t('history_refresh_button.confirm_refresh.message'),
    title: t('history_refresh_button.confirm_refresh.title'),
  }, () => {
    emit('refresh');
  });
}
</script>

<template>
  <RuiButtonGroup
    variant="outlined"
    color="primary"
    class="h-9"
    :class="{ '!outline-rui-text-disabled': processing }"
  >
    <RuiTooltip :open-delay="400">
      <template #activator>
        <RuiButton
          :disabled="processing"
          variant="outlined"
          color="primary"
          class="rounded-r-none !outline-none border-r border-rui-primary/[0.5] disabled:!border-rui-text-disabled"
          @click="confirmRefresh()"
        >
          <template #prepend>
            <RuiIcon name="lu-refresh-ccw" />
          </template>
          {{ t('common.refresh') }}
        </RuiButton>
      </template>

      {{ t('transactions.refresh_tooltip') }}
    </RuiTooltip>

    <HistoryRefreshSelection
      :processing="processing"
      :disabled="processing"
      @refresh="emit('refresh', $event)"
    />
  </RuiButtonGroup>
</template>
