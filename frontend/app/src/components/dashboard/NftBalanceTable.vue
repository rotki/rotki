<script setup lang="ts">
import DashboardExpandableTable from '@/components/dashboard/DashboardExpandableTable.vue';
import VisibleColumnsSelector from '@/components/dashboard/VisibleColumnsSelector.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import NftDetails from '@/components/helper/NftDetails.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import { useNftData } from '@/composables/dashboard/use-nft-data';
import { useNftTableConfig } from '@/composables/dashboard/use-nft-table-config';
import { Routes } from '@/router/routes';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { DashboardTableType } from '@/types/settings/frontend-settings';

const nonFungibleRoute = Routes.BALANCES_NON_FUNGIBLE;
const group = DashboardTableType.NFT;

const { t } = useI18n({ useScope: 'global' });
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const {
  data,
  fetchData,
  isLoading,
  loading,
  pagination,
  percentageOfCurrentGroup,
  percentageOfTotalNetValue,
  refreshNonFungibleBalances,
  totalUsdValue,
} = useNftData();

const { sort, tableHeaders } = useNftTableConfig(currencySymbol);

onMounted(async () => {
  await fetchData();
  await refreshNonFungibleBalances();
});

watch(loading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading)
    await fetchData();
});
</script>

<template>
  <DashboardExpandableTable>
    <template #title>
      <RefreshButton
        :loading="loading"
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
      <AmountDisplay
        v-if="totalUsdValue"
        :value="totalUsdValue"
        show-currency="symbol"
        fiat-currency="USD"
        class="text-h6 font-bold"
      />
    </template>

    <RuiDataTable
      v-model:sort.external="sort"
      v-model:pagination.external="pagination"
      :cols="tableHeaders"
      :rows="data"
      :loading="isLoading"
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
        <AmountDisplay
          v-if="row.priceAsset !== currencySymbol"
          :value="row.priceInAsset"
          :asset="row.priceAsset"
        />
        <span v-else>-</span>
      </template>
      <template #item.usdPrice="{ row }">
        <AmountDisplay
          is-asset-price
          :price-asset="row.priceAsset"
          :amount="row.priceInAsset"
          :value="row.usdPrice"
          show-currency="symbol"
          fiat-currency="USD"
        />
      </template>
      <template #item.percentageOfTotalNetValue="{ row }">
        <PercentageDisplay
          :value="percentageOfTotalNetValue(row.usdPrice)"
          :asset-padding="0.1"
        />
      </template>
      <template #item.percentageOfTotalCurrentGroup="{ row }">
        <PercentageDisplay
          :value="percentageOfCurrentGroup(row.usdPrice)"
          :asset-padding="0.1"
        />
      </template>
      <template #body.append>
        <RowAppend
          label-colspan="2"
          :label="t('common.total')"
          :right-patch-colspan="tableHeaders.length - 3"
          :is-mobile="false"
          class-name="[&>td]:p-4 text-sm"
        >
          <AmountDisplay
            v-if="totalUsdValue"
            :value="totalUsdValue"
            show-currency="symbol"
            fiat-currency="USD"
          />
        </RowAppend>
      </template>
    </RuiDataTable>
  </DashboardExpandableTable>
</template>
