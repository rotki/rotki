<script setup lang="ts">
import type { AddressData, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import { Blockchain, type Eth2ValidatorEntry, type EthStakingFilter } from '@rotki/common';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import BlockchainAccountSelector from '@/modules/accounts/BlockchainAccountSelector.vue';
import ValidatorFilterInput from '@/modules/staking/eth2/ValidatorFilterInput.vue';
import { useBlockchainValidatorsStore } from '@/modules/staking/use-blockchain-validators-store';

const modelValue = defineModel<EthStakingFilter>({ required: true });

const { t } = useI18n({ useScope: 'global' });

const chain = Blockchain.ETH;
const accounts = ref<BlockchainAccount<AddressData>[]>([]);

const { ethStakingValidators } = storeToRefs(useBlockchainValidatorsStore());

function updateValidators(validators: Eth2ValidatorEntry[]): void {
  set(modelValue, { validators });
}

function updateAccounts(accounts: BlockchainAccount<AddressData>[]): void {
  const accountList = accounts.map(account => ({
    address: getAccountAddress(account),
    chain: account.chain,
  }));
  set(modelValue, { accounts: accountList });
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
    dense
    hide-details
    @update:model-value="updateValidators($event)"
  />
</template>
