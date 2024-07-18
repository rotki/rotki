<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { Eth2ValidatorEntry, EthStakingFilter } from '@rotki/common/lib/staking/eth2';

defineProps<{
  modelValue: EthStakingFilter;
}>();

const emit = defineEmits<{
  (e: 'update:model-value', value: EthStakingFilter): void;
}>();

const { t } = useI18n();

const chain = Blockchain.ETH;
const accounts = ref<BlockchainAccount<AddressData>[]>([]);

const { ethStakingValidators } = storeToRefs(useBlockchainStore());

function updateValidators(validators: Eth2ValidatorEntry[]) {
  emit('update:model-value', { validators });
}

function updateAccounts(accounts: BlockchainAccount<AddressData>[]) {
  const accountList = accounts.map(account => ({
    address: getAccountAddress(account),
    chain: account.chain,
  }));
  emit('update:model-value', { accounts: accountList });
}

watch(accounts, accounts => updateAccounts(accounts));
</script>

<template>
  <BlockchainAccountSelector
    v-if="'accounts' in modelValue"
    v-model="accounts"
    no-padding
    dense
    outlined
    :chains="[chain]"
    :label="t('eth2_validator_filter.label')"
  />
  <ValidatorFilterInput
    v-else
    :model-value="modelValue.validators"
    :items="ethStakingValidators"
    @update:model-value="updateValidators($event)"
  />
</template>
