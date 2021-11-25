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
import { defineComponent, PropType } from '@vue/composition-api';

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

    return {
      items: Object.values(Blockchain),
      updateBlockchain
    };
  }
});
</script>
