<script setup lang="ts">
import type { RecentTransaction } from '@/modules/wallet/types';
import HistoryEventNote from '@/modules/history/events/HistoryEventNote.vue';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';
import TimeAgoDisplay from '@/modules/shell/components/display/TimeAgoDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';

const { item } = defineProps<{
  item: RecentTransaction;
}>();

const { t } = useI18n({ useScope: 'global' });

const color = computed<'error' | 'success' | 'warning'>(() => {
  const status = item.status;
  if (status === 'completed') {
    return 'success';
  }
  if (status === 'pending') {
    return 'warning';
  }
  return 'error';
});

/** The status in words, the same ones the dialog's tabs use, rather than the raw value. */
const statusLabel = computed<string>(() => {
  const status = item.status;
  if (status === 'completed')
    return t('trade_history_view.labels.completed');
  if (status === 'pending')
    return t('trade_history_view.labels.pending');
  return t('trade_history_view.labels.failed');
});
</script>

<template>
  <div class="flex items-start gap-3 py-3 px-4">
    <ChainIcon
      size="24px"
      :chain="item.chain"
      class="shrink-0 mt-0.5"
    />
    <div class="flex-1 min-w-0 flex flex-col gap-1">
      <HistoryEventNote
        class="text-sm text-rui-text! leading-6"
        :notes="item.context"
        :chain="item.chain"
        :context="item.metadata"
      />
      <div class="flex items-center gap-1.5 min-w-0 text-xs text-rui-text-secondary">
        <TimeAgoDisplay
          :timestamp="item.timestamp"
          milliseconds
        />
        <span class="text-rui-text-disabled before:content-['·']" />
        <HashLink
          class="pl-0!"
          :text="item.hash"
          :location="item.chain"
          type="transaction"
        />
      </div>
    </div>
    <RuiChip
      size="sm"
      variant="tonal"
      :color="color"
      class="shrink-0 mt-0.5"
      data-testid="trade-history-status"
    >
      {{ statusLabel }}
    </RuiChip>
  </div>
</template>
