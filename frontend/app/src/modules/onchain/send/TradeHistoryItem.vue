<script setup lang="ts">
import type { RecentTransaction } from '@/modules/onchain/types';
import DateDisplay from '@/components/display/DateDisplay.vue';
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import HistoryEventNote from '@/components/history/events/HistoryEventNote.vue';
import HashLink from '@/modules/common/links/HashLink.vue';

const props = defineProps<{
  item: RecentTransaction;
}>();

const color = computed<'error' | 'success' | 'warning'>(() => {
  const status = props.item.status;
  if (status === 'completed') {
    return 'success';
  }
  if (status === 'pending') {
    return 'warning';
  }
  return 'error';
});
const dot = '•';
</script>

<template>
  <div class="flex items-center gap-2 py-4 px-4 border-t border-default">
    <ChainIcon
      size="28px"
      :chain="item.chain"
    />
    <div class="flex-1">
      <div class="flex items-start justify-between text-rui-text-secondary text-sm">
        <div class="flex items-center gap-2 pb-1.5">
          <DateDisplay
            class="!text-xs"
            :timestamp="item.timestamp"
            milliseconds
          />
          {{ dot }}
          <HashLink
            class="text-rui-primary underline cursor-pointer !pl-0"
            :text="item.hash"
            :location="item.chain"
            type="transaction"
          />
        </div>
        <RuiChip
          size="sm"
          :color="color"
          class="[&_span]:!text-[9px] leading-3 uppercase !p-0.5"
        >
          {{ item.status }}
        </RuiChip>
      </div>
      <div class="text-sm">
        <HistoryEventNote
          class="text-sm inline-flex flex-wrap whitespace-break-spaces items-center [&_.shrink]:!text-xs"
          :notes="item.context"
          :chain="item.chain"
          v-bind="item.metadata"
        />
      </div>
    </div>
  </div>
</template>
