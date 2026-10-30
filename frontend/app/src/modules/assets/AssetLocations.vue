<script setup lang="ts">
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import { type BigNumber, Blockchain } from '@rotki/common';
import { FiatDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import { assetLocationParams } from '@/modules/assets/asset-location-fields';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useAssetLocationFields } from '@/modules/assets/use-asset-location-fields';
import { type AssetLocation, useAssetLocationsData } from '@/modules/assets/use-asset-locations-data';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
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
    cellClass: 'w-48',
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
    cellClass: 'font-medium',
    key: 'value',
    label: t('common.value'),
    sortable: true,
  }, {
    align: 'end',
    cellClass: 'text-rui-text-secondary',
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
  <section class="flex flex-col gap-3">
    <h2 class="text-base font-semibold text-rui-text">
      {{ t('asset_locations.title') }}
    </h2>
    <TableFrame>
      <template #toolbar>
        <PillFilterBar
          v-model:params="pillParams"
          class="flex-1 min-w-64"
          :fields="fields"
          :labels="pillLabels"
        />
      </template>
      <RuiDataTable
        v-model:sort="sort"
        :pagination="{
          page: pagination.page,
          limit: pagination.itemsPerPage,
          total: visibleAssetLocations.length,
        }"
        :cols="headers"
        :rows="visibleAssetLocations"
        dense
        row-attr="location"
        :loading="detailsLoading"
        @update:pagination="setTablePagination($event)"
      >
        <template #item.location="{ row }">
          <LocationDisplay
            :identifier="row.location"
            :detail-path="row.detailPath"
            horizontal
            size="20px"
          />
        </template>
        <template #item.label="{ row }">
          <div class="flex flex-wrap items-center gap-2 py-2">
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
          <i18n-t
            v-if="row.awaitingClaim"
            keypath="claims.account_awaiting"
            scope="global"
            tag="div"
            class="flex items-center justify-end gap-1 text-xs text-rui-text-secondary"
            data-testid="asset-location-awaiting-claim"
          >
            <template #amount>
              <ValueDisplay :value="row.awaitingClaim" />
            </template>
          </i18n-t>
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
    </TableFrame>
  </section>
</template>
