<script setup lang="ts">
import { AssetAmountDisplay, FiatDisplay } from '@/modules/assets/amount-display/components';
import NftDetails from '@/modules/balances/nft/NftDetails.vue';
import { useNftData } from '@/modules/balances/non-fungible/use-nft-data';
import DashboardExpandableTable from '@/modules/dashboard/DashboardExpandableTable.vue';
import VisibleColumnsSelector from '@/modules/dashboard/VisibleColumnsSelector.vue';
import { DashboardTableType } from '@/modules/settings/types/frontend-settings';
import PercentageDisplay from '@/modules/shell/components/display/PercentageDisplay.vue';
import RefreshButton from '@/modules/shell/components/RefreshButton.vue';
import RowAppend from '@/modules/shell/components/RowAppend.vue';
import { Routes } from '@/router/routes';

const nonFungibleRoute = Routes.BALANCES_NON_FUNGIBLE;
const group = DashboardTableType.NFT;

const { t } = useI18n({ useScope: 'global' });

const {
  cols,
  currencySymbol,
  data,
  dataLoading,
  fetchData,
  percentageOfCurrentGroup,
  percentageOfTotalNetValue,
  refreshNonFungibleBalances,
  sectionLoading,
  sort,
  pagination,
  totalValue,
} = useNftData({ dashboard: true });

onMounted(async () => {
  await fetchData();
  await refreshNonFungibleBalances();
});

watch(sectionLoading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading)
    await fetchData();
});
</script>

<template>
  <DashboardExpandableTable>
    <template #title>
      <RefreshButton
        :loading="sectionLoading"
        :tooltip="t('nft_balance_table.refresh')"
        @refresh="refreshNonFungibleBalances(true)"
      />
      {{ t('nft_balance_table.title') }}
      <RouterLink :to="nonFungibleRoute">
        <RuiButton
          variant="text"
          icon
          class="ml-2"
        >
          <RuiIcon name="lu-chevron-right" />
        </RuiButton>
      </RouterLink>
    </template>
    <template #details>
      <VisibleColumnsSelector :group="group" />
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
      :empty="{ description: t('data_table.no_data') }"
      row-attr="id"
      sticky-header
      outlined
      dense
    >
      <template #item.name="{ row }">
        <NftDetails :identifier="row.id" />
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
          class-name="[&>td]:p-4 text-sm"
        >
          <FiatDisplay
            v-if="totalValue"
            :value="totalValue"
          />
        </RowAppend>
      </template>
    </RuiDataTable>
  </DashboardExpandableTable>
</template>
