<script setup lang="ts">
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import { type BigNumber, Blockchain } from '@rotki/common';
import { FiatDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { assetLocationParams } from '@/modules/assets/asset-location-fields';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useAssetLocationFields } from '@/modules/assets/use-asset-location-fields';
import { type AssetLocation, useAssetLocationsData } from '@/modules/assets/use-asset-locations-data';
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

const { isPricePending } = usePriceUtils();

const valuePending = computed<boolean>(() => isPricePending(identifier));

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

const fields = useAssetLocationFields(assetLocations);
const pillLabels = usePillBarLabels();

const pillParams = assetLocationParams(addresses, locationFilter, onlyTags);

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

/**
 * Keeps the location and account filters mutually exclusive, clearing whichever was set first.
 *
 * @remarks
 * An account is only ever held on a chain, so an exchange location and an account can never both
 * match the same row: leaving both set would empty the table. Clearing the older pill means the
 * one the user picked last is the one that takes effect.
 */
function keepLocationAndAccountsExclusive(): void {
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
}

keepLocationAndAccountsExclusive();

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
        <FiatDisplay
          :value="row.value"
          :loading="valuePending"
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
