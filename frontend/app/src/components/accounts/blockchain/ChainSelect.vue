<template>
  <v-select
    :value="blockchain"
    data-cy="account-blockchain-field"
    outlined
    class="account-form__chain pt-2"
    :items="items"
    :label="$t('account_form.labels.blockchain')"
    :disabled="disabled"
    @change="updateBlockchain"
  >
    <template #selection="{ item }">
      <asset-details class="pt-2 pb-2" :asset="item" />
    </template>
    <template #item="{ item }">
      <asset-details class="pt-2 pb-2" :asset="item" />
    </template>
  </v-select>
</template>

<script lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { defineComponent, PropType, computed } from '@vue/composition-api';
import { setupModuleEnabled } from '@/composables/session';
import { Module } from '@/types/modules';

export default defineComponent({
  name: 'ChainSelect',
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
      const modules: Blockchain[] = Object.values(Blockchain);
      const isEth2Enabled = isModuleEnabled(Module.ETH2).value;

      if (!isEth2Enabled) {
        return modules.filter(value => value !== Blockchain.ETH2);
      }
      return modules;
    });

    return {
      items,
      updateBlockchain
    };
  }
});
</script>
