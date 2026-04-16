<script setup lang="ts">
import type { AddressData, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { LocationLabel } from '@/modules/common/location';
import { getTextToken } from '@rotki/common';
import AccountDisplay from '@/components/display/AccountDisplay.vue';
import LocationIcon from '@/components/history/LocationIcon.vue';
import TagDisplay from '@/components/tags/TagDisplay.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { hasAccountAddress } from '@/modules/accounts/account-helpers';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useAddressNameResolution } from '@/modules/address-names/use-address-name-resolution';
import { useHistoryStore } from '@/modules/history/use-history-store';

defineOptions({
  name: 'LocationLabelSelector',
  inheritAttrs: false,
});

const modelValue = defineModel<string[] | string>({
  required: true,
  set: (val: string[] | string | undefined) => val ?? '',
});

const { options } = defineProps<{
  options?: LocationLabel[];
  noTruncate?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
const { locationLabels: storeLocationLabels } = storeToRefs(useHistoryStore());

const locationLabelOptions = computed<LocationLabel[]>(() => options ?? get(storeLocationLabels));
const { allTxChainsInfo, matchChain } = useSupportedChains();
const txChainIds = useArrayMap(allTxChainsInfo, x => x.id);

const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());
const { getAddressName } = useAddressNameResolution();

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

  const text = getTextToken(getAddressName(item.locationLabel, chain) ?? '');

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
      :no-truncate="noTruncate"
    />
    <div
      v-else
      class="flex items-center gap-2"
      :class="{ 'py-[5px]': !dense }"
    >
      <LocationIcon
        :item="item.location"
        class="overflow-hidden rounded-sm"
        :class="dense ? '!size-4' : '!size-6'"
        :size="dense ? '0.875rem' : '1.25rem'"
        icon
      />
      {{ item.locationLabel }}
    </div>
  </DefineLocationItem>
  <RuiAutoComplete
    v-model="modelValue"
    :options="locationLabelOptions"
    :item-height="40"
    clearable
    key-attr="locationLabel"
    text-attr="locationLabel"
    :filter="filter"
    :label="t('transactions.filter.account')"
    variant="outlined"
    v-bind="$attrs"
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
