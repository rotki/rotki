<script setup lang="ts" generic="T extends string | string[]">
import type { ChainInfo } from '@/types/api/chains';
import type { AutoCompleteProps } from '@rotki/ui-library';
import ChainDisplay from '@/components/accounts/blockchain/ChainDisplay.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { useModules } from '@/composables/session/modules';
import { Module } from '@/types/modules';
import { Blockchain } from '@rotki/common';

defineOptions({
  inheritAttrs: false,
});

const model = defineModel<T extends Array<infer U> ? U[] : T | undefined>({ required: true });

const props = withDefaults(
  defineProps<{
    disabled?: boolean;
    dense?: boolean;
    evmOnly?: boolean;
    excludeEthStaking?: boolean;
    items?: string[];
  }>(),
  {
    dense: false,
    disabled: false,
    evmOnly: false,
    excludeEthStaking: false,
    items: () => [],
  },
);

const { evmOnly, excludeEthStaking, items } = toRefs(props);

const { isModuleEnabled } = useModules();

const { isEvm, supportedChains } = useSupportedChains();

const { t } = useI18n({ useScope: 'global' });

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

const mappedOptions = computed(() => {
  const filtered = get(filteredItems);
  const chains = get(supportedChains).filter(item => filtered.includes(item.id));
  if (get(items).includes('evm')) {
    chains.unshift({
      id: 'evm',
      image: '',
      name: '',
      type: 'evm',
    });
  }

  return chains;
});

const autoCompleteProps: AutoCompleteProps<string, ChainInfo> = {
  keyAttr: 'id',
};
</script>

<template>
  <RuiAutoComplete
    v-model="model"
    :dense="dense"
    :disabled="disabled"
    :options="mappedOptions"
    :label="t('account_form.labels.blockchain')"
    data-cy="account-blockchain-field"
    variant="outlined"
    auto-select-first
    text-attr="name"
    :item-height="dense ? 48 : 56"
    v-bind="{ ...$attrs, ...autoCompleteProps }"
  >
    <template #selection="{ item }">
      <ChainDisplay
        :class="{ '-my-1': dense }"
        :dense="dense"
        :chain="item.id"
      />
    </template>
    <template #item="{ item }">
      <ChainDisplay
        :class="{ 'my-1': dense }"
        :dense="dense"
        :chain="item.id"
      />
    </template>
  </RuiAutoComplete>
</template>
