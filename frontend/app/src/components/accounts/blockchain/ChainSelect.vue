<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Module } from '@/types/modules';

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    modelValue?: string | null;
    disabled?: boolean;
    dense?: boolean;
    evmOnly?: boolean;
    excludeEthStaking?: boolean;
    items?: string[];
  }>(),
  {
    modelValue: null,
    disabled: false,
    dense: false,
    evmOnly: false,
    excludeEthStaking: false,
    items: () => [],
  },
);

const emit = defineEmits<{
  (e: 'update:model-value', blockchain: string | null): void;
}>();

const rootAttrs = useAttrs();

const { evmOnly, modelValue, excludeEthStaking, items } = toRefs(props);

const { isModuleEnabled } = useModules();

const { isEvm, supportedChains } = useSupportedChains();

const { t } = useI18n();

const search = ref<string | null>(null);

const filteredItems = computed(() => {
  const isEth2Enabled = get(isModuleEnabled(Module.ETH2));

  let data: string[] = get(supportedChains).map(({ id }) => id);

  const only = get(items);
  if (only.length > 0)
    data = data.filter(chain => only.includes(chain));

  if (!isEth2Enabled || get(excludeEthStaking))
    data = data.filter(symbol => symbol !== Blockchain.ETH2);

  if (get(evmOnly))
    data = data.filter(symbol => get(isEvm(symbol as Blockchain)));

  return data;
});

function clearSearch() {
  set(search, '');
}

function updateBlockchain(blockchain: Blockchain) {
  clearSearch();
  emit('update:model-value', blockchain);
}

function filter(chain: Blockchain, queryText: string) {
  const item = get(supportedChains).find(blockchain => blockchain.id === chain);
  if (!item)
    return false;

  const nameIncludes = item.name
    .toLocaleLowerCase()
    .includes(queryText.toLocaleLowerCase());

  const idIncludes = item.id
    .toLocaleLowerCase()
    .includes(queryText.toLocaleLowerCase());

  return nameIncludes || idIncludes;
}
</script>

<template>
  <VAutocomplete
    :dense="dense"
    :disabled="disabled"
    :filter="filter"
    :items="filteredItems"
    :label="t('account_form.labels.blockchain')"
    :search-input.sync="search"
    :value="modelValue"
    data-cy="account-blockchain-field"
    outlined
    auto-select-first
    single-line
    v-bind="rootAttrs"
    @change="updateBlockchain($event)"
    @blur="clearSearch()"
  >
    <template #selection="{ item }">
      <ChainDisplay
        v-if="!search"
        :chain="item"
        :dense="dense"
        class="!py-0"
      />
    </template>
    <template #item="{ item }">
      <ChainDisplay
        :chain="item"
        :dense="dense"
      />
    </template>
  </VAutocomplete>
</template>
