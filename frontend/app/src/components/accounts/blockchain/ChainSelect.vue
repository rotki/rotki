<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Module } from '@/types/modules';

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

const rootAttrs = useAttrs();

const emit = defineEmits<{
  (e: 'update:model-value', blockchain: Blockchain): void;
}>();

const updateBlockchain = (blockchain: Blockchain) => {
  emit('update:model-value', blockchain);
};

const { evmOnly } = toRefs(props);

const { isModuleEnabled } = useModules();

const { isEvm, supportedChains } = useSupportedChains();

const items = computed(() => {
  const isEth2Enabled = get(isModuleEnabled(Module.ETH2));

  let data = get(supportedChains).map(({ id }) => id);

  if (!isEth2Enabled) {
    data = data.filter(symbol => symbol !== Blockchain.ETH2);
  }

  if (get(evmOnly)) {
    data = data.filter(symbol => get(isEvm(symbol as Blockchain)));
  }

  return data;
});

const { t } = useI18n();
</script>

<template>
  <v-select
    :value="modelValue"
    data-cy="account-blockchain-field"
    outlined
    class="account-form__chain"
    :items="items"
    :label="t('account_form.labels.blockchain')"
    :disabled="disabled"
    :dense="dense"
    v-bind="rootAttrs"
    @change="updateBlockchain"
  >
    <template #selection="{ item }">
      <chain-display :chain="item" :dense="dense" />
    </template>
    <template #item="{ item }">
      <chain-display :chain="item" />
    </template>
  </v-select>
</template>
