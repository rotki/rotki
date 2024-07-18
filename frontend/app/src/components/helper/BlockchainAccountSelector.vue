<script setup lang="ts">
import { uniqBy } from 'lodash-es';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { objectOmit } from '@vueuse/shared';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';

type AccountWithAddressData = BlockchainAccount<AddressData>;

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    label?: string;
    hint?: boolean;
    loading?: boolean;
    usableAddresses?: string[];
    multiple?: boolean;
    modelValue: AccountWithAddressData[];
    chains?: string[];
    outlined?: boolean;
    dense?: boolean;
    noPadding?: boolean;
    hideOnEmptyUsable?: boolean;
    multichain?: boolean;
    unique?: boolean;
    hideChainIcon?: boolean;
    errorMessages?: string[];
    showDetails?: boolean;
    customHint?: string;
  }>(),
  {
    label: '',
    hint: false,
    loading: false,
    usableAddresses: () => [],
    multiple: false,
    chains: () => [],
    outlined: false,
    dense: false,
    noPadding: false,
    hideOnEmptyUsable: false,
    multichain: false,
    unique: false,
    hideChainIcon: false,
    errorMessages: () => [],
    showDetails: false,
    customHint: '',
  },
);

const emit = defineEmits<{
  (e: 'update:model-value', value: AccountWithAddressData[]): void;
}>();

const { chains, usableAddresses, hideOnEmptyUsable, multiple, multichain, unique } = toRefs(props);

const { t } = useI18n();

const { accounts: accountsPerChain } = storeToRefs(useBlockchainStore());

const accounts = computed<AccountWithAddressData[]>(() =>
  Object.values(get(accountsPerChain))
    .flatMap(x => x)
    .filter(hasAccountAddress),
);

const internalValue = computed(() => {
  const accounts = props.modelValue.map(item => ({
    ...item,
    address: getAccountAddress(item),
    key: getAccountId(item),
  }));
  if (get(multiple))
    return accounts;

  if (!accounts || accounts.length === 0)
    return null;

  return accounts[0];
});

const selectableAccounts = computed<AccountWithAddressData[]>(() => {
  const filteredChains = get(chains);
  const accountData = get(accounts);

  const blockchainAccounts: AccountWithAddressData[] = get(unique)
    ? uniqBy(accountData, account => getAccountAddress(account))
    : accountData;

  const filteredAccounts
    = filteredChains.length === 0
      ? blockchainAccounts
      : blockchainAccounts.filter(({ chain }) => chain === 'ALL' || filteredChains.includes(chain));

  if (get(multichain)) {
    const entries: Record<string, number> = {};
    filteredAccounts.forEach((account) => {
      const address = getAccountAddress(account);
      if (entries[address])
        entries[address] += 1;
      else entries[address] = 1;
    });

    for (const address in entries) {
      const count = entries[address];
      if (count <= 1)
        continue;

      filteredAccounts.push(
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

  return filteredAccounts;
});

const hintText = computed(() => {
  const all = t('blockchain_account_selector.all').toString();
  const selection = props.modelValue;
  if (Array.isArray(selection))
    return selection.length > 0 ? selection.length.toString() : all;

  return selection ? '1' : all;
});

const displayedAccounts = computed<AccountWithAddressData[]>(() => {
  const addresses = get(usableAddresses);
  const accounts = [...get(selectableAccounts)].map(item => ({
    ...item,
    address: getAccountAddress(item),
    key: getAccountId(item),
  }));
  if (addresses.length > 0)
    return accounts.filter(account => addresses.includes(account.address));

  return get(hideOnEmptyUsable) ? [] : accounts;
});

const { addressNameSelector } = useAddressesNamesStore();

function filter(item: BlockchainAccount, queryText: string) {
  const chain = item.chain === 'ALL' ? Blockchain.ETH : item.chain;
  const text = getTextToken(get(addressNameSelector(getAccountAddress(item), chain)) ?? '');
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

function filterOutElements(
  lastElement: AccountWithAddressData,
  nextValue: AccountWithAddressData[],
): AccountWithAddressData[] {
  if (lastElement.chain === 'ALL')
    return nextValue.filter(x => getAccountAddress(x) !== getAccountAddress(lastElement) || x.chain === 'ALL');

  return nextValue.filter(x => getAccountAddress(x) !== getAccountAddress(lastElement) || x.chain !== 'ALL');
}

function input(nextValue: null | AccountWithAddressData | AccountWithAddressData[]) {
  const previousValue = props.modelValue;
  let result: AccountWithAddressData[];
  if (Array.isArray(nextValue)) {
    const lastElement = nextValue.at(-1);
    if (lastElement && nextValue.length > previousValue.length)
      result = filterOutElements(lastElement, nextValue);
    else result = nextValue;
  }
  else {
    result = nextValue ? [nextValue] : [];
  }

  emit('update:model-value', result);
}

const [DefineAutocomplete, ReuseAutocomplete] = createReusableTemplate();
const attrs = useAttrs();
</script>

<template>
  <DefineAutocomplete>
    <RuiAutoComplete
      :model-value="internalValue"
      :options="displayedAccounts"
      :filter="filter"
      auto-select-first
      :loading="loading"
      :disabled="loading"
      :hide-details="!showDetails"
      hide-selected
      :hide-no-data="!hideOnEmptyUsable"
      :chips="multiple"
      :item-height="40"
      clearable
      :dense="dense"
      :variant="outlined ? 'outlined' : 'default'"
      :outlined="outlined"
      :hint="customHint"
      key-attr="key"
      :label="label || t('blockchain_account_selector.default_label')"
      class="blockchain-account-selector"
      :error-messages="errorMessages"
      v-bind="objectOmit(attrs, ['class'])"
      :no-data-text="t('blockchain_account_selector.no_data')"
      return-object
      @update:model-value="input($event)"
    >
      <template #selection="{ item }">
        <AccountDisplay
          :account="item"
          :hide-chain-icon="hideChainIcon"
        />
      </template>
      <template #item="{ item }">
        <div class="grow py-1">
          <AccountDisplay
            :account="item"
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
    class="bg-white dark:bg-[#1E1E1E]"
    :class="attrs.class"
  >
    <ReuseAutocomplete />
  </div>
  <RuiCard
    v-else
    variant="outlined"
    :class="attrs.class"
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
