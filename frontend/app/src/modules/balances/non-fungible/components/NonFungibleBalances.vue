<script setup lang="ts">
import type { Module } from '@/modules/core/common/modules';
import NonFungibleBalancesFilter from '@/modules/accounts/balances/NonFungibleBalancesFilter.vue';
import { AssetAmountDisplay, FiatDisplay } from '@/modules/assets/amount-display/components';
import LatestPriceFormDialog from '@/modules/assets/prices/latest/LatestPriceFormDialog.vue';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import NftDetails from '@/modules/balances/nft/NftDetails.vue';
import SuccessDisplay from '@/modules/shell/components/display/SuccessDisplay.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';
import RowAppend from '@/modules/shell/components/RowAppend.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import { useNftAssetIgnoring } from '../use-nft-asset-ignoring';
import { useNftData } from '../use-nft-data';
import { useNftPriceManagement } from '../use-nft-price-management';
import NonFungibleBalancesActions from './NonFungibleBalancesActions.vue';

defineProps<{ modules: Module[] }>();

const { t } = useI18n({ useScope: 'global' });
const { useIsAssetIgnored } = useAssetsStore();

const {
  cols,
  currencySymbol,
  data,
  dataLoading,
  fetchData,
  modelIgnoredAssetsHandling,
  pagination,
  refreshNonFungibleBalances,
  sectionLoading,
  sort,
  totalValue,
} = useNftData();

const {
  customPrice,
  modelOpenPriceDialog,
  setPriceForm,
  showDeleteConfirmation,
} = useNftPriceManagement(fetchData);

const {
  massIgnore,
  modelSelected,
  toggleIgnoreAsset,
} = useNftAssetIgnoring(fetchData, modelIgnoredAssetsHandling);

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
        :selected="modelSelected"
        :ignored-assets-handling="modelIgnoredAssetsHandling"
        @update:selected="modelSelected = $event"
        @update:ignored-assets-handling="modelIgnoredAssetsHandling = $event"
        @mass-ignore="massIgnore($event)"
      />
      <RuiDataTable
        v-model="modelSelected"
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
            <FiatDisplay :value="totalValue" />
          </RowAppend>
        </template>
      </RuiDataTable>
    </RuiCard>

    <LatestPriceFormDialog
      v-model:open="modelOpenPriceDialog"
      :editable-item="customPrice"
      @refresh="fetchData()"
    />
  </TablePageLayout>
</template>
