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

/** Which accounts the selector offers. These are consumed together by `selectableAccounts`. */
interface AccountSelectorSource {
  chains?: string[];
  usableAddresses?: string[];
  multichain?: boolean;
  unique?: boolean;
  hideOnEmptyUsable?: boolean;
}

/** How the wrapped field presents and validates. Passed through to RuiAutoComplete. */
interface AccountSelectorField {
  label?: string;
  hint?: string;
  errorMessages?: string[];
  required?: boolean;
  showDetails?: boolean;
  noDataText?: string;
  dense?: boolean;
}

defineOptions({
  inheritAttrs: false,
});

const modelValue = defineModel<AccountWithAddressData[]>({ required: true });

const {
  field,
  hideChainIcon = false,
  loading = false,
  source,
} = defineProps<{
  source?: AccountSelectorSource;
  field?: AccountSelectorField;
  loading?: boolean;
  hideChainIcon?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());
const { getAddressName } = useAddressNameResolution();

// Every field is read with `??` rather than by spreading the bag over a defaults object: a caller
// forwarding its own optional value passes a present key holding `undefined`, which a spread takes
// as the value and the default would be lost.
const chains = computed<string[]>(() => source?.chains ?? []);

const usableAddresses = computed<string[]>(() => source?.usableAddresses ?? []);

const hideOnEmptyUsable = computed<boolean>(() => source?.hideOnEmptyUsable ?? false);

const errorMessages = computed<string[]>(() => field?.errorMessages ?? []);

const required = computed<boolean>(() => field?.required ?? false);

const hideDetails = computed<boolean>(() => !(field?.showDetails ?? false));

const dense = computed<boolean>(() => field?.dense ?? false);

const label = computed<string>(() => field?.label || t('blockchain_account_selector.default_label'));

const noDataText = computed<string>(() => field?.noDataText || t('blockchain_account_selector.no_data'));

const accounts = computed<AccountWithAddressData[]>(() =>
  Object.values(get(accountsPerChain))
    .flatMap(x => x)
    .filter(hasAccountAddress),
);

const internalValue = computed<AccountWithExtra | undefined>(() => {
  const [first] = get(modelValue);
  if (!first)
    return undefined;

  return { ...first, address: getAccountAddress(first), key: getAccountId(first) };
});

const selectableAccounts = computed<AccountWithAddressData[]>(() => {
  const accountData = get(accounts);
  const selectedChains = get(chains);

  const filteredAccounts = selectedChains.length === 0
    ? accountData
    : accountData.filter(({ chain }) => chain === 'ALL' || selectedChains.includes(chain));

  const filteredByUnique: AccountWithAddressData[] = source?.unique
    ? uniqBy(filteredAccounts, account => getAccountAddress(account))
    : filteredAccounts;

  if (source?.multichain) {
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

const displayedAccounts = computed<AccountWithExtra[]>(() => {
  const accounts = Array.from(get(selectableAccounts), item => ({
    ...item,
    address: getAccountAddress(item),
    key: getAccountId(item),
  }));
  const usable = get(usableAddresses);
  if (usable.length > 0)
    return accounts.filter(account => usable.includes(account.address));

  return get(hideOnEmptyUsable) ? [] : accounts;
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

// The model stays an array so callers keep their shape, but the selector is single-select:
// RuiAutoComplete derives multi-select from an array model value and `internalValue` never is one.
function input(nextValue?: AccountWithExtra): void {
  set(modelValue, nextValue ? [omit(nextValue, ['address', 'key'])] : []);
}

function getAccount(account: AccountWithAddressData): Account {
  return {
    address: getAccountAddress(account),
    chain: account.chain,
  };
}
</script>

<template>
  <div
    class="bg-white dark:bg-dark-elevated"
    v-bind="getRootAttrs($attrs)"
  >
    <RuiAutoComplete
      :model-value="internalValue"
      :options="displayedAccounts"
      :filter="filter"
      key-attr="key"
      text-attr="address"
      auto-select-first
      :loading="loading"
      :disabled="loading"
      :hide-details="hideDetails"
      hide-selected
      :hide-no-data="!hideOnEmptyUsable"
      :item-height="40"
      :required="required"
      :clearable="!required"
      :dense="dense"
      variant="outlined"
      outlined
      :hint="field?.hint"
      :label="label"
      class="blockchain-account-selector"
      :error-messages="errorMessages"
      v-bind="getNonRootAttrs($attrs)"
      :no-data-text="noDataText"
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
  </div>
</template>
