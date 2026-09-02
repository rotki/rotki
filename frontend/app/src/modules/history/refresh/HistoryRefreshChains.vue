<script lang="ts" setup>
import type { ChainAddress } from '@/modules/history/events/event-payloads';
import HistoryRefreshAddressSelection from '@/modules/history/refresh/HistoryRefreshAddressSelection.vue';
import HistoryRefreshChainItem from '@/modules/history/refresh/HistoryRefreshChainItem.vue';
import { useHistoryRefreshChainSelection } from '@/modules/history/refresh/use-history-refresh-chain-selection';

const modelValue = defineModel<ChainAddress[]>({ required: true });
const selectedChain = defineModel<string | undefined>('chain', { required: true });
const search = defineModel<string>('search', { required: true });

defineProps<{
  processing: boolean;
}>();

const emit = defineEmits<{ 'update:all-selected': [allSelected: boolean] }>();

const { t } = useI18n({ useScope: 'global' });

const {
  chainAddresses,
  filtered,
  modelSelection: selection,
  toggleSelectAll,
} = useHistoryRefreshChainSelection({
  chain: selectedChain,
  modelValue,
  onAllSelected: allSelected => emit('update:all-selected', allSelected),
  search,
});

defineExpose({
  toggleSelectAll,
});
</script>

<template>
  <div v-if="selectedChain">
    <RuiButton
      size="sm"
      variant="list"
      @click.prevent="selectedChain = undefined"
    >
      <template #prepend>
        <RuiIcon
          size="16"
          name="lu-arrow-left"
        />
      </template>
      {{ t('history_refresh_selection.back_to_chain') }}
    </RuiButton>
  </div>
  <div class="h-[220px] overflow-y-auto">
    <template v-if="!selectedChain">
      <HistoryRefreshChainItem
        v-for="item in filtered"
        :key="item.id"
        v-model="selection[item.chain]"
        :processing="processing"
        :item="item"
        :addresses="chainAddresses[item.chain]"
        @pick-addresses="selectedChain = $event"
      />
    </template>
    <template v-else>
      <HistoryRefreshAddressSelection
        v-model="selection[selectedChain]"
        :search="search"
        :chain="selectedChain"
        :processing="processing"
        :addresses="chainAddresses[selectedChain]"
      />
    </template>
  </div>
</template>
