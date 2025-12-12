<script setup lang="ts">
import type { Module } from '@/types/modules';
import NonFungibleBalancesFilter from '@/components/accounts/balances/NonFungibleBalancesFilter.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import SuccessDisplay from '@/components/display/SuccessDisplay.vue';
import NftDetails from '@/components/helper/NftDetails.vue';
import RowActions from '@/components/helper/RowActions.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import LatestPriceFormDialog from '@/components/price-manager/latest/LatestPriceFormDialog.vue';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useNftAssetIgnoring } from '../composables/use-nft-asset-ignoring';
import { useNftData } from '../composables/use-nft-data';
import { useNftPriceManagement } from '../composables/use-nft-price-management';
import NonFungibleBalancesActions from './NonFungibleBalancesActions.vue';

defineProps<{ modules: Module[] }>();

const { t } = useI18n({ useScope: 'global' });
const { useIsAssetIgnored } = useIgnoredAssetsStore();

// Data management
const {
  cols,
  currencySymbol,
  data,
  dataLoading,
  fetchData,
  ignoredAssetsHandling,
  pagination,
  refreshNonFungibleBalances,
  sectionLoading,
  sort,
  totalValue,
} = useNftData();

// Price management
const {
  customPrice,
  openPriceDialog,
  setPriceForm,
  showDeleteConfirmation,
} = useNftPriceManagement(fetchData);

// Asset ignoring
const {
  massIgnore,
  selected,
  toggleIgnoreAsset,
} = useNftAssetIgnoring(fetchData, ignoredAssetsHandling);

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
  <TablePageLayout :title="[t('navigation_menu.balances'), t('navigation_menu.balances_sub.non_fungible_balances')]">
    <template #buttons>
      <NonFungibleBalancesActions
        :modules="modules"
        :section-loading="sectionLoading"
        @refresh="refreshNonFungibleBalances(true)"
      />
    </template>

    <RuiCard>
      <NonFungibleBalancesFilter
        class="mb-4"
        :selected="selected"
        :ignored-assets-handling="ignoredAssetsHandling"
        @update:selected="selected = $event"
        @update:ignored-assets-handling="ignoredAssetsHandling = $event"
        @mass-ignore="massIgnore($event)"
      />
      <RuiDataTable
        v-model="selected"
        v-model:sort.external="sort"
        v-model:pagination.external="pagination"
        row-attr="id"
        outlined
        dense
        :cols="cols"
        :rows="data"
        :loading="dataLoading"
      >
        <template #item.name="{ row }">
          <NftDetails :identifier="row.id" />
        </template>
        <template #item.ignored="{ row }">
          <div class="flex justify-center">
            <RuiSwitch
              color="primary"
              hide-details
              :model-value="useIsAssetIgnored(row.id).value"
              @update:model-value="toggleIgnoreAsset(row)"
            />
          </div>
        </template>
        <template #item.priceInAsset="{ row }">
          <AmountDisplay
            v-if="row.priceAsset !== currencySymbol"
            :value="row.priceInAsset"
            :asset="row.priceAsset"
          />
          <span v-else>-</span>
        </template>
        <template #item.price="{ row }">
          <AmountDisplay
            :price-asset="row.priceAsset"
            :amount="row.priceInAsset"
            :value="row.price"
            is-asset-price
            show-currency="symbol"
            force-currency
          />
        </template>
        <template #item.actions="{ row }">
          <RowActions
            :delete-tooltip="t('assets.custom_price.delete.tooltip')"
            :edit-tooltip="t('assets.custom_price.edit.tooltip')"
            :delete-disabled="!row.manuallyInput"
            @delete-click="showDeleteConfirmation(row)"
            @edit-click="setPriceForm(row)"
          />
        </template>
        <template #item.manuallyInput="{ row }">
          <SuccessDisplay
            v-if="row.manuallyInput"
            class="mx-auto"
            success
          />
          <div v-else />
        </template>
        <template #body.append>
          <RowAppend
            v-if="totalValue"
            label-colspan="4"
            :label="t('common.total')"
            class="[&>td]:p-4"
            :right-patch-colspan="2"
          >
            <AmountDisplay
              :value="totalValue"
              show-currency="symbol"
              force-currency
            />
          </RowAppend>
        </template>
      </RuiDataTable>
    </RuiCard>

    <LatestPriceFormDialog
      v-model:open="openPriceDialog"
      :editable-item="customPrice"
      @refresh="fetchData()"
    />
  </TablePageLayout>
</template>
