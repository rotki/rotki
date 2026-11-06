<script setup lang="ts">
import type { HistoryRefreshEventData } from '@/modules/history/refresh/types';
import HistoryRefreshSelection from '@/modules/history/refresh/HistoryRefreshSelection.vue';

defineProps<{
  processing: boolean;
}>();

const emit = defineEmits<{
  refresh: [payload?: HistoryRefreshEventData];
  repull: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiButtonGroup
    variant="outlined"
    color="primary"
    :class="{ 'outline-rui-text-disabled! between:border-rui-text-disabled!': processing }"
  >
    <RuiTooltip :open-delay="400">
      <template #activator>
        <RuiButton
          :disabled="processing"
          variant="outlined"
          color="primary"
          class="[&>span]:hidden! lg:[&>span]:inline!"
          :aria-label="t('common.refresh')"
          data-testid="history-refresh-all"
          @click="emit('refresh')"
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
      @repull="emit('repull')"
    />
  </RuiButtonGroup>
</template>
