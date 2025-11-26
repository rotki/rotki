<script lang="ts" setup>
import type { ValidationErrors } from '@/types/api/errors';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { Exchange } from '@/types/exchanges';
import type { RepullingTransactionPayload } from '@/types/history/events';
import useVuelidate from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import ChainSelect from '@/components/accounts/blockchain/ChainSelect.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import DateTimeRangePicker from '@/components/inputs/DateTimeRangePicker.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useSupportedChains } from '@/composables/info/chains';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { Routes } from '@/router/routes';
import { useSessionSettingsStore } from '@/store/settings/session';
import { hasAccountAddress } from '@/utils/blockchain/accounts';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';

type AccountType = 'blockchain' | 'exchange';

const modelValue = defineModel<RepullingTransactionPayload>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });
const accountType = defineModel<AccountType>('accountType', { default: 'blockchain', required: false });

const { t } = useI18n({ useScope: 'global' });

const chain = useRefPropVModel(modelValue, 'chain');
const address = useRefPropVModel(modelValue, 'address');
const fromTimestamp = useRefPropVModel(modelValue, 'fromTimestamp');
const toTimestamp = useRefPropVModel(modelValue, 'toTimestamp');

const exchange = ref<Exchange | undefined>(undefined);

const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());
const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
const { decodableTxChainsInfo, getChain } = useSupportedChains();
const decodableTxChains = useArrayMap(decodableTxChainsInfo, x => x.id);

const accountTypeOptions = computed<{ text: string; value: AccountType }[]>(() => [
  { text: t('transactions.repulling.account_type.blockchain'), value: 'blockchain' },
  { text: t('transactions.repulling.account_type.exchange'), value: 'exchange' },
]);

const chainOptions = computed(() => {
  const accountChains = Object.entries(get(accountsPerChain))
    .filter(([_, accounts]) => accounts.length > 0)
    .map(([chain]) => chain);

  return get(decodableTxChains).filter(chain => accountChains.includes(chain));
});

const usableChains = computed<string[]>(() => {
  const chainVal = get(chain);
  if (!chainVal) {
    return get(chainOptions);
  }

  return [getChain(chainVal)];
});

const accounts = computed<BlockchainAccount<AddressData>[]>({
  get: () => {
    const model = get(modelValue);
    const accountFound = Object.values(get(accountsPerChain))
      .flatMap(x => x)
      .filter(hasAccountAddress)
      .find(
        item =>
          getAccountAddress(item) === model.address
          && (!model.chain || model.chain === item.chain),
      );

    if (accountFound) {
      return [accountFound];
    }

    return [];
  },
  set: (value: BlockchainAccount<AddressData>[]) => {
    const account = value[0];
    const address = account
      ? getAccountAddress(account)
      : '';

    set(modelValue, {
      ...get(modelValue),
      address,
    });
  },
});

const isBlockchainType = computed<boolean>(() => get(accountType) === 'blockchain');

const hasNoBlockchainAccounts = computed<boolean>(() => get(isBlockchainType) && get(chainOptions).length === 0);

const hasNoExchanges = computed<boolean>(() => !get(isBlockchainType) && get(connectedExchanges).length === 0);

const rules = computed(() => {
  if (get(isBlockchainType)) {
    return {
      address: { externalServerValidation: () => true },
      chain: { required },
      exchange: {},
      fromTimestamp: { required },
      toTimestamp: { required },
    };
  }
  return {
    address: {},
    chain: {},
    exchange: { required },
    fromTimestamp: { required },
    toTimestamp: { required },
  };
});

const states = {
  address,
  chain,
  exchange,
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

watchImmediate(accountType, (type) => {
  if (!type) {
    set(accountType, 'blockchain');
  }
});

defineExpose({
  getExchangeData: () => get(exchange),
  validate: () => get(v$).$validate(),
});
</script>

<template>
  <form class="flex flex-col gap-4">
    <RuiTabs
      v-model="accountType"
      class="border border-default rounded bg-white dark:bg-rui-grey-900 flex max-w-min mb-5"
      color="primary"
    >
      <RuiTab
        v-for="option in accountTypeOptions"
        :key="option.value"
        :value="option.value"
      >
        {{ option.text }}
      </RuiTab>
    </RuiTabs>

    <RuiAlert
      v-if="hasNoBlockchainAccounts"
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

    <RuiAlert
      v-else-if="hasNoExchanges"
      type="warning"
    >
      <i18n-t
        keypath="transactions.repulling.no_exchanges"
        tag="span"
      >
        <template #link>
          <RouterLink :to="Routes.API_KEYS_EXCHANGES">
            <RuiButton
              color="primary"
              variant="text"
              size="sm"
              class="inline -my-1 [&>span]:underline"
            >
              {{ t('transactions.repulling.add_exchange_link') }}
            </RuiButton>
          </RouterLink>
        </template>
      </i18n-t>
    </RuiAlert>

    <template v-else>
      <div
        v-if="isBlockchainType"
        class="flex gap-2"
      >
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

      <RuiAutoComplete
        v-else
        v-model="exchange"
        :options="connectedExchanges"
        :label="t('transactions.repulling.exchange')"
        variant="outlined"
        auto-select-first
        :item-height="48"
        text-attr="name"
        :error-messages="toMessages(v$.exchange)"
      >
        <template #selection="{ item }">
          <div class="flex items-center gap-2">
            <LocationDisplay
              horizontal
              icon
              :open-details="false"
              :identifier="item.location"
            />
            {{ item.name }}
          </div>
        </template>
        <template #item="{ item }">
          <div class="flex items-center gap-2">
            <LocationDisplay
              icon
              horizontal
              :open-details="false"
              :identifier="item.location"
            />
            {{ item.name }}
          </div>
        </template>
      </RuiAutoComplete>

      <DateTimeRangePicker
        v-model:start="fromTimestamp"
        v-model:end="toTimestamp"
        allow-empty
        max-end-date="now"
        :start-error-messages="toMessages(v$.fromTimestamp)"
        :end-error-messages="toMessages(v$.toTimestamp)"
      />
    </template>
  </form>
</template>
