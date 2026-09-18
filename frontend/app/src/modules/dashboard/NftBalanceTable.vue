<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import { AssetAmountDisplay, FiatDisplay } from '@/modules/assets/amount-display/components';
import NftDetails from '@/modules/balances/nft/NftDetails.vue';
import { useNftData } from '@/modules/balances/non-fungible/use-nft-data';
import { useTableEmptyState } from '@/modules/core/table/use-table-empty-state';
import DashboardExpandableTable from '@/modules/dashboard/DashboardExpandableTable.vue';
import VisibleColumnsSelector from '@/modules/dashboard/VisibleColumnsSelector.vue';
import { DashboardTableType } from '@/modules/settings/types/frontend-settings';
import PercentageDisplay from '@/modules/shell/components/display/PercentageDisplay.vue';
import RowAppend from '@/modules/shell/components/RowAppend.vue';

/**
 * Attributes are forwarded explicitly in the template below, since with no nfts this section renders
 * a comment root, which vue cannot inherit onto and warns about.
 */
defineOptions({ inheritAttrs: false });

const nonFungibleRoute: RouteLocationRaw = { name: '/balances/non-fungible/' };
const group = DashboardTableType.NFT;

const { t } = useI18n({ useScope: 'global' });

const {
  cols,
  currencySymbol,
  data,
  dataLoading,
  error,
  fetchData,
  found,
  percentageOfCurrentGroup,
  percentageOfTotalNetValue,
  refreshNonFungibleBalances,
  sectionLoading,
  sort,
  pagination,
  totalValue,
} = useNftData({ dashboard: true });

const emptyState = useTableEmptyState({ error });

onMounted(async () => {
  await fetchData();
  await refreshNonFungibleBalances();
});

/**
 * The section is only worth showing once we know there is at least one nft. `found` starts at zero and the fetch
 * happens on mount, so this also keeps an empty table from flashing before the first response arrives.
 */
const hasBalances = computed<boolean>(() => get(found) > 0);

const fitsOnePage = computed<boolean>(() => get(found) <= get(pagination).limit);

watch(sectionLoading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading)
    await fetchData();
});
</script>

<template>
  <DashboardExpandableTable
    v-if="hasBalances"
    v-bind="$attrs"
    :count="found"
  >
    <template #title>
      {{ t('nft_balance_table.title') }}
    </template>
    <template #titleActions>
      <RouterLink :to="nonFungibleRoute">
        <RuiButton
          variant="text"
          icon
          size="sm"
          :aria-label="t('nft_balance_table.open_page')"
        >
          <RuiIcon
            name="lu-chevron-right"
            size="18"
          />
        </RuiButton>
      </RouterLink>
    </template>
    <template #details>
      <VisibleColumnsSelector
        :group="group"
        size="sm"
      />
    </template>
    <template #shortDetails>
      <FiatDisplay
        v-if="totalValue"
        :value="totalValue"
        class="text-h6 font-bold"
      />
    </template>

    <RuiDataTable
      v-model:sort.external="sort"
      v-model:pagination.external="pagination"
      :cols="cols"
      :rows="data"
      :loading="dataLoading"
      :empty="emptyState"
      row-attr="id"
      sticky-header
      dense
      :hide-default-header="fitsOnePage"
      :hide-default-footer="fitsOnePage"
      class="!rounded-t-none"
      :class="{ 'border-t border-default': !fitsOnePage }"
    >
      <template #item.name="{ row }">
        <NftDetails
          :identifier="row.id"
          size="32px"
        />
      </template>
      <template #item.priceInAsset="{ row }">
        <AssetAmountDisplay
          v-if="row.priceAsset !== currencySymbol"
          :amount="row.priceInAsset"
          :asset="row.priceAsset"
        />
        <span v-else>-</span>
      </template>
      <template #item.price="{ row }">
        <FiatDisplay
          :value="row.price"
          no-scramble
        />
      </template>
      <template #item.percentageOfTotalNetValue="{ row }">
        <PercentageDisplay
          :value="percentageOfTotalNetValue(row.price)"
          :asset-padding="0.1"
        />
      </template>
      <template #item.percentageOfTotalCurrentGroup="{ row }">
        <PercentageDisplay
          :value="percentageOfCurrentGroup(row.price)"
          :asset-padding="0.1"
        />
      </template>
      <template #body.append>
        <RowAppend
          label-colspan="2"
          :label="t('common.total')"
          :right-patch-colspan="cols.length - 3"
          :is-mobile="false"
          class-name="text-sm border-t border-default [&>td]:px-4 [&>td]:py-3"
        >
          <FiatDisplay
            v-if="totalValue"
            :value="totalValue"
            class="font-bold"
          />
        </RowAppend>
      </template>
    </RuiDataTable>
  </DashboardExpandableTable>
</template>
