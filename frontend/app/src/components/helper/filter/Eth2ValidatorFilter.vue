<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type {
  Eth2ValidatorEntry,
  EthStakingFilter,
} from '@rotki/common/lib/staking/eth2';

defineProps<{
  value: EthStakingFilter;
}>();

const emit = defineEmits<{
  (e: 'input', value: EthStakingFilter): void;
}>();

const { t } = useI18n();

const chain = Blockchain.ETH;
const accounts = ref<BlockchainAccount<AddressData>[]>([]);

const { ethStakingValidators } = storeToRefs(useBlockchainStore());

function updateValidators(validators: Eth2ValidatorEntry[]) {
  emit('input', { validators });
}

function updateAccounts(accounts: BlockchainAccount<AddressData>[]) {
  const accountList = accounts.map(account => ({
    address: getAccountAddress(account),
    chain: account.chain,
  }));
  emit('input', { accounts: accountList });
}

watch(accounts, accounts => updateAccounts(accounts));
</script>

<template>
  <BlockchainAccountSelector
    v-if="'accounts' in value"
    v-model="accounts"
    no-padding
    flat
    dense
    outlined
    :chains="[chain]"
    :label="t('eth2_validator_filter.label')"
    multiple
  />
  <ValidatorFilterInput
    v-else
    :value="value.validators"
    :items="ethStakingValidators.map(({ data }) => data)"
    @input="updateValidators($event)"
  />
</template>
