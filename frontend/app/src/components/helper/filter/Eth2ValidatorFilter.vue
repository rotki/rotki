<script setup lang="ts">
import { type GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import ValidatorFilterInput from '@/components/helper/filter/ValidatorFilterInput.vue';
import { useEthAccountsStore } from '@/store/blockchain/accounts/eth';

withDefaults(
  defineProps<{
    value: string[];
    usableAddresses?: string[];
    filterType?: 'address' | 'key';
  }>(),
  {
    usableAddresses: () => [],
    filterType: 'address'
  }
);

const emit = defineEmits<{ (e: 'input', value: string[]): void }>();

const chains = [Blockchain.ETH];
const accounts = ref<GeneralAccount[]>([]);

const { eth2Validators } = storeToRefs(useEthAccountsStore());
const { tc } = useI18n();

const input = (selection: string[]) => {
  emit('input', selection);
};

watch(accounts, account => {
  input(account.length === 0 ? [] : [account[0].address]);
});
</script>

<template>
  <blockchain-account-selector
    v-if="filterType === 'address'"
    v-model="accounts"
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
