<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import ChainDisplay from '@/components/accounts/blockchain/ChainDisplay.vue';
import { Module } from '@/types/modules';

interface SupportedChain {
  symbol: Blockchain;
  name: string;
  icon?: string;
}

const chains: SupportedChain[] = [
  {
    symbol: Blockchain.ETH,
    name: 'Ethereum'
  },
  {
    symbol: Blockchain.ETH2,
    name: 'Beacon chain validator'
  },
  {
    symbol: Blockchain.BTC,
    name: 'Bitcoin'
  },
  {
    symbol: Blockchain.BCH,
    name: 'Bitcoin Cash'
  },
  {
    symbol: Blockchain.OPTIMISM,
    name: 'Optimism',
    icon: './assets/images/chains/optimism.svg'
  },
  {
    symbol: Blockchain.KSM,
    name: 'Kusama'
  },
  {
    symbol: Blockchain.DOT,
    name: 'Polkadot'
  },
  {
    symbol: Blockchain.AVAX,
    name: 'Avalanche'
  }
];

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

const { isEvm } = useSupportedChains();

const items = computed(() => {
  const isEth2Enabled = get(isModuleEnabled(Module.ETH2));

  let data = chains;

  if (!isEth2Enabled) {
    data = data.filter(({ symbol }) => symbol !== Blockchain.ETH2);
  }

  if (get(evmOnly)) {
    data = data.filter(({ symbol }) => get(isEvm(symbol)));
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
    item-value="symbol"
    :dense="dense"
    v-bind="rootAttrs"
    @change="updateBlockchain"
  >
    <template #selection="{ item }">
      <chain-display :item="item" :dense="dense" />
    </template>
    <template #item="{ item }">
      <chain-display :item="item" />
    </template>
  </v-select>
</template>
