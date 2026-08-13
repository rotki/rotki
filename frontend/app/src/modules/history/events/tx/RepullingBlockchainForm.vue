<script lang="ts" setup>
import type { ZodType } from 'zod';
import type { AddressData, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type { RepullingTransactionPayload } from '@/modules/history/events/event-payloads';
import { hasAccountAddress } from '@/modules/accounts/account-helpers';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import ChainSelect from '@/modules/accounts/blockchain/ChainSelect.vue';
import BlockchainAccountSelector from '@/modules/accounts/BlockchainAccountSelector.vue';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useModelForm } from '@/modules/core/form/use-model-form';
import { type RepullingBlockchainFormState, repullingBlockchainSchema } from '@/modules/history/events/tx/repulling-forms';
import { useRepullingTransactionForm } from '@/modules/history/events/tx/use-repulling-transaction-form';
import DateTimeRangePicker from '@/modules/shell/components/inputs/DateTimeRangePicker.vue';

const modelValue = defineModel<RepullingTransactionPayload>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { t } = useI18n({ useScope: 'global' });

const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());
const { chainOptions, getUsableChains } = useRepullingTransactionForm();

const schema = computed<ZodType>(() => repullingBlockchainSchema(t('transactions.repulling.validation.date_non_empty')));

const form = useModelForm<RepullingBlockchainFormState>({
  model: modelValue,
  schema,
  serverErrors: errors,
  stateUpdated,
});

const hasNoAccounts = computed<boolean>(() => get(chainOptions).length === 0);

const usableChains = computed<string[]>(() => getUsableChains(form.state.chain));

const accounts = computed<BlockchainAccount<AddressData>[]>({
  get: () => {
    const { address, chain } = form.state;
    const accountFound = Object.values(get(accountsPerChain))
      .flatMap(x => x)
      .filter(hasAccountAddress)
      .find(
        item =>
          getAccountAddress(item) === address
          && (!chain || chain === 'all' || chain === item.chain),
      );

    if (accountFound) {
      return [accountFound];
    }

    return [];
  },
  set: (value: BlockchainAccount<AddressData>[]) => {
    const account = value[0];
    form.state.address = account ? getAccountAddress(account) : '';
    form.touch('address');
  },
});

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
      v-if="hasNoAccounts"
      type="warning"
    >
      <i18n-t
        keypath="transactions.repulling.no_accounts"
        tag="span"
      >
        <template #link>
          <RouterLink :to="{ name: '/accounts/evm/[[tab]]' }">
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
          v-model="form.state.chain"
          class="max-w-[20rem]"
          :items="chainOptions"
          :error-messages="form.errors('chain')"
          @update:model-value="form.touch('chain')"
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
          :error-messages="form.errors('address')"
          :no-data-text="t('transactions.form.account.no_address_found')"
        />
      </div>

      <DateTimeRangePicker
        v-model:start="form.state.fromTimestamp"
        v-model:end="form.state.toTimestamp"
        allow-empty
        max-end-date="now"
        :start-error-messages="form.errors('fromTimestamp')"
        :end-error-messages="form.errors('toTimestamp')"
        @update:start="form.touch('fromTimestamp')"
        @update:end="form.touch('toTimestamp')"
      />
    </template>
  </div>
</template>
