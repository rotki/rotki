<script setup lang="ts">
import type { Account } from '@rotki/common';
import HistoryRefreshChainSelection from '@/modules/history/refresh/HistoryRefreshChainSelection.vue';

defineProps<{
  processing: boolean;
}>();

const emit = defineEmits<{ refresh: [] | [Account[]] }>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiButtonGroup
    variant="outlined"
    color="primary"
  >
    <RuiTooltip :open-delay="400">
      <template #activator>
        <RuiButton
          :disabled="processing"
          variant="outlined"
          color="primary"
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

    <HistoryRefreshChainSelection @refresh="emit('refresh', $event)" />
  </RuiButtonGroup>
</template>
