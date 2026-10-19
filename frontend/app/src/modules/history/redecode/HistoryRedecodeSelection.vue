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
const { allTxChainsInfo } = useSupportedChains();

const filteredChains = computed<ChainInfo[]>(() => {
  const query = getTextToken(get(search));
  return get(allTxChainsInfo).filter(chain =>
    getTextToken(chain.name).includes(query)
    || ('evmChainName' in chain && getTextToken(chain.evmChainName).includes(query)),
  );
});

const indeterminate = computed<boolean>(() => {
  const selectedItems = get(selection).length;
  return selectedItems > 0 && selectedItems < get(allTxChainsInfo).length;
});

const selected = computed<boolean>(() => {
  const selectedItems = get(selection).length;
  return selectedItems > 0 && selectedItems === get(allTxChainsInfo).length;
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
    set(selection, get(allTxChainsInfo).map(chain => chain.id));
  }
}

function reset() {
  set(open, false);
  set(selection, []);
  set(search, '');
}

/** Redecodes the picked chains; every chain is the full run, which asks for confirmation before it starts. */
function redecode() {
  emit('redecode', get(selected) ? { type: 'all' } : { chains: get(selection), type: 'chains' });
  reset();
}
</script>

<template>
  <RuiMenu
    v-model="open"
    class="border-0!"
    :options="{ placement: 'bottom-end' }"
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="outlined"
        color="primary"
        class="[&>span]:hidden! lg:[&>span]:inline!"
        :disabled="disabled"
        :aria-label="t('transactions.events_decoding.redecode')"
        data-testid="history-redecode"
        v-bind="attrs"
      >
        <template #prepend>
          <RuiIcon name="lu-refresh-cw" />
        </template>
        {{ t('transactions.events_decoding.redecode') }}
        <template #append>
          <RuiIcon
            name="lu-chevron-down"
            size="16"
          />
        </template>
      </RuiButton>
    </template>

    <div class="w-112.5">
      <div class="p-4 border-b border-default">
        <RuiTextField
          v-model="search"
          dense
          color="primary"
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

    <div class="h-55 overflow-y-auto">
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
          data-testid="history-redecode-selection-confirm"
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
        class="w-full justify-start!"
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
