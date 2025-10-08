<script lang="ts" setup>
import type { ChainData } from '@/modules/history/refresh/types';
import { getTextToken } from '@rotki/common';
import { cloneDeep, isEqual } from 'es-toolkit';
import { useSupportedChains } from '@/composables/info/chains';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import HistoryRefreshAddressSelection from '@/modules/history/refresh/HistoryRefreshAddressSelection.vue';
import HistoryRefreshChainItem from '@/modules/history/refresh/HistoryRefreshChainItem.vue';
import {
  type ChainAddress,
  TransactionChainType,
} from '@/types/history/events';

const modelValue = defineModel<ChainAddress[]>({ required: true });
const selectedChain = defineModel<string | undefined>('chain', { required: true });
const search = defineModel<string>('search', { required: true });

defineProps<{
  processing: boolean;
}>();

const emit = defineEmits<{ 'update:all-selected': [allSelected: boolean] }>();

const selection = ref<Record<string, string[]>>({});

const { bitcoinChainsData, evmLikeChainsData, txEvmChains } = useSupportedChains();
const { getAddresses } = useAccountAddresses();
const { t } = useI18n({ useScope: 'global' });

const refreshChains = computed<ChainData[]>(() => [
  ...get(txEvmChains).map(item => ({
    chain: item.id,
    id: item.id,
    name: item.name,
    type: TransactionChainType.EVM,
  })),
  ...get(evmLikeChainsData).map(item => ({
    chain: item.id,
    id: item.id,
    name: item.name,
    type: TransactionChainType.EVMLIKE,
  })),
  ...get(bitcoinChainsData).map(item => ({
    chain: item.id,
    id: item.id,
    name: item.name,
    type: TransactionChainType.BITCOIN,
  })),
]);

const filtered = computed<ChainData[]>(() => {
  const chains = get(refreshChains).filter(item => getAddresses(item.id)?.length > 0);
  const query = getTextToken(get(search));
  if (!query)
    return chains;

  return chains.filter(item => getTextToken(item.chain).includes(query) || getTextToken(item.name).includes(query));
});

const chainAddresses = computed<Record<string, string[]>>(() => {
  const chains = [...get(refreshChains)];
  const record: Record<string, string[]> = {};
  return chains.reduce((acc, item) => {
    acc[item.chain] = getAddresses(item.id) ?? [];
    return acc;
  }, record);
});

const selected = computed<number>(() => getAccounts(get(selection)).length);

function getAccounts(record: Record<string, string[]>): ChainAddress[] {
  return Object.entries(record).flatMap(([chainKey, addresses]) => addresses.map((address): ChainAddress => ({
    address,
    chain: chainKey,
  })));
}

function emptySelection(): Record<string, string[]> {
  return Object.fromEntries(get(refreshChains).map(item => [item.chain, []]));
}

function toggleSelectAll() {
  if (isDefined(selectedChain)) {
    toggleSpecificChain(get(selectedChain));
  }
  else {
    toggleAllChains();
  }
}

function toggleSpecificChain(chain: string) {
  const currentSelection = get(selection);
  if (currentSelection[chain].length === 0) {
    updateSelection({
      ...currentSelection,
      [chain]: get(chainAddresses)[chain],
    });
  }
  else {
    updateSelection({
      ...currentSelection,
      [chain]: [],
    });
  }
}

function toggleAllChains() {
  if (get(selected) === 0) {
    updateSelection(cloneDeep(get(chainAddresses)));
  }
  else {
    updateSelection(emptySelection());
  }
}

function updateAllSelected() {
  if (isDefined(selectedChain)) {
    const selected = get(selection);
    const evmChain = get(selectedChain);
    emit('update:all-selected', isEqual(get(chainAddresses)[evmChain], selected[evmChain]));
  }
  else {
    const all = getAccounts(get(chainAddresses));
    const selected = getAccounts(get(selection));
    emit('update:all-selected', isEqual(all, selected));
  }
}

function updateSelection(newSelection: Record<string, string[]>) {
  set(selection, newSelection);
  set(modelValue, getAccounts(newSelection));
  updateAllSelected();
}

watch(selectedChain, () => {
  set(search, '');
  updateAllSelected();
});

watch(selection, (newSelection) => {
  set(modelValue, getAccounts(newSelection));
  updateAllSelected();
}, {
  deep: true,
});

onBeforeMount(() => {
  updateSelection(emptySelection());
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
