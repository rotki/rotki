<template>
  <blockchain-account-selector
    v-if="filterType === 'address'"
    v-model="account"
    no-padding
    flat
    dense
    outlined
    :chains="chains"
    :usable-addresses="usableAddresses"
    :label="$t('eth2_validator_filter.label')"
    multiple
  />
  <validator-filter-input
    v-else
    :value="value"
    :items="eth2Validators"
    @input="input"
  />
</template>

<script lang="ts">
import { GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { defineComponent, PropType, ref, watch } from '@vue/composition-api';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import ValidatorFilterInput from '@/components/helper/filter/ValidatorFilterInput.vue';
import { setupBlockchainAccounts } from '@/composables/balances';

export default defineComponent({
  name: 'Eth2ValidatorFilter',
  components: { ValidatorFilterInput, BlockchainAccountSelector },
  props: {
    value: {
      required: true,
      type: Array as PropType<string[]>
    },
    usableAddresses: {
      required: false,
      type: Array as PropType<string[]>,
      default: () => []
    },
    filterType: {
      required: false,
      type: String as PropType<'address' | 'key'>,
      default: 'address'
    }
  },
  setup(props, { emit }) {
    const { eth2Validators } = setupBlockchainAccounts();
    const account = ref<GeneralAccount[]>([]);
    const input = (selection: string[]) => {
      emit('input', selection);
    };
    watch(account, account => {
      input(account.length === 0 ? [] : [account[0].address]);
    });
    return {
      account,
      input,
      chains: [Blockchain.ETH],
      eth2Validators
    };
  }
});
</script>
