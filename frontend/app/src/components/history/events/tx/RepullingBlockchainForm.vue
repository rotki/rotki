<script lang="ts" setup>
import type { ValidationErrors } from '@/types/api/errors';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { RepullingTransactionPayload } from '@/types/history/events';
import useVuelidate from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import ChainSelect from '@/components/accounts/blockchain/ChainSelect.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import DateTimeRangePicker from '@/components/inputs/DateTimeRangePicker.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useRepullingTransactionForm } from '@/composables/history/events/tx/use-repulling-transaction-form';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { Routes } from '@/router/routes';
import { hasAccountAddress } from '@/utils/blockchain/accounts';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';

const modelValue = defineModel<RepullingTransactionPayload>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { t } = useI18n({ useScope: 'global' });

const chain = useRefPropVModel(modelValue, 'chain');
const address = useRefPropVModel(modelValue, 'address');
const fromTimestamp = useRefPropVModel(modelValue, 'fromTimestamp');
const toTimestamp = useRefPropVModel(modelValue, 'toTimestamp');

const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());
const { chainOptions, getUsableChains } = useRepullingTransactionForm();

const hasNoAccounts = computed<boolean>(() => get(chainOptions).length === 0);

const usableChains = computed<string[]>(() => getUsableChains(get(chain)));

const accounts = computed<BlockchainAccount<AddressData>[]>({
  get: () => {
    const model = get(modelValue);
    const accountFound = Object.values(get(accountsPerChain))
      .flatMap(x => x)
      .filter(hasAccountAddress)
      .find(
        item =>
          getAccountAddress(item) === model.address
          && (!model.chain || model.chain === 'all' || model.chain === item.chain),
      );

    if (accountFound) {
      return [accountFound];
    }

    return [];
  },
  set: (value: BlockchainAccount<AddressData>[]) => {
    const account = value[0];
    const addr = account
      ? getAccountAddress(account)
      : '';

    set(modelValue, {
      ...get(modelValue),
      address: addr,
    });
  },
});

const rules = {
  address: { externalServerValidation: () => true },
  chain: {},
  fromTimestamp: { required },
  toTimestamp: { required },
};

const states = {
  address,
  chain,
  fromTimestamp,
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

useFormStateWatcher(states, stateUpdated);

onBeforeUnmount(() => {
  set(errors, {});
});

defineExpose({
  validate: () => get(v$).$validate(),
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <RuiAlert
      v-if="hasNoAccounts"
      type="warning"
    >
      <i18n-t
        keypath="transactions.repulling.no_accounts"
        tag="span"
      >
        <template #link>
          <RouterLink :to="Routes.ACCOUNTS_EVM">
            <RuiButton
              color="primary"
              variant="text"
              size="sm"
              class="inline -my-1 [&>span]:underline"
            >
              {{ t('transactions.repulling.add_account_link') }}
            </RuiButton>
          </RouterLink>
        </template>
      </i18n-t>
    </RuiAlert>

    <template v-else>
      <div class="flex gap-2">
        <ChainSelect
          v-model="chain"
          class="max-w-[20rem]"
          :items="chainOptions"
          :error-messages="toMessages(v$.chain)"
        />
        <BlockchainAccountSelector
          v-model="accounts"
          class="flex-1"
          :chains="usableChains"
          hide-chain-icon
          outlined
          show-details
          multichain
          unique
          :custom-hint="t('transactions.repulling.address_hint')"
          :label="t('common.address')"
          :error-messages="toMessages(v$.address)"
          :no-data-text="t('transactions.form.account.no_address_found')"
        />
      </div>

      <DateTimeRangePicker
        v-model:start="fromTimestamp"
        v-model:end="toTimestamp"
        allow-empty
        max-end-date="now"
        :start-error-messages="toMessages(v$.fromTimestamp)"
        :end-error-messages="toMessages(v$.toTimestamp)"
      />
    </template>
  </div>
</template>
