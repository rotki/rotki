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
import { useFormStateWatcher } from '@/composables/form';
import { useSupportedChains } from '@/composables/info/chains';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
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

const evmChain = useRefPropVModel(modelValue, 'evmChain');
const address = useRefPropVModel(modelValue, 'address');
const fromTimestamp = useRefPropVModel(modelValue, 'fromTimestamp');
const toTimestamp = useRefPropVModel(modelValue, 'toTimestamp');

const location = ref<string>('');
const name = ref<string>('');

const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());
const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
const { evmAndEvmLikeTxChainsInfo, getChain } = useSupportedChains();
const txChains = useArrayMap(evmAndEvmLikeTxChainsInfo, x => x.id);

const accountTypeOptions = computed<{ text: string; value: AccountType }[]>(() => [
  { text: t('transactions.repulling.account_type.blockchain'), value: 'blockchain' },
  { text: t('transactions.repulling.account_type.exchange'), value: 'exchange' },
]);

const selectedExchange = computed<Exchange | undefined>({
  get: () => {
    const locationVal = get(location);
    const nameVal = get(name);
    if (!locationVal || !nameVal) {
      return undefined;
    }
    return get(connectedExchanges).find(
      exchange => exchange.location === locationVal && exchange.name === nameVal,
    );
  },
  set: (value: Exchange | undefined) => {
    set(location, value?.location || '');
    set(name, value?.name || '');
  },
});

const chainOptions = computed(() => {
  const accountChains = Object.entries(get(accountsPerChain))
    .filter(([_, accounts]) => accounts.length > 0)
    .map(([chain]) => chain);

  return [
    'evm',
    ...get(txChains).filter(chain => accountChains.includes(chain)),
  ];
});

const usableChains = computed<string[]>(() => {
  const evmChainVal = get(evmChain);
  if (!evmChainVal || evmChainVal === 'evm') {
    return get(chainOptions);
  }

  return [getChain(evmChainVal)];
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
          && (!model.evmChain || model.evmChain === 'evm' || model.evmChain === item.chain),
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
const isExchangeType = computed<boolean>(() => get(accountType) === 'exchange');

const rules = computed(() => {
  if (get(isBlockchainType)) {
    return {
      address: { externalServerValidation: () => true },
      evmChain: { required },
      fromTimestamp: { required },
      location: {},
      name: {},
      toTimestamp: { required },
    };
  }
  return {
    address: {},
    evmChain: {},
    fromTimestamp: { required },
    location: { required },
    name: { required },
    toTimestamp: { required },
  };
});

const states = {
  address,
  evmChain,
  fromTimestamp,
  location,
  name,
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

watchImmediate(evmChain, (chain) => {
  if (chain === '') {
    set(evmChain, 'evm');
  }
});

watchImmediate(accountType, (type) => {
  if (!type) {
    set(accountType, 'blockchain');
  }
});

defineExpose({
  getExchangeData: () => ({ location: get(location), name: get(name) }),
  validate: () => get(v$).$validate(),
});
</script>

<template>
  <form class="flex flex-col gap-4">
    <RuiTabs
      v-model="accountType"
      class="border rounded bg-white dark:bg-rui-grey-900 flex max-w-min mb-5"
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

    <div
      v-if="isBlockchainType"
      class="flex gap-2"
    >
      <ChainSelect
        v-model="evmChain"
        class="max-w-[20rem]"
        :items="chainOptions"
        :error-messages="toMessages(v$.evmChain)"
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

    <div
      v-if="isExchangeType"
    >
      <RuiAutoComplete
        v-model="selectedExchange"
        :options="connectedExchanges"
        :label="t('transactions.repulling.exchange')"
        variant="outlined"
        auto-select-first
        :item-height="48"
        :error-messages="toMessages(v$.location)"
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
    </div>

    <div class="w-full flex gap-2">
      <div class="flex-1">
        <RuiDateTimePicker
          v-model="fromTimestamp"
          :label="t('generate.labels.start_date')"
          :max-date="toTimestamp"
          type="epoch"
          allow-empty
          color="primary"
          variant="outlined"
          :error-messages="toMessages(v$.fromTimestamp)"
        />
      </div>
      <div class="flex-1">
        <RuiDateTimePicker
          v-model="toTimestamp"
          :label="t('generate.labels.end_date')"
          :min-date="fromTimestamp"
          type="epoch"
          max-date="now"
          color="primary"
          variant="outlined"
          :error-messages="toMessages(v$.toTimestamp)"
        />
      </div>
    </div>
  </form>
</template>
