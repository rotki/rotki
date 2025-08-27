<script setup lang="ts">
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { LocationLabel } from '@/types/location';
import { getTextToken } from '@rotki/common';
import AccountDisplay from '@/components/display/AccountDisplay.vue';
import LocationIcon from '@/components/history/LocationIcon.vue';
import TagDisplay from '@/components/tags/TagDisplay.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useHistoryStore } from '@/store/history';
import { hasAccountAddress } from '@/utils/blockchain/accounts';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';

defineOptions({
  name: 'LocationLabelSelector',
});

const modelValue = defineModel<string[]>({ required: true });

const { t } = useI18n();
const { locationLabels: locationLabelOptions } = storeToRefs(useHistoryStore());
const { allTxChainsInfo, matchChain } = useSupportedChains();
const txChainIds = useArrayMap(allTxChainsInfo, x => x.id);

const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());
const { addressNameSelector } = useAddressesNamesStore();

const accounts = computed<BlockchainAccount<AddressData>[]>(() =>
  Object.values(get(accountsPerChain))
    .flatMap(x => x)
    .filter(hasAccountAddress),
);

function getBlockchainLocation(location: string): string | undefined {
  const chain = matchChain(location);
  if (!chain)
    return undefined;

  if (!get(txChainIds).includes(chain))
    return undefined;

  return chain;
}

function getTags(item: LocationLabel): string[] {
  const chain = getBlockchainLocation(item.location);

  if (!chain)
    return [];

  const registeredAccounts = get(accounts).filter(acc => getAccountAddress(acc) === item.locationLabel && acc.chain === chain);

  if (registeredAccounts.length === 0) {
    return [];
  }

  return registeredAccounts[0].tags || [];
}

function filter(item: LocationLabel, queryText: string): boolean {
  const locationLabel = getTextToken(item.locationLabel);
  const query = getTextToken(queryText);

  const locationLabelMatches = locationLabel.includes(query);

  if (locationLabelMatches) {
    return true;
  }

  const chain = getBlockchainLocation(item.location);

  if (!chain) {
    return false;
  }

  const text = getTextToken(get(addressNameSelector(item.locationLabel, chain)) ?? '');

  const labelMatches = text.includes(query);

  if (labelMatches) {
    return true;
  }

  const tags = getTags(item);
  return tags
    ? tags
        .map(tag => getTextToken(tag))
        .join(' ')
        .includes(query)
    : false;
}

const [DefineLocationItem, ReuseLocationItem] = createReusableTemplate<{ item: LocationLabel; dense: boolean }>();
</script>

<template>
  <DefineLocationItem #default="{ item, dense }">
    <AccountDisplay
      v-if="getBlockchainLocation(item.location)"
      :class="{ 'py-1': !dense }"
      :size="dense ? '16px' : '24px'"
      :account="{ address: item.locationLabel, chain: getBlockchainLocation(item.location)! }"
      hide-chain-icon
    />
    <div
      v-else
      class="flex items-center "
      :class="dense ? 'pl-0.5 gap-2' : 'py-[5.5px] gap-3'"
    >
      <LocationIcon
        :item="item.location"
        horizontal
        :size="dense ? '1rem' : '1.25rem'"
        icon
      />
      {{ item.locationLabel }}
    </div>
  </DefineLocationItem>
  <RuiAutoComplete
    v-model="modelValue"
    class="w-[18rem]"
    :options="locationLabelOptions"
    hide-details
    :item-height="40"
    dense
    clearable
    chips
    key-attr="locationLabel"
    text-attr="locationLabel"
    :filter="filter"
    :label="t('transactions.filter.account')"
    variant="outlined"
  >
    <template #selection="{ item }">
      <ReuseLocationItem
        :item="item"
        :dense="true"
      />
    </template>

    <template #item="{ item }">
      <ReuseLocationItem
        :item="item"
        :dense="false"
      />
      <TagDisplay
        class="pl-8 !mt-0"
        :tags="getTags(item)"
        small
      />
    </template>
  </RuiAutoComplete>
</template>
