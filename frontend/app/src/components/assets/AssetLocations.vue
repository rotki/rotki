<script setup lang="ts">
import type { AddressData, AssetBreakdown, BlockchainAccount } from '@/types/blockchain/accounts';
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import LabeledAddressDisplay from '@/components/display/LabeledAddressDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import TagFilter from '@/components/inputs/TagFilter.vue';
import TagDisplay from '@/components/tags/TagDisplay.vue';
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';
import { useSupportedChains } from '@/composables/info/chains';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useAssetBalancesBreakdown } from '@/modules/balances/use-asset-balances-breakdown';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatusStore } from '@/store/status';
import { isBlockchain } from '@/types/blockchain/chains';
import { CURRENCY_USD } from '@/types/currencies';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { type BigNumber, Blockchain, toSentenceCase } from '@rotki/common';

type AssetLocations = AssetLocation[];

interface AssetLocation extends AssetBreakdown {
  readonly account?: BlockchainAccount;
  readonly label: string;
}

const props = defineProps<{ identifier: string }>();

const { t } = useI18n({ useScope: 'global' });

const { identifier } = toRefs(props);

const sort = ref<DataTableSortData<AssetLocation>>({
  column: 'amount',
  direction: 'desc',
});

const pagination = ref({
  itemsPerPage: 10,
  page: 1,
});

const onlyTags = ref<string[]>([]);
const locationFilter = ref<string>('');
const selectedAccounts = ref<BlockchainAccount<AddressData>[]>([]);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { getAccountByAddress } = useBlockchainAccountsStore();
const { detailsLoading } = storeToRefs(useStatusStore());
const { assetPriceInfo } = useAggregatedBalances();
const { useAssetBreakdown } = useAssetBalancesBreakdown();
const { addressNameSelector } = useAddressesNamesStore();
const { getChainName, matchChain } = useSupportedChains();

const totalUsdValue = computed<BigNumber>(() => get(assetPriceInfo(identifier)).usdValue);

const assetLocations = computed<AssetLocations>(() => {
  const breakdowns = get(useAssetBreakdown(get(identifier)));
  return breakdowns.map((item: AssetBreakdown) => {
    const account = item.address ? getAccountByAddress(item.address, item.location) : undefined;
    return {
      ...item,
      account,
      label: account?.label ?? '',
    };
  });
});

const visibleAssetLocations = computed<AssetLocations>(() => {
  const locations = get(assetLocations).map(item => ({
    ...item,
    label:
      (isBlockchain(item.location) ? get(addressNameSelector(item.address, item.location)) : null)
      || item.label
      || item.address,
  }));

  const tagsFilter = get(onlyTags);
  const location = get(locationFilter);
  const accounts = get(selectedAccounts);

  return locations.filter((assetLocation) => {
    const tags = assetLocation.tags ?? [];
    const includedInTags = tagsFilter.every(tag => tags.includes(tag));
    const currentLocation = assetLocation.location;
    const locationToCheck = get(getChainName(currentLocation));
    const locationMatches = !location || locationToCheck === toSentenceCase(location);
    const accountMatches = accounts.length === 0 || accounts.some(account =>
      getAccountAddress(account) === assetLocation.address,
    );

    return includedInTags && locationMatches && accountMatches;
  });
});

function getPercentage(usdValue: BigNumber): string {
  const percentage = get(totalUsdValue).isZero() ? 0 : usdValue.div(get(totalUsdValue)).multipliedBy(100);

  return percentage.toFixed(2);
}

function setTablePagination(event: TablePaginationData | undefined) {
  if (!isDefined(event))
    return;

  const { limit, page } = event;
  set(pagination, {
    itemsPerPage: limit,
    page,
  });
}

function setPage(page: number) {
  set(pagination, {
    ...get(pagination),
    page,
  });
}

const headers = computed<DataTableColumn<AssetLocation>[]>(() => {
  const visibleItemsLength = get(visibleAssetLocations).length;
  const eth2Length = get(visibleAssetLocations).filter(account => account?.location === Blockchain.ETH2).length;

  const labelAccount = t('common.account');
  const labelValidator = t('asset_locations.header.validator');

  let label: string;
  if (eth2Length === 0)
    label = labelAccount;
  else if (eth2Length === visibleItemsLength)
    label = labelValidator;
  else label = `${labelAccount} / ${labelValidator}`;

  return [{
    align: 'center',
    cellClass: 'w-36',
    key: 'location',
    label: t('common.location'),
    sortable: true,
  }, {
    key: 'label',
    label,
    sortable: true,
  }, {
    align: 'end',
    key: 'amount',
    label: t('common.amount'),
    sortable: true,
  }, {
    align: 'end',
    key: 'usdValue',
    label: t('asset_locations.header.value', {
      symbol: get(currencySymbol) ?? CURRENCY_USD,
    }),
    sortable: true,
  }, {
    align: 'end',
    key: 'percentage',
    label: t('asset_locations.header.percentage'),
    sortable: false,
  }];
});

useRememberTableSorting<AssetLocation>(TableId.ASSET_LOCATION, sort, headers);

watch(locationFilter, (location) => {
  if (location && !matchChain(location)) {
    set(selectedAccounts, []);
  }
});

watch(selectedAccounts, (accounts) => {
  if (accounts.length > 0 && !matchChain(get(locationFilter))) {
    set(locationFilter, '');
  }
});

watch([onlyTags, locationFilter, selectedAccounts], () => {
  setPage(1);
});
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('asset_locations.title') }}
    </template>
    <div class="flex flex-col md:flex-row justify-end gap-2">
      <div class="w-full md:w-[20rem]">
        <LocationSelector
          v-model="locationFilter"
          :label="t('common.location')"
          dense
          clearable
          hide-details
        />
      </div>

      <BlockchainAccountSelector
        v-model="selectedAccounts"
        class="w-full md:w-[20rem]"
        variant="outlined"
        dense
        multichain
        hide-chain-icon
        unique
      />

      <div class="w-full md:w-[20rem]">
        <TagFilter v-model="onlyTags" />
      </div>
    </div>
    <RuiDataTable
      v-model:sort="sort"
      :pagination="{
        page: pagination.page,
        limit: pagination.itemsPerPage,
        total: visibleAssetLocations.length,
      }"
      :cols="headers"
      :rows="visibleAssetLocations"
      outlined
      dense
      row-attr="location"
      :loading="detailsLoading"
      @update:pagination="setTablePagination($event)"
    >
      <template #item.location="{ row }">
        <LocationDisplay
          :identifier="row.location"
          :detail-path="row.detailPath"
          class="py-2"
        />
      </template>
      <template #item.label="{ row }">
        <div class="py-4">
          <LabeledAddressDisplay
            v-if="row.account"
            :account="row.account"
          />
          <TagDisplay
            v-if="row.tags"
            :tags="row.tags"
            small
          />
        </div>
      </template>
      <template #item.amount="{ row }">
        <AmountDisplay :value="row.amount" />
      </template>
      <template #item.usdValue="{ row }">
        <AmountDisplay
          show-currency="symbol"
          :amount="row.amount"
          :price-asset="identifier"
          fiat-currency="USD"
          :value="row.usdValue"
        />
      </template>
      <template #item.percentage="{ row }">
        <PercentageDisplay
          :value="getPercentage(row.usdValue)"
          :asset-padding="0.1"
        />
      </template>
    </RuiDataTable>
  </RuiCard>
</template>
