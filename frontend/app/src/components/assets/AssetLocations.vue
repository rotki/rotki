<script setup lang="ts">
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import { type BigNumber, Blockchain } from '@rotki/common';
import { type AssetLocation, useAssetLocationsData } from '@/components/assets/use-asset-locations-data';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import LabeledAddressDisplay from '@/components/display/LabeledAddressDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import TagFilter from '@/components/inputs/TagFilter.vue';
import TagDisplay from '@/components/tags/TagDisplay.vue';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { CURRENCY_USD } from '@/types/currencies';

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

const {
  currencySymbol,
  detailsLoading,
  matchChain,
  totalValue,
  visibleAssetLocations,
} = useAssetLocationsData({
  identifier,
  locationFilter,
  onlyTags,
  selectedAccounts,
});

function getPercentage(value: BigNumber): string {
  const percentage = get(totalValue).isZero() ? 0 : value.div(get(totalValue)).multipliedBy(100);

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
    key: 'value',
    label: t('common.value_in_symbol', {
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
      <template #item.value="{ row }">
        <AmountDisplay
          show-currency="symbol"
          :amount="row.amount"
          :price-asset="identifier"
          force-currency
          :value="row.value"
        />
      </template>
      <template #item.percentage="{ row }">
        <PercentageDisplay
          :value="getPercentage(row.value)"
          :asset-padding="0.1"
        />
      </template>
    </RuiDataTable>
  </RuiCard>
</template>
