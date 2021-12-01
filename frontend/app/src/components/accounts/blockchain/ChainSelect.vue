<template>
  <v-select
    :value="blockchain"
    data-cy="account-blockchain-field"
    outlined
    class="account-form__chain pt-2"
    :items="items"
    :label="$t('account_form.labels.blockchain')"
    :disabled="disabled"
    item-value="symbol"
    @change="updateBlockchain"
  >
    <template #selection="{ item }">
      <chain-display :item="item" />
    </template>
    <template #item="{ item }">
      <chain-display :item="item" />
    </template>
  </v-select>
</template>

<script lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { computed, defineComponent, PropType } from '@vue/composition-api';
import ChainDisplay from '@/components/accounts/blockchain/ChainDisplay.vue';
import { setupModuleEnabled } from '@/composables/session';
import { Module } from '@/types/modules';

type SupportedChain = {
  symbol: Blockchain;
  name: string;
};

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

export default defineComponent({
  name: 'ChainSelect',
  components: { ChainDisplay },
  props: {
    blockchain: {
      required: true,
      type: String as PropType<Blockchain>
    },
    disabled: {
      required: true,
      type: Boolean
    }
  },
  emits: ['update:blockchain'],
  setup(props, { emit }) {
    const updateBlockchain = (blockchain: Blockchain) => {
      emit('update:blockchain', blockchain);
    };

    const { isModuleEnabled } = setupModuleEnabled();

    const items = computed(() => {
      const isEth2Enabled = isModuleEnabled(Module.ETH2).value;

      if (!isEth2Enabled) {
        return chains.filter(({ symbol }) => symbol !== Blockchain.ETH2);
      }
      return chains;
    });

    return {
      items,
      updateBlockchain
    };
  }
});
</script>
