<script setup lang="ts">
import type { EvmChainInfo } from '@/types/api/chains';
import { useSupportedChains } from '@/composables/info/chains';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import HistoryRefreshChainItem from '@/modules/history/refresh/HistoryRefreshChainItem.vue';
import { type Account, getTextToken } from '@rotki/common';

defineProps<{
  processing: boolean;
}>();

const emit = defineEmits<{ refresh: [] | [Account[]] }>();

const open = ref<boolean>(false);
const search = ref<string>('');
const selection = ref<Account[]>([]);

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
    acc[item.id] = getAddresses(item.id);
    return acc;
  }, record);
});

const allSelected = computed<boolean>(() => {
  const allAddresses = Object.entries(get(chainAddresses)).flatMap(([chain, addresses]) => addresses.map(address => ({
    address,
    chain,
  }) satisfies Account));
  return get(selection).every(item => allAddresses.includes(item));
});

function toggleSelectAll() {

}

function reset() {

}

function refresh() {
  emit('refresh', []);
}
</script>

<template>
  <RuiMenu
    v-model="open"
    :popper="{ placement: 'bottom', offsetSkid: 35 }"
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="outlined"
        class="px-3 py-3 !outline-none rounded-none"
        v-bind="attrs"
      >
        <RuiIcon
          name="lu-chevrons-up-down"
          color="primary"
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
          :label="t('account_balances.detect_tokens.selection.type')"
          prepend-icon="lu-search"
          hide-details
          clearable
        />
      </div>
      <div class="px-4 py-2 text-xs font-medium uppercase border-b border-default bg-rui-grey-50 dark:bg-rui-grey-900">
        {{ t('account_balances.detect_tokens.selection.select') }}
      </div>
      <div class="h-[220px] overflow-y-auto">
        <div
          v-for="item in filtered"
          :key="item.id"
          class="flex items-center px-4 py-1 pr-2 cursor-pointer hover:bg-rui-grey-100 hover:dark:bg-rui-grey-900 transition"
        >
          <HistoryRefreshChainItem
            :item="item"
            :addresses="chainAddresses[item.id]"
          />
        </div>
      </div>
      <div class="px-4 py-2 border-t border-default flex items-center justify-between">
        <RuiCheckbox
          color="primary"
          :disabled="processing"
          :indeterminate="selection.length > 0 && !allSelected"
          :model-value="selection.length > 0 && allSelected"
          size="sm"
          hide-details
          @click.prevent="toggleSelectAll()"
        >
          {{ t('account_balances.detect_tokens.selection.select_all') }}
        </RuiCheckbox>
        <div class="flex items-center gap-2">
          <RuiButton
            v-if="selection.length > 0"
            variant="text"
            @click="reset()"
          >
            {{ t('common.actions.cancel') }}
          </RuiButton>
          <RuiButton
            color="primary"
            :disabled="selection.length === 0"
            :loading="processing"
            @click="refresh()"
          >
            {{
              t('history_refresh_chain_selection.refresh', {
                accounts: selection.length,
              })
            }}
          </RuiButton>
        </div>
      </div>
    </div>
  </RuiMenu>
</template>
