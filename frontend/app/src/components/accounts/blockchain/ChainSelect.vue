<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Module } from '@/types/modules';

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    disabled?: boolean;
    dense?: boolean;
    evmOnly?: boolean;
    excludeEthStaking?: boolean;
    items?: string[];
  }>(),
  {
    disabled: false,
    dense: false,
    evmOnly: false,
    excludeEthStaking: false,
    items: () => [],
  },
);

const model = defineModel<string | undefined>({ required: true });

const { evmOnly, excludeEthStaking, items } = toRefs(props);

const { isModuleEnabled } = useModules();

const { isEvm, supportedChains } = useSupportedChains();

const { t } = useI18n();

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
  return get(supportedChains).filter(item => filtered.includes(item.id));
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
    key-attr="id"
    text-attr="name"
    :item-height="dense ? 48 : 56"
    v-bind="$attrs"
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
