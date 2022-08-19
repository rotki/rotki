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
    :label="tc('eth2_validator_filter.label')"
    multiple
  />
  <validator-filter-input
    v-else
    :value="value"
    :items="eth2Validators.entries"
    @input="input"
  />
</template>

<script lang="ts">
import { GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { defineComponent, PropType, ref, watch } from '@vue/composition-api';
import { storeToRefs } from 'pinia';
import { useI18n } from 'vue-i18n-composable';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import ValidatorFilterInput from '@/components/helper/filter/ValidatorFilterInput.vue';
import { useBlockchainAccountsStore } from '@/store/balances/blockchain-accounts';

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
  emits: ['input'],
  setup(props, { emit }) {
    const { eth2ValidatorsState: eth2Validators } = storeToRefs(
      useBlockchainAccountsStore()
    );
    const account = ref<GeneralAccount[]>([]);
    const { tc } = useI18n();
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
      eth2Validators,
      tc
    };
  }
});
</script>
