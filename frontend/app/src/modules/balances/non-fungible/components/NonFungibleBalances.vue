<script setup lang="ts">
import NonFungibleBalancesFilter from '@/modules/accounts/balances/NonFungibleBalancesFilter.vue';
import { AssetAmountDisplay, FiatDisplay } from '@/modules/assets/amount-display/components';
import LatestPriceFormDialog from '@/modules/assets/prices/latest/LatestPriceFormDialog.vue';
import { IgnoredAssetHandlingType } from '@/modules/assets/types';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import NftDetails from '@/modules/balances/nft/NftDetails.vue';
import TableEmptyNotice from '@/modules/core/table/TableEmptyNotice.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { useTableEmptyState } from '@/modules/core/table/use-table-empty-state';
import SuccessDisplay from '@/modules/shell/components/display/SuccessDisplay.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';
import RowAppend from '@/modules/shell/components/RowAppend.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import { useNftAssetIgnoring } from '../use-nft-asset-ignoring';
import { useNftData } from '../use-nft-data';
import { useNftPriceManagement } from '../use-nft-price-management';
import NonFungibleBalancesActions from './NonFungibleBalancesActions.vue';

const { t } = useI18n({ useScope: 'global' });
const { useIsAssetIgnored } = useAssetsStore();

const {
  cols,
  currencySymbol,
  data,
  dataLoading,
  error,
  fetchData,
  modelIgnoredAssetsHandling,
  pagination,
  refreshNonFungibleBalances,
  sectionLoading,
  sort,
  totalValue,
} = useNftData();

const emptyState = useTableEmptyState({ error });

const selectionMode = ref<boolean>(false);

/** Hiding ignored or unignored NFTs can leave an empty table that is only a filter away from rows. */
const filtered = computed<boolean>(() => get(modelIgnoredAssetsHandling) !== IgnoredAssetHandlingType.NONE);

const {
  customPrice,
  hasCustomPrice,
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
        :section-loading="sectionLoading"
        @refresh="refreshNonFungibleBalances(true)"
      />
    </template>

    <TableFrame data-testid="nft-balances">
      <template #toolbar>
        <NonFungibleBalancesFilter
          v-model:selected="modelSelected"
          v-model:ignored-assets-handling="modelIgnoredAssetsHandling"
          v-model:selection-mode="selectionMode"
          @mass-ignore="massIgnore($event)"
        />
      </template>
      <RuiDataTable
        v-model:sort.external="sort"
        v-model:pagination.external="pagination"
        :model-value="selectionMode ? modelSelected : undefined"
        row-attr="id"
        dense
        class="bg-rui-surface"
        :cols="cols"
        :empty="emptyState"
        :rows="data"
        :loading="dataLoading"
        @update:model-value="modelSelected = $event ?? []"
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
        <template
          v-if="data.length > 0"
          #body.append
        >
          <RowAppend
            v-if="totalValue"
            :label-colspan="selectionMode ? 4 : 3"
            :label="t('common.total')"
            class-name="[&>td]:px-4 [&>td]:py-2 text-sm"
            :right-patch-colspan="2"
          >
            <FiatDisplay
              class="font-bold"
              :value="totalValue"
            />
          </RowAppend>
        </template>
        <template
          v-if="!error"
          #no-data
        >
          <TableEmptyNotice
            :icon="filtered ? 'lu-search-x' : 'lu-image'"
            :title="filtered ? t('non_fungible_balances.empty.filtered_title') : t('non_fungible_balances.empty.title')"
            :description="filtered ? t('non_fungible_balances.empty.filtered_description') : t('non_fungible_balances.empty.description')"
            :data-testid="filtered ? 'nft-balances-empty-filtered' : 'nft-balances-empty'"
          >
            <RuiButton
              v-if="filtered"
              variant="outlined"
              color="primary"
              data-testid="nft-balances-empty-show-all"
              @click="modelIgnoredAssetsHandling = IgnoredAssetHandlingType.NONE"
            >
              {{ t('non_fungible_balances.empty.show_all') }}
            </RuiButton>
          </TableEmptyNotice>
        </template>
      </RuiDataTable>
    </TableFrame>

    <LatestPriceFormDialog
      v-model:open="modelOpenPriceDialog"
      :editable-item="hasCustomPrice ? customPrice : null"
      :prefill="hasCustomPrice ? null : customPrice"
      disable-from-asset
      @refresh="fetchData()"
    />
  </TablePageLayout>
</template>
