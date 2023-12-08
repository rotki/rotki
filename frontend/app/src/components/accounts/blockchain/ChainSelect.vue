<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Module } from '@/types/modules';

defineOptions({
  inheritAttrs: false
});

const props = withDefaults(
  defineProps<{
    modelValue?: Blockchain | null;
    disabled?: boolean;
    dense?: boolean;
    evmOnly?: boolean;
  }>(),
  {
    modelValue: null,
    disabled: false,
    dense: false,
    evmOnly: false
  }
);

const emit = defineEmits<{
  (e: 'update:model-value', blockchain: Blockchain | null): void;
}>();

const rootAttrs = useAttrs();

const { evmOnly, modelValue } = toRefs(props);

const { isModuleEnabled } = useModules();

const { isEvm, supportedChains } = useSupportedChains();

const { t } = useI18n();

const search = ref<string | null>(null);

const items = computed(() => {
  const isEth2Enabled = get(isModuleEnabled(Module.ETH2));

  let data: string[] = get(supportedChains).map(({ id }) => id);

  if (!isEth2Enabled) {
    data = data.filter(symbol => symbol !== Blockchain.ETH2);
  }

  if (get(evmOnly)) {
    data = data.filter(symbol => get(isEvm(symbol as Blockchain)));
  }

  return data;
});

const clearSearch = () => {
  set(search, '');
};

const updateBlockchain = (blockchain: Blockchain) => {
  clearSearch();
  emit('update:model-value', blockchain);
};

const filter = (chain: Blockchain, queryText: string) => {
  const item = get(supportedChains).find(blockchain => blockchain.id === chain);
  if (!item) {
    return false;
  }

  const nameIncludes = item.name
    .toLocaleLowerCase()
    .includes(queryText.toLocaleLowerCase());

  const idIncludes = item.id
    .toLocaleLowerCase()
    .includes(queryText.toLocaleLowerCase());

  return nameIncludes || idIncludes;
};
</script>

<template>
  <VAutocomplete
    :dense="dense"
    :disabled="disabled"
    :filter="filter"
    :items="items"
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
        :full-width="false"
      />
    </template>
    <template #item="{ item }">
      <ChainDisplay :chain="item" />
    </template>
  </VAutocomplete>
</template>
