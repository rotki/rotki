<script setup lang="ts">
import type { EvmChainInfo } from '@/types/api/chains';
import type { EvmChainAddress } from '@/types/history/events';
import { useSupportedChains } from '@/composables/info/chains';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import HistoryRefreshAddressSelection from '@/modules/history/refresh/HistoryRefreshAddressSelection.vue';
import HistoryRefreshChainItem from '@/modules/history/refresh/HistoryRefreshChainItem.vue';
import { getTextToken } from '@rotki/common';
import { cloneDeep, isEqual } from 'es-toolkit';
import { isEmpty } from 'es-toolkit/compat';

withDefaults(defineProps<{
  processing: boolean;
  disabled?: boolean;
}>(), {
  disabled: false,
});

const emit = defineEmits<{ refresh: [accounts?: EvmChainAddress[]] }>();

const open = ref<boolean>(false);
const search = ref<string>('');
const selection = ref<Record<string, string[]>>({});
const selectedChain = ref<string>();

const { txEvmChains } = useSupportedChains();
const { getAddresses } = useAccountAddresses();
const { t } = useI18n({ useScope: 'global' });

const filtered = computed<EvmChainInfo[]>(() => {
  const chains = [...get(txEvmChains)];
  const query = getTextToken(get(search));
  if (!query)
    return chains;

  return chains.filter(item => getTextToken(item.evmChainName).includes(query) || getTextToken(item.name).includes(query));
});

const chainAddresses = computed<Record<string, string[]>>(() => {
  const chains = [...get(txEvmChains)];
  const record: Record<string, string[]> = {};
  return chains.reduce((acc, item) => {
    acc[item.evmChainName] = getAddresses(item.id) ?? [];
    return acc;
  }, record);
});

const allSelected = computed<boolean>(() => {
  if (isDefined(selectedChain)) {
    const selected = get(selection);
    const evmChain = get(selectedChain);
    return isEqual(get(chainAddresses)[evmChain], selected[evmChain]);
  }

  const all = getAccounts(get(chainAddresses));
  const selected = getAccounts(get(selection));
  return isEqual(all, selected);
});

const selected = computed<number>(() => getAccounts(get(selection)).length);

function getAccounts(record: Record<string, string[]>): EvmChainAddress[] {
  return Object.entries(record).flatMap(([evmChain, addresses]) => addresses.map(address => ({
    address,
    evmChain,
  }) satisfies EvmChainAddress));
}

function emptySelection(): Record<string, string[]> {
  return Object.fromEntries(get(txEvmChains).map(item => [item.evmChainName, []]));
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
    set(selection, {
      ...currentSelection,
      [chain]: get(chainAddresses)[chain],
    });
  }
  else {
    set(selection, {
      ...currentSelection,
      [chain]: [],
    });
  }
}

function toggleAllChains() {
  if (get(selected) === 0) {
    set(selection, cloneDeep(get(chainAddresses)));
  }
  else {
    set(selection, emptySelection());
  }
}

function reset() {
  set(selection, emptySelection());
}

function refresh() {
  emit('refresh', getAccounts(get(selection)));
  reset();
  set(open, false);
}

watch(selectedChain, () => {
  set(search, '');
});

onMounted(() => {
  reset();
});
</script>

<template>
  <RuiMenu
    v-model="open"
    class="!border-0"
    :popper="{ placement: 'bottom', offsetSkid: 35 }"
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="outlined"
        color="primary"
        class="px-3 py-3 rounded-l-none -ml-[1px]"
        :disabled="disabled"
        v-bind="attrs"
      >
        <RuiIcon
          name="lu-chevrons-up-down"
          class="size-4"
        />
      </RuiButton>
    </template>

    <div class="w-[450px]">
      <div class="p-4 border-b border-default">
        <RuiTextField
          v-model="search"
          dense
          color="primary"
          variant="outlined"
          :label="selectedChain ? t('history_refresh_chain_selection.search_address') : t('history_refresh_chain_selection.search_chain')"
          prepend-icon="lu-search"
          hide-details
          clearable
        />
      </div>
      <div class="px-4 py-2 text-xs font-medium uppercase border-b border-default bg-rui-grey-50 dark:bg-rui-grey-900">
        {{ t('history_refresh_chain_selection.selection') }}
      </div>
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
          {{ t('history_refresh_chain_selection.back_to_chain') }}
        </RuiButton>
      </div>
      <div class="h-[220px] overflow-y-auto">
        <template v-if="!selectedChain">
          <HistoryRefreshChainItem
            v-for="item in filtered"
            :key="item.id"
            v-model="selection[item.evmChainName]"
            :processing="processing"
            :item="item"
            :addresses="chainAddresses[item.evmChainName]"
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
      <div class="px-4 py-2 border-t border-default flex items-center justify-between">
        <RuiCheckbox
          color="primary"
          :disabled="processing"
          :indeterminate="selected !== 0 && !allSelected"
          :model-value="selected !== 0 && allSelected"
          size="sm"
          hide-details
          @click.prevent="toggleSelectAll()"
        >
          {{ t('common.actions.select_all') }}
        </RuiCheckbox>
        <div class="flex items-center gap-2">
          <RuiButton
            v-if="!isEmpty(selection)"
            variant="text"
            @click="reset()"
          >
            {{ t('common.actions.cancel') }}
          </RuiButton>
          <RuiButton
            color="primary"
            :disabled="isEmpty(selection)"
            :loading="processing"
            @click="refresh()"
          >
            {{ t('history_refresh_chain_selection.refresh', { accounts: selected }) }}
          </RuiButton>
        </div>
      </div>
    </div>
  </RuiMenu>
</template>
