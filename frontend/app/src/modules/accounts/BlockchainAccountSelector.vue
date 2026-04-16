<script setup lang="ts">
import type { AddressData, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import { type Account, Blockchain, getTextToken } from '@rotki/common';
import { omit, uniqBy } from 'es-toolkit';
import { hasAccountAddress } from '@/modules/accounts/account-helpers';
import { getAccountAddress, getAccountId } from '@/modules/accounts/account-utils';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { createAccount } from '@/modules/accounts/create-account';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { getNonRootAttrs, getRootAttrs } from '@/modules/core/common/helpers/attrs';
import AccountDisplay from '@/modules/shell/components/display/AccountDisplay.vue';
import TagDisplay from '@/modules/tags/TagDisplay.vue';

type AccountWithAddressData = BlockchainAccount<AddressData>;

type AccountWithExtra = AccountWithAddressData & { address: string; key: string };

defineOptions({
  inheritAttrs: false,
});

const modelValue = defineModel<AccountWithAddressData[]>({ required: true });

const {
  chains = [],
  customHint = '',
  dense = false,
  errorMessages = [],
  hideChainIcon = false,
  hideOnEmptyUsable = false,
  hint = false,
  label = '',
  loading = false,
  multichain = false,
  multiple = false,
  noDataText,
  outlined = false,
  required = false,
  showDetails = false,
  unique = false,
  usableAddresses = [],
} = defineProps<{
  label?: string;
  hint?: boolean;
  loading?: boolean;
  usableAddresses?: string[];
  multiple?: boolean;
  chains?: string[];
  outlined?: boolean;
  dense?: boolean;
  hideOnEmptyUsable?: boolean;
  multichain?: boolean;
  unique?: boolean;
  hideChainIcon?: boolean;
  errorMessages?: string[];
  showDetails?: boolean;
  customHint?: string;
  noDataText?: string;
  required?: boolean;
}>();

defineSlots<{
  default: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());
const { getAddressName } = useAddressNameResolution();

const [DefineAutocomplete, ReuseAutocomplete] = createReusableTemplate();

const accounts = computed<AccountWithAddressData[]>(() =>
  Object.values(get(accountsPerChain))
    .flatMap(x => x)
    .filter(hasAccountAddress),
);

const internalValue = computed<AccountWithExtra | AccountWithExtra[] | undefined>(() => {
  const accounts = get(modelValue).map(item => ({ ...item, address: getAccountAddress(item), key: getAccountId(item) }));
  if (multiple)
    return accounts;

  if (!accounts || accounts.length === 0)
    return undefined;

  return accounts[0];
});

const selectableAccounts = computed<AccountWithAddressData[]>(() => {
  const accountData = get(accounts);

  const filteredAccounts = chains.length === 0
    ? accountData
    : accountData.filter(({ chain }) => chain === 'ALL' || chains.includes(chain));

  const filteredByUnique: AccountWithAddressData[] = unique
    ? uniqBy(filteredAccounts, account => getAccountAddress(account))
    : filteredAccounts;

  if (multichain) {
    const entries: Record<string, number> = {};
    filteredByUnique.forEach((account) => {
      const address = getAccountAddress(account);
      if (entries[address])
        entries[address] += 1;
      else entries[address] = 1;
    });

    for (const address in entries) {
      const count = entries[address];
      if (count <= 1)
        continue;

      filteredByUnique.push(
        createAccount(
          {
            address,
            label: null,
            tags: null,
          },
          {
            chain: 'ALL',
            nativeAsset: '',
          },
        ),
      );
    }
  }

  return filteredByUnique;
});

const hintText = computed<string>(() => {
  const all = t('blockchain_account_selector.all');
  const selection = get(modelValue);
  if (Array.isArray(selection))
    return selection.length > 0 ? selection.length.toString() : all;

  return selection ? '1' : all;
});

const displayedAccounts = computed<AccountWithExtra[]>(() => {
  const accounts = [...get(selectableAccounts)].map(item => ({
    ...item,
    address: getAccountAddress(item),
    key: getAccountId(item),
  }));
  if (usableAddresses.length > 0)
    return accounts.filter(account => usableAddresses.includes(account.address));

  return hideOnEmptyUsable ? [] : accounts;
});

function filter(item: BlockchainAccount, queryText: string) {
  const chain = item.chain === 'ALL' ? Blockchain.ETH : item.chain;
  const text = getTextToken(getAddressName(getAccountAddress(item), chain) ?? '');
  const address = getTextToken(getAccountAddress(item));
  const query = getTextToken(queryText);

  const labelMatches = text.includes(query);
  const addressMatches = address.includes(query);

  if (labelMatches || addressMatches)
    return true;

  return item.tags
    ? item.tags
        .map(tag => getTextToken(tag))
        .join(' ')
        .includes(query)
    : false;
}

function filterOutElements<T extends AccountWithAddressData>(
  lastElement: T,
  nextValue: T[],
): T[] {
  if (lastElement.chain === 'ALL')
    return nextValue.filter(x => getAccountAddress(x) !== getAccountAddress(lastElement) || x.chain === 'ALL');

  return nextValue.filter(x => getAccountAddress(x) !== getAccountAddress(lastElement) || x.chain !== 'ALL');
}

function input(nextValue?: AccountWithExtra | AccountWithExtra[]) {
  const previousValue = get(modelValue);
  let result: AccountWithExtra[];
  if (Array.isArray(nextValue)) {
    const lastElement = nextValue.at(-1);
    if (lastElement && nextValue.length > previousValue.length)
      result = filterOutElements(lastElement, nextValue);
    else
      result = nextValue;
  }
  else {
    result = nextValue ? [nextValue] : [];
  }

  set(modelValue, result.map(item => omit(item, ['address', 'key'])));
}

function getAccount(account: AccountWithAddressData): Account {
  return {
    address: getAccountAddress(account),
    chain: account.chain,
  };
}
</script>

<template>
  <DefineAutocomplete>
    <RuiAutoComplete
      :model-value="internalValue"
      :options="displayedAccounts"
      :filter="filter"
      key-attr="key"
      text-attr="address"
      auto-select-first
      :loading="loading"
      :disabled="loading"
      :hide-details="!showDetails"
      hide-selected
      :hide-no-data="!hideOnEmptyUsable"
      :chips="multiple"
      :item-height="40"
      :required="required"
      :clearable="!required"
      :dense="dense"
      :variant="outlined ? 'outlined' : 'default'"
      :outlined="outlined"
      :hint="customHint"
      :label="label || t('blockchain_account_selector.default_label')"
      class="blockchain-account-selector"
      :error-messages="errorMessages"
      v-bind="getNonRootAttrs($attrs)"
      :no-data-text="noDataText || t('blockchain_account_selector.no_data')"
      return-object
      @update:model-value="input($event)"
    >
      <template #selection="{ item }">
        <AccountDisplay
          :account="getAccount(item)"
          :hide-chain-icon="hideChainIcon"
        />
      </template>
      <template #item="{ item }">
        <div class="grow py-1">
          <AccountDisplay
            :account="getAccount(item)"
            :hide-chain-icon="hideChainIcon"
          />
          <TagDisplay
            :class="hideChainIcon ? 'pl-8' : 'pl-[3.75rem]'"
            :tags="item.tags"
            small
          />
        </div>
      </template>
    </RuiAutoComplete>
  </DefineAutocomplete>

  <div
    v-if="!hint"
    class="bg-white dark:bg-dark-elevated"
    v-bind="getRootAttrs($attrs)"
  >
    <ReuseAutocomplete />
  </div>
  <RuiCard
    v-else
    variant="outlined"
    v-bind="getRootAttrs($attrs)"
  >
    <ReuseAutocomplete />
    <div
      v-if="hint"
      class="text-body-2 text-rui-text-secondary p-2"
    >
      {{ t('blockchain_account_selector.hint', { hintText }) }}
      <slot />
    </div>
  </RuiCard>
</template>
