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

<script setup lang="ts">
import { GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { PropType } from 'vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import ValidatorFilterInput from '@/components/helper/filter/ValidatorFilterInput.vue';
import { useEthAccountsStore } from '@/store/blockchain/accounts/eth';

defineProps({
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
});

const emit = defineEmits<{ (e: 'input', value: string[]): void }>();

const chains = [Blockchain.ETH];
const account = ref<GeneralAccount[]>([]);

const { eth2Validators } = storeToRefs(useEthAccountsStore());
const { tc } = useI18n();

const input = (selection: string[]) => {
  emit('input', selection);
};

watch(account, account => {
  input(account.length === 0 ? [] : [account[0].address]);
});
</script>
