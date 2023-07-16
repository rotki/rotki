<script setup lang="ts">
import { type GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  type Eth2StakingFilter,
  type Eth2StakingFilterType,
  type Eth2ValidatorEntry
} from '@rotki/common/lib/staking/eth2';

withDefaults(
  defineProps<{
    value: Eth2StakingFilter;
    filterType?: Eth2StakingFilterType;
  }>(),
  {
    usableAddresses: () => [],
    filterType: 'address'
  }
);

const emit = defineEmits<{
  (e: 'input', value: Eth2StakingFilter): void;
}>();

const chain = Blockchain.ETH;
const accounts: Ref<GeneralAccount[]> = ref([]);

const { eth2Validators } = storeToRefs(useEthAccountsStore());
const { t } = useI18n();

const updateValidators = (validators: Eth2ValidatorEntry[]) => {
  emit('input', { validators, accounts: [] });
};

const updateAccounts = (accounts: GeneralAccount[]) => {
  emit('input', { validators: [], accounts });
};

watch(accounts, accounts => updateAccounts(accounts));
</script>

<template>
  <BlockchainAccountSelector
    v-if="filterType === 'address'"
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
