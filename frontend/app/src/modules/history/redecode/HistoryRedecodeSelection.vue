<script setup lang="ts">
import type { EvmChainInfo } from '@/types/api/chains';
import { getTextToken } from '@rotki/common';
import { checkIfDevelopment } from '@shared/utils';
import { useSupportedChains } from '@/composables/info/chains';
import HistoryRedecodeChainItem from '@/modules/history/redecode/HistoryRedecodeChainItem.vue';

withDefaults(defineProps<{
  loading: boolean;
  disabled?: boolean;
}>(), {
  disabled: false,
});

const emit = defineEmits<{ redecode: [payload: string[]] }>();

const open = ref<boolean>(false);
const search = ref<string>('');
const selection = ref<string[]>([]);

const isDemoMode = import.meta.env.VITE_DEMO_MODE !== undefined;
const isDevelopment = checkIfDevelopment();

const { t } = useI18n({ useScope: 'global' });
const { txEvmChains } = useSupportedChains();

const filteredChains = computed<EvmChainInfo[]>(() => {
  const query = getTextToken(get(search));
  const chains = get(txEvmChains);
  return chains.filter(chain => getTextToken(chain.name).includes(query) || getTextToken(chain.evmChainName).includes(query));
});

const indeterminate = computed<boolean>(() => {
  const selectedItems = get(selection).length;
  return selectedItems > 0 && selectedItems < get(txEvmChains).length;
});

const selected = computed<boolean>(() => {
  const selectedItems = get(selection).length;
  return selectedItems > 0 && selectedItems === get(txEvmChains).length;
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
    set(selection, get(txEvmChains).map(chain => chain.evmChainName));
  }
}

function reset() {
  set(open, false);
  set(selection, []);
  set(search, '');
}

function redecode() {
  emit('redecode', get(selection));
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
        :class="{
          'rounded-r-none': isDevelopment && !isDemoMode,
        }"
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
        :model-value="selection.includes(chain.evmChainName)"
        :disabled="disabled"
        :chain="chain.evmChainName"
        @update:model-value="toggleSelection(chain.evmChainName, $event)"
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
          {{ t('history_redecode_selection.redecode', { total: selection.length }) }}
        </RuiButton>
      </div>
    </div>
  </RuiMenu>
</template>
