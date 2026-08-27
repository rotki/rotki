<script lang="ts" setup>
import type { ZodType } from 'zod';
import type { BlockchainAccount, ValidatorData } from '@/modules/accounts/blockchain-accounts';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type { RepullingEthStakingPayload } from '@/modules/history/events/event-payloads';
import { Blockchain, toHumanReadable } from '@rotki/common';
import { isValidatorAccount } from '@/modules/accounts/account-utils';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { toServerErrors } from '@/modules/core/form/server-errors';
import { type FormApi, noSubmit, useForm } from '@/modules/core/form/use-form';
import { OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';
import {
  type RepullingEthStakingFormState,
  repullingEthStakingSchema,
  type RepullingFilterMode,
  toEthStakingPayload,
} from '@/modules/history/events/tx/repulling-forms';
import AccountDisplay from '@/modules/shell/components/display/AccountDisplay.vue';
import DateTimeRangePicker from '@/modules/shell/components/inputs/DateTimeRangePicker.vue';
import ValidatorFilterInput from '@/modules/staking/eth2/ValidatorFilterInput.vue';
import { useBlockchainValidatorsStore } from '@/modules/staking/use-blockchain-validators-store';

const modelValue = defineModel<RepullingEthStakingPayload>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { t } = useI18n({ useScope: 'global' });

/*
 * `useForm` rather than `useModelForm`: the payload is a projection of this state, not a copy of it.
 * The filter mode picks which of the two selections is sent and never travels itself, so syncing the
 * model back in would push request-shaped keys into the state.
 */
const form: FormApi<RepullingEthStakingFormState, RepullingEthStakingPayload> = useForm({
  initial: (): RepullingEthStakingFormState => ({
    entryType: get(modelValue).entryType,
    filterMode: 'validator_indices',
    fromTimestamp: get(modelValue).fromTimestamp,
    selectedAddresses: [],
    selectedValidators: [],
    toTimestamp: get(modelValue).toTimestamp,
  }),
  schema: (): ZodType => repullingEthStakingSchema({
    entryTypeRequired: t('transactions.repulling.validation.entry_type_non_empty'),
    rangeRequired: t('transactions.repulling.validation.date_non_empty'),
  }, form.state.entryType !== OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS),
  submit: noSubmit,
  transform: toEthStakingPayload,
});

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

const filterModeOptions = computed<{ id: RepullingFilterMode; label: string }[]>(() => [
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

const isBlockProductions = computed<boolean>(() => form.state.entryType === OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS);

const showDateRangePicker = computed<boolean>(() => !get(isBlockProductions));

// The dialog reads the request off the model, so every edit is projected into it.
watchDeep(() => form.state, (state) => {
  set(modelValue, toEthStakingPayload(state));
});

watch(() => form.state.filterMode, () => {
  form.state.selectedValidators = [];
  form.state.selectedAddresses = [];
});

watch(showDateRangePicker, (show) => {
  if (!show) {
    form.state.fromTimestamp = undefined;
    form.state.toTimestamp = undefined;
  }
});

watchImmediate(errors, (value) => {
  form.setServerErrors(toServerErrors(value));
}, { deep: true });

// Immediate, so arriving from an edited sibling tab hands the dialog's flag back disarmed.
syncRefs(form.dirty, stateUpdated);

onBeforeUnmount(() => {
  set(errors, {});
});

defineExpose({
  validate: (): boolean => form.validate(),
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
        v-model="form.state.entryType"
        data-testid="eth-staking-entry-type"
        :options="entryTypeOptions"
        :label="t('transactions.repulling.eth_staking.type_label')"
        variant="outlined"
        auto-select-first
        key-attr="id"
        text-attr="label"
        :error-messages="form.errors('entryType')"
        @update:model-value="form.touch('entryType')"
      />

      <RuiAutoComplete
        v-model="form.state.filterMode"
        data-testid="eth-staking-filter-mode"
        :options="filterModeOptions"
        :label="t('transactions.repulling.eth_staking.filter_by_label')"
        variant="outlined"
        auto-select-first
        key-attr="id"
        text-attr="label"
      />

      <ValidatorFilterInput
        v-if="form.state.filterMode === 'validator_indices'"
        v-model="form.state.selectedValidators"
        :items="ethStakingValidators"
        :hint="t('transactions.repulling.eth_staking.validator_indices_hint')"
      />

      <RuiAutoComplete
        v-else
        v-model="form.state.selectedAddresses"
        data-testid="eth-staking-addresses"
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
        v-model:start="form.state.fromTimestamp"
        v-model:end="form.state.toTimestamp"
        allow-empty
        max-end-date="now"
        :start-error-messages="form.errors('fromTimestamp')"
        :end-error-messages="form.errors('toTimestamp')"
        @update:start="form.touch('fromTimestamp')"
        @update:end="form.touch('toTimestamp')"
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
