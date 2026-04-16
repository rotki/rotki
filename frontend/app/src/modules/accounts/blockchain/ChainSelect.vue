<script setup lang="ts" generic="T extends string | string[]">
import type { ChainInfo } from '@/modules/core/api/types/chains';
import { Blockchain } from '@rotki/common';
import ChainDisplay from '@/modules/accounts/blockchain/ChainDisplay.vue';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { getModuleEnabled, Module } from '@/modules/session/use-module-enabled';

defineOptions({
  inheritAttrs: false,
});

const model = defineModel<T extends Array<infer U> ? U[] : T | undefined>({ required: true });

const {
  dense = false,
  disabled = false,
  evmOnly = false,
  excludeEthStaking = false,
  items = [],
} = defineProps<{
  disabled?: boolean;
  dense?: boolean;
  evmOnly?: boolean;
  excludeEthStaking?: boolean;
  items?: string[];
}>();

const { isEvm, supportedChains } = useSupportedChains();

const { t } = useI18n({ useScope: 'global' });

const filteredItems = computed<string[]>(() => {
  const isEth2Enabled = getModuleEnabled(Module.ETH2);

  let data: string[] = get(supportedChains).map(({ id }) => id);

  if (items.length > 0)
    data = data.filter(chain => items.includes(chain));

  if (!isEth2Enabled || excludeEthStaking)
    data = data.filter(symbol => symbol !== Blockchain.ETH2);

  if (evmOnly)
    data = data.filter(isEvm);

  return data;
});

const mappedOptions = computed<ChainInfo[]>(() => {
  const filtered = get(filteredItems);
  const chains = get(supportedChains).filter(item => filtered.includes(item.id));
  if (items.includes('all')) {
    chains.unshift({
      id: 'all',
      image: '',
      name: '',
      type: 'all',
    });
  }

  return chains;
});
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
    v-bind="{ ...$attrs, keyAttr: 'id' as any }"
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
