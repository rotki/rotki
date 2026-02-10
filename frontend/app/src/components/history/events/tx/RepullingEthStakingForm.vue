<script lang="ts" setup>
import type { ValidationErrors } from '@/types/api/errors';
import type { BlockchainAccount, ValidatorData } from '@/types/blockchain/accounts';
import type { RepullingEthStakingPayload } from '@/types/history/events';
import { Blockchain, type Eth2ValidatorEntry, toHumanReadable } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import AccountDisplay from '@/components/display/AccountDisplay.vue';
import ValidatorFilterInput from '@/components/helper/filter/ValidatorFilterInput.vue';
import DateTimeRangePicker from '@/components/inputs/DateTimeRangePicker.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBlockchainValidatorsStore } from '@/store/blockchain/validators';
import { OnlineHistoryEventsQueryType } from '@/types/history/events/schemas';
import { isValidatorAccount } from '@/utils/blockchain/accounts/utils';
import { toMessages } from '@/utils/validation';

type FilterMode = 'addresses' | 'validator_indices';

const modelValue = defineModel<RepullingEthStakingPayload>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { t } = useI18n({ useScope: 'global' });

const entryType = ref<string>(get(modelValue).entryType);
const fromTimestamp = ref<number | undefined>(get(modelValue).fromTimestamp);
const toTimestamp = ref<number | undefined>(get(modelValue).toTimestamp);
const filterMode = ref<FilterMode>('validator_indices');
const selectedValidators = ref<Eth2ValidatorEntry[]>([]);
const selectedAddresses = ref<string[]>([]);

const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());
const { ethStakingValidators } = storeToRefs(useBlockchainValidatorsStore());

const entryTypeOptions: { id: string; label: string }[] = [
  {
    id: OnlineHistoryEventsQueryType.ETH_WITHDRAWALS,
    label: toHumanReadable(OnlineHistoryEventsQueryType.ETH_WITHDRAWALS, 'capitalize'),
  },
  {
    id: OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS,
    label: toHumanReadable(OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS, 'capitalize'),
  },
];

const filterModeOptions = computed<{ id: FilterMode; label: string }[]>(() => [
  {
    id: 'validator_indices',
    label: t('transactions.repulling.eth_staking.filter_mode.validator_indices'),
  },
  {
    id: 'addresses',
    label: t('transactions.repulling.eth_staking.filter_mode.addresses'),
  },
]);

const eth2Accounts = computed(() => get(accountsPerChain)[Blockchain.ETH2] ?? []);

const validatorAccounts = computed<BlockchainAccount<ValidatorData>[]>(() =>
  get(eth2Accounts).filter(isValidatorAccount),
);

const withdrawalAddressOptions = computed<string[]>(() => {
  const addresses = new Set<string>();
  for (const account of get(validatorAccounts)) {
    if (account.data.withdrawalAddress)
      addresses.add(account.data.withdrawalAddress);
  }
  return [...addresses];
});

const hasNoValidators = computed<boolean>(() => get(eth2Accounts).length === 0);

const isBlockProductions = computed<boolean>(() => get(entryType) === OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS);

const showDateRangePicker = computed<boolean>(() => !get(isBlockProductions));

const rules = computed(() => {
  const timestampRules = get(showDateRangePicker) ? { required } : {};
  return {
    entryType: { required },
    fromTimestamp: timestampRules,
    toTimestamp: timestampRules,
  };
});

const states = computed(() => ({
  entryType: get(entryType),
  fromTimestamp: get(fromTimestamp),
  toTimestamp: get(toTimestamp),
}));

const watchedStates = {
  entryType,
  filterMode,
  fromTimestamp,
  selectedAddresses,
  selectedValidators,
  toTimestamp,
};

const v$ = useVuelidate(
  rules,
  states,
  {
    $autoDirty: true,
    $externalResults: errors,
  },
);

useFormStateWatcher(watchedStates, stateUpdated);

const payload = computed<RepullingEthStakingPayload>(() => {
  const base: RepullingEthStakingPayload = {
    entryType: get(entryType),
    fromTimestamp: get(fromTimestamp),
    toTimestamp: get(toTimestamp),
  };

  if (get(filterMode) === 'validator_indices') {
    return {
      ...base,
      validatorIndices: get(selectedValidators).map(v => v.index),
    };
  }

  return {
    ...base,
    addresses: get(selectedAddresses),
  };
});

watch(payload, (val) => {
  set(modelValue, val);
});

watch(filterMode, () => {
  set(selectedValidators, []);
  set(selectedAddresses, []);
});

watch(showDateRangePicker, (show) => {
  if (!show) {
    set(fromTimestamp, undefined);
    set(toTimestamp, undefined);
  }
});

onBeforeUnmount(() => {
  set(errors, {});
});

defineExpose({
  validate: (): Promise<boolean> => get(v$).$validate(),
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <RuiAlert
      v-if="hasNoValidators"
      type="warning"
    >
      {{ t('transactions.repulling.eth_staking.no_validators') }}
    </RuiAlert>

    <template v-else>
      <RuiAutoComplete
        v-model="entryType"
        :options="entryTypeOptions"
        :label="t('transactions.repulling.eth_staking.type_label')"
        variant="outlined"
        auto-select-first
        key-attr="id"
        text-attr="label"
        :error-messages="toMessages(v$.entryType)"
      />

      <RuiAutoComplete
        v-model="filterMode"
        :options="filterModeOptions"
        :label="t('transactions.repulling.eth_staking.filter_by_label')"
        variant="outlined"
        auto-select-first
        key-attr="id"
        text-attr="label"
      />

      <ValidatorFilterInput
        v-if="filterMode === 'validator_indices'"
        v-model="selectedValidators"
        :items="ethStakingValidators"
        :hint="t('transactions.repulling.eth_staking.validator_indices_hint')"
      />

      <RuiAutoComplete
        v-else
        v-model="selectedAddresses"
        :options="withdrawalAddressOptions"
        :label="t('transactions.repulling.eth_staking.addresses_label')"
        variant="outlined"
        :item-height="40"
        chips
        clearable
        :hint="t('transactions.repulling.eth_staking.addresses_hint')"
      >
        <template #selection="{ item }">
          <AccountDisplay
            :account="{ address: item, chain: Blockchain.ETH }"
            size="20px"
            hide-chain-icon
          />
        </template>
        <template #item="{ item }">
          <AccountDisplay
            :account="{ address: item, chain: Blockchain.ETH }"
            size="24px"
            hide-chain-icon
          />
        </template>
      </RuiAutoComplete>

      <DateTimeRangePicker
        v-if="showDateRangePicker"
        v-model:start="fromTimestamp"
        v-model:end="toTimestamp"
        allow-empty
        max-end-date="now"
        :start-error-messages="toMessages(v$.fromTimestamp)"
        :end-error-messages="toMessages(v$.toTimestamp)"
      />

      <RuiAlert
        v-if="isBlockProductions"
        type="warning"
      >
        {{ t('transactions.repulling.eth_staking.block_productions_warning') }}
      </RuiAlert>
    </template>
  </div>
</template>
