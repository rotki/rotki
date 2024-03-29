<script setup lang="ts">
import { uniqBy } from 'lodash-es';
import { Blockchain } from '@rotki/common/lib/blockchain';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';

type Account = BlockchainAccount<AddressData>;

const props = withDefaults(
  defineProps<{
    label?: string;
    hint?: boolean;
    loading?: boolean;
    usableAddresses?: string[];
    multiple?: boolean;
    value: Account[];
    chains: string[];
    outlined?: boolean;
    dense?: boolean;
    noPadding?: boolean;
    hideOnEmptyUsable?: boolean;
    multichain?: boolean;
    unique?: boolean;
    hideChainIcon?: boolean;
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
  },
);

const emit = defineEmits<{
  (e: 'input', value: Account[]): void;
}>();

const {
  chains,
  value,
  usableAddresses,
  hideOnEmptyUsable,
  multiple,
  multichain,
  unique,
} = toRefs(props);

const search = ref('');
const { t } = useI18n();

const { accounts: accounsPerChain } = storeToRefs(useBlockchainStore());

const accounts = computed<Account[]>(
  () => Object.values(get(accounsPerChain)).flatMap(x => x).filter(hasAccountAddress),
);

const internalValue = computed(() => {
  const accounts = get(value);
  if (get(multiple))
    return accounts;

  if (!accounts || accounts.length === 0)
    return null;

  return accounts[0];
});

const selectableAccounts = computed<Account[]>(() => {
  const filteredChains = get(chains);
  const accountData = get(accounts);
  const blockchainAccounts: Account[] = get(unique)
    ? uniqBy(accountData, account => getAccountAddress(account))
    : accountData;

  const filteredAccounts = filteredChains.length === 0
    ? blockchainAccounts
    : blockchainAccounts.filter(
      ({ chain }) => chain === 'ALL' || filteredChains.includes(chain),
    );

  if (get(multichain)) {
    const entries: Record<string, number> = {};
    filteredAccounts.forEach((account) => {
      const address = getAccountAddress(account);
      if (entries[address])
        entries[address] += 1;
      else
        entries[address] = 1;
    });

    for (const address in entries) {
      const count = entries[address];
      if (count <= 1)
        continue;

      filteredAccounts.push(createAccount({
        address,
        label: null,
        tags: null,
      }, {
        chain: 'ALL',
        nativeAsset: '',
      }));
    }
  }

  return filteredAccounts;
});

const hintText = computed(() => {
  const all = t('blockchain_account_selector.all').toString();
  const selection = get(value);
  if (Array.isArray(selection))
    return selection.length > 0 ? selection.length.toString() : all;

  return selection ? '1' : all;
});

const displayedAccounts = computed<BlockchainAccount[]>(() => {
  const addresses = get(usableAddresses);
  const accounts = get(selectableAccounts);
  if (addresses.length > 0)
    return accounts.filter(account => addresses.includes(getAccountAddress(account)));

  return get(hideOnEmptyUsable) ? [] : accounts;
});

const { addressNameSelector } = useAddressesNamesStore();

function filter(item: BlockchainAccount, queryText: string) {
  const chain = item.chain === 'ALL' ? Blockchain.ETH : item.chain;
  const text = (get(addressNameSelector(getAccountAddress(item), chain)) ?? '').toLowerCase();
  const address = getAccountAddress(item).toLocaleLowerCase();
  const query = queryText.toLocaleLowerCase();

  const labelMatches = text.includes(query);
  const addressMatches = address.includes(query);

  const tagMatches = item.tags
    ? item.tags
      .map(tag => tag.toLocaleLowerCase())
      .join(' ')
      .includes(query)
    : false;

  return labelMatches || tagMatches || addressMatches;
}

function filterOutElements(
  lastElement: Account,
  nextValue: Account[],
): Account[] {
  if (lastElement.chain === 'ALL') {
    return nextValue.filter(
      x => getAccountAddress(x) !== getAccountAddress(lastElement) || x.chain === 'ALL',
    );
  }
  return nextValue.filter(
    x => getAccountAddress(x) !== getAccountAddress(lastElement) || x.chain !== 'ALL',
  );
}

function input(nextValue: null | Account | Account[]) {
  const previousValue = get(value);
  let result: Account[];
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

  emit('input', result);
}

const getItemKey = (item: Account) => getAccountId(item);

const [DefineAutocomplete, ReuseAutocomplete] = createReusableTemplate();
</script>

<template>
  <div>
    <DefineAutocomplete>
      <VAutocomplete
        :value="internalValue"
        :items="displayedAccounts"
        :filter="filter"
        auto-select-first
        :search-input.sync="search"
        :multiple="multiple"
        :loading="loading"
        :disabled="loading"
        hide-details
        hide-selected
        :hide-no-data="!hideOnEmptyUsable"
        return-object
        chips
        single-line
        clearable
        :dense="dense"
        :outlined="outlined"
        :item-text="getItemKey"
        :open-on-clear="false"
        :label="label ? label : t('blockchain_account_selector.default_label')"
        :class="outlined ? 'blockchain-account-selector--outlined' : null"
        class="blockchain-account-selector"
        @input="input($event)"
      >
        <template #no-data>
          <span class="text-caption px-2">
            {{ t('blockchain_account_selector.no_data') }}
          </span>
        </template>
        <template #selection="data">
          <RuiChip
            v-if="multiple"
            :key="data.item.chain + data.item.address"
            v-bind="data.attrs"
            clickable
            closeable
            size="sm"
            class="m-0.5"
            @click:close="data.parent.selectItem(data.item)"
          >
            <AccountDisplay
              :account="data.item"
              :hide-chain-icon="hideChainIcon"
            />
          </RuiChip>
          <div
            v-else
            class="overflow-x-hidden"
          >
            <AccountDisplay
              :account="data.item"
              :hide-chain-icon="hideChainIcon"
              class="pr-2"
            />
          </div>
        </template>
        <template #item="data">
          <div
            class="blockchain-account-selector__list__item flex items-center justify-between grow"
          >
            <div class="blockchain-account-selector__list__item__address-label">
              <RuiChip
                class="text-truncate"
                size="sm"
              >
                <AccountDisplay
                  :account="data.item"
                  :hide-chain-icon="hideChainIcon"
                />
              </RuiChip>
            </div>
            <TagDisplay
              class="mb-1"
              :tags="data.item.tags"
              :small="true"
            />
          </div>
        </template>
      </VAutocomplete>
    </DefineAutocomplete>

    <div
      v-if="!hint"
      class="bg-white dark:bg-[#1E1E1E]"
    >
      <ReuseAutocomplete />
    </div>
    <RuiCard
      v-else
      variant="outlined"
      v-bind="$attrs"
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
  </div>
</template>

<style scoped lang="scss">
.blockchain-account-selector {
  &__list {
    &__item {
      max-width: 100%;
    }
  }

  /* stylelint-disable selector-class-pattern,selector-nested-pattern */

  :deep(.v-select__selections) {
    padding: 2px;

    input {
      min-width: 0;
    }
  }

  /* stylelint-enable selector-class-pattern,selector-nested-pattern */
}
</style>
