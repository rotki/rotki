<script setup lang="ts">
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import { type BigNumber, Blockchain } from '@rotki/common';
import { FiatDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { useAssetLocationFields } from '@/modules/assets/use-asset-location-fields';
import { type AssetLocation, useAssetLocationsData } from '@/modules/assets/use-asset-locations-data';
import { arrayify } from '@/modules/core/common/data/array';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import LabeledAddressDisplay from '@/modules/shell/components/display/LabeledAddressDisplay.vue';
import PercentageDisplay from '@/modules/shell/components/display/PercentageDisplay.vue';
import TagDisplay from '@/modules/tags/TagDisplay.vue';

const { identifier } = defineProps<{ identifier: string }>();

const { t } = useI18n({ useScope: 'global' });

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
const addresses = ref<string[]>([]);

const {
  assetLocations,
  currencySymbol,
  detailsLoading,
  matchChain,
  totalValue,
  visibleAssetLocations,
} = useAssetLocationsData({
  addresses,
  identifier: () => identifier,
  locationFilter,
  onlyTags,
});

// Offered from the unfiltered breakdown, so the bar lists the locations and accounts this asset is
// held in rather than every location and account there is.
const fields = useAssetLocationFields(assetLocations);
const pillLabels = usePillBarLabels();

// Every pill here is param-bound, and this table filters what it already holds, so the bar's params
// are bridged straight to the three models instead of a request. An absent param clears its model:
// removing the pill is how the filter is turned off.
function toList(value: string | string[] | boolean | undefined): string[] {
  return value === undefined || typeof value === 'boolean' ? [] : arrayify(value);
}

const pillParams = computed<Record<string, string | string[] | boolean>>({
  get(): Record<string, string | string[] | boolean> {
    const location = get(locationFilter);
    const picked = get(addresses);
    const tags = get(onlyTags);
    return {
      ...(picked.length > 0 ? { addresses: picked } : {}),
      ...(location ? { location } : {}),
      ...(tags.length > 0 ? { tags } : {}),
    };
  },
  set(value: Record<string, string | string[] | boolean>): void {
    set(addresses, toList(value.addresses));
    set(locationFilter, toList(value.location)[0] ?? '');
    set(onlyTags, toList(value.tags));
  },
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

// An account is only held on a chain, so an exchange location and an account can never both match
// a row. Whichever was picked last wins, rather than leaving the user with an empty table.
watch(locationFilter, (location) => {
  if (location && !matchChain(location)) {
    set(addresses, []);
  }
});

watch(addresses, (picked) => {
  if (picked.length > 0 && !matchChain(get(locationFilter))) {
    set(locationFilter, '');
  }
});

watch([onlyTags, locationFilter, addresses], () => {
  setPage(1);
});
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('asset_locations.title') }}
    </template>
    <PillFilterBar
      v-model:params="pillParams"
      class="mb-4"
      :fields="fields"
      :labels="pillLabels"
    />
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
        <ValueDisplay :value="row.amount" />
      </template>
      <template #item.value="{ row }">
        <FiatDisplay :value="row.value" />
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
