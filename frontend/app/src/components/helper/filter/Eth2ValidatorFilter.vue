<script setup lang="ts">
import { type GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  type Eth2ValidatorEntry,
  type EthStakingFilter
} from '@rotki/common/lib/staking/eth2';

defineProps<{
  value: EthStakingFilter;
}>();

const emit = defineEmits<{
  (e: 'input', value: EthStakingFilter): void;
}>();

const chain = Blockchain.ETH;
const accounts: Ref<GeneralAccount[]> = ref([]);

const { eth2Validators } = storeToRefs(useEthAccountsStore());
const { t } = useI18n();

const updateValidators = (validators: Eth2ValidatorEntry[]) => {
  emit('input', { validators });
};

const updateAccounts = (accounts: GeneralAccount[]) => {
  emit('input', { accounts });
};

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
    :items="eth2Validators.entries"
    @input="updateValidators($event)"
  />
</template>
