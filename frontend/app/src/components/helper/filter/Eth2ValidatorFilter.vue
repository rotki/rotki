<script setup lang="ts">
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import ValidatorFilterInput from '@/components/helper/filter/ValidatorFilterInput.vue';
import { useBlockchainValidatorsStore } from '@/store/blockchain/validators';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { Blockchain, type Eth2ValidatorEntry, type EthStakingFilter } from '@rotki/common';

defineProps<{
  modelValue: EthStakingFilter;
}>();

const emit = defineEmits<{
  (e: 'update:model-value', value: EthStakingFilter): void;
}>();

const { t } = useI18n({ useScope: 'global' });

const chain = Blockchain.ETH;
const accounts = ref<BlockchainAccount<AddressData>[]>([]);

const { ethStakingValidators } = storeToRefs(useBlockchainValidatorsStore());

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
    dense
    outlined
    :chains="[chain]"
    class="!bg-transparent"
    :label="t('eth2_validator_filter.label')"
  />
  <ValidatorFilterInput
    v-else
    :model-value="modelValue.validators"
    :items="ethStakingValidators"
    @update:model-value="updateValidators($event)"
  />
</template>
