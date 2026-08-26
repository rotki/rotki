<script setup lang="ts">
import type { ChainInfo } from '@/modules/core/api/types/chains';
import type { DecodeScope } from '@/modules/history/events/event-payloads';
import { getTextToken } from '@rotki/common';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import HistoryRedecodeChainItem from '@/modules/history/redecode/HistoryRedecodeChainItem.vue';

const {
  loading,
  disabled = false,
  showRedecodePage = false,
} = defineProps<{
  loading: boolean;
  disabled?: boolean;
  showRedecodePage?: boolean;
}>();

const emit = defineEmits<{
  redecode: [scope: DecodeScope];
}>();

const open = ref<boolean>(false);
const search = ref<string>('');
const selection = ref<string[]>([]);

const { t } = useI18n({ useScope: 'global' });
// Every chain that can be redecoded, not just the EVM ones. The consumer decides whether a request
// is the full run by comparing the selection against `decodableTxChainsInfo`, so offering a
// narrower list here meant selecting everything still read as a partial run: it never took the
// canonical `redecode:all` id and so never deduped against the Redecode All button.
const { decodableTxChainsInfo } = useSupportedChains();

const filteredChains = computed<ChainInfo[]>(() => {
  const query = getTextToken(get(search));
  return get(decodableTxChainsInfo).filter(chain =>
    getTextToken(chain.name).includes(query)
    // Narrowed with `in` rather than on `type`: the fallback chain variant types `type` as a plain
    // string, so comparing it to 'evm' excludes nothing.
    || ('evmChainName' in chain && getTextToken(chain.evmChainName).includes(query)),
  );
});

const indeterminate = computed<boolean>(() => {
  const selectedItems = get(selection).length;
  return selectedItems > 0 && selectedItems < get(decodableTxChainsInfo).length;
});

const selected = computed<boolean>(() => {
  const selectedItems = get(selection).length;
  return selectedItems > 0 && selectedItems === get(decodableTxChainsInfo).length;
});

function toggleSelection(chain: string, selected: boolean): void {
  if (selected) {
    set(selection, [...get(selection), chain]);
  }
  else {
    set(selection, get(selection).filter(c => c !== chain));
  }
}

function toggleSelectAll() {
  if (get(selection).length > 0) {
    set(selection, []);
  }
  else {
    set(selection, get(decodableTxChainsInfo).map(chain => chain.id));
  }
}

function reset() {
  set(open, false);
  set(selection, []);
  set(search, '');
}

function redecode() {
  emit('redecode', { chains: get(selection), type: 'chains' });
  reset();
}
</script>

<template>
  <RuiMenu
    v-model="open"
    class="!border-0"
    :popper="{ placement: 'bottom', offsetSkid: 35 }"
  >
    <template #activator="{ attrs }">
      <RuiButton
        color="primary"
        class="px-3 py-3 rounded-l-none -ml-[1px] border-l border-rui-primary-darker disabled:border-rui-grey-200 disabled:dark:border-rui-grey-800"
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
          :label="t('history_redecode_selection.search_chain')"
          prepend-icon="lu-search"
          hide-details
          clearable
        />
      </div>
    </div>

    <div class="px-4 py-2 text-xs font-medium uppercase border-b border-default bg-rui-grey-50 dark:bg-rui-grey-900">
      {{ t('history_redecode_selection.selection') }}
    </div>

    <div class="h-[220px] overflow-y-auto">
      <HistoryRedecodeChainItem
        v-for="chain in filteredChains"
        :key="chain.id"
        :model-value="selection.includes(chain.id)"
        :disabled="disabled"
        :chain="chain.id"
        @update:model-value="toggleSelection(chain.id, $event)"
      />
    </div>

    <div class="px-4 py-2 border-t border-default flex items-center justify-between">
      <RuiCheckbox
        color="primary"
        :disabled="disabled"
        :indeterminate="indeterminate"
        :model-value="selected"
        size="sm"
        hide-details
        @click.prevent="toggleSelectAll()"
      >
        {{ t('common.actions.select_all') }}
      </RuiCheckbox>
      <div class="flex items-center gap-2">
        <RuiButton
          v-if="indeterminate || selected"
          variant="text"
          @click="reset()"
        >
          {{ t('common.actions.cancel') }}
        </RuiButton>
        <RuiButton
          color="primary"
          :disabled="!(indeterminate || selected)"
          :loading="loading"
          @click="redecode()"
        >
          {{ t('history_redecode_selection.redecode', { total: selection.length }, selection.length) }}
        </RuiButton>
      </div>
    </div>

    <div
      v-if="showRedecodePage"
      class="px-4 py-2 border-t border-default"
    >
      <RuiButton
        variant="text"
        size="sm"
        class="w-full !justify-start"
        @click="emit('redecode', { type: 'page' }); reset()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-file-text"
            size="16"
          />
        </template>
        {{ t('transactions.actions.redecode_page') }}
      </RuiButton>
    </div>
  </RuiMenu>
</template>
