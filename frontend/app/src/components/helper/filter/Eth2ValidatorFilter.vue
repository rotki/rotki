<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import type { GeneralAccount } from '@rotki/common/lib/account';
import type {
  Eth2ValidatorEntry,
  EthStakingFilter,
} from '@rotki/common/lib/staking/eth2';

defineProps<{
  modelValue: EthStakingFilter;
}>();

const emit = defineEmits<{
  (e: 'update:model-value', value: EthStakingFilter): void;
}>();

const chain = Blockchain.ETH;
const accounts: Ref<GeneralAccount[]> = ref([]);

const { eth2Validators } = storeToRefs(useEthAccountsStore());
const { t } = useI18n();

function updateValidators(validators: Eth2ValidatorEntry[]) {
  emit('update:model-value', { validators });
}

function updateAccounts(accounts: GeneralAccount[]) {
  emit('update:model-value', { accounts });
}

watch(accounts, accounts => updateAccounts(accounts));
</script>

<template>
  <BlockchainAccountSelector
    v-if="'accounts' in modelValue"
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
    :model-value="modelValue.validators"
    :items="eth2Validators.entries"
    @update:model-value="updateValidators($event)"
  />
</template>
