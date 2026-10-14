<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { ManualPriceFormPayload, ManualPriceWithUsd } from '@/modules/assets/prices/price-types';
import { omit } from 'es-toolkit';
import { AssetAmountDisplay, FiatDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { isNft } from '@/modules/assets/nft-utils';
import LatestPriceFormDialog from '@/modules/assets/prices/latest/LatestPriceFormDialog.vue';
import { priceDecimals } from '@/modules/assets/prices/price-decimals';
import { useLatestPrices } from '@/modules/assets/prices/use-latest-price-manager';
import NftDetails from '@/modules/balances/nft/NftDetails.vue';
import { useAddQuery } from '@/modules/core/common/use-add-query';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { useCommonTableProps } from '@/modules/core/table/use-common-table-props';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useSetting } from '@/modules/settings/use-setting';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { t } = useI18n({ useScope: 'global' });

const filter = ref<string>();
const { editableItem, openDialog } = useCommonTableProps<ManualPriceFormPayload>();

const currencySymbol = useSetting('currencySymbol');

const sort = ref<DataTableSortData<ManualPriceWithUsd>>([]);

const headers = computed<DataTableColumn<ManualPriceWithUsd>[]>(() => [
  {
    key: 'fromAsset',
    label: t('price_table.headers.from_asset'),
    sortable: true,
  },
  // one amount, "3,000.00 USDC", where an "is worth", a number and an asset column split one sentence
  {
    align: 'end',
    key: 'price',
    label: t('common.price'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'usdPrice',
    label: t('common.price_in_symbol', { symbol: get(currencySymbol) }),
    sortable: true,
  },
  {
    align: 'end',
    class: 'w-12',
    key: 'actions',
    label: '',
  },
]);

useRememberTableSorting<ManualPriceWithUsd>(TableId.LATEST_PRICES, sort, headers);

const { deletePrice, items, loading, refreshCurrentPrices, refreshing } = useLatestPrices(t, filter);

const { show } = useConfirmStore();

function showDeleteConfirmation(item: ManualPriceWithUsd) {
  show(
    {
      message: t('price_table.delete.dialog.message'),
      title: t('price_table.delete.dialog.title'),
    },
    () => deletePrice(item),
  );
}

function add() {
  set(editableItem, null);
  set(openDialog, true);
}

function edit(item: ManualPriceWithUsd) {
  set(editableItem, omit({
    ...item,
    price: item.price.toFixed() ?? '',
  }, ['id', 'usdPrice']));
  set(openDialog, true);
}

const { consumeAddQuery } = useAddQuery(add);

onMounted(async () => {
  await refreshCurrentPrices();
  await consumeAddQuery();
});
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.manage_prices'), t('navigation_menu.manage_prices_sub.latest_prices')]">
    <template #buttons>
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            color="primary"
            variant="outlined"
            :loading="loading || refreshing"
            @click="refreshCurrentPrices()"
          >
            <template #prepend>
              <RuiIcon name="lu-refresh-ccw" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('price_table.refresh_tooltip') }}
      </RuiTooltip>

      <RuiButton
        color="primary"
        data-testid="latest-price-add"
        @click="add()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('price_management.dialog.add_title') }}
      </RuiButton>
    </template>

    <TableFrame>
      <template #toolbar>
        <HintMenuIcon>
          {{ t('price_management.latest.hint') }}
        </HintMenuIcon>
        <AssetSelect
          v-model="filter"
          class="w-full sm:w-80"
          dense
          :source="{ nfts: 'include' }"
          :label="t('price_management.from_asset')"
          label-placement="hidden"
          :placeholder="t('price_management.from_asset')"
          clearable
          hide-details
          data-testid="latest-price-filter-from"
        />
      </template>
      <RuiDataTable
        v-model:sort="sort"
        dense
        :cols="headers"
        :loading="loading || refreshing"
        :rows="items"
        row-attr="id"
        data-testid="latest-price-table"
      >
        <template #item.fromAsset="{ row }">
          <NftDetails
            v-if="isNft(row.fromAsset)"
            :identifier="row.fromAsset"
          />
          <AssetDetails
            v-else
            class="[&_.avatar]:ml-1.5 [&_.avatar]:mr-2"
            :asset="row.fromAsset"
          />
        </template>
        <template #item.price="{ row }">
          <AssetAmountDisplay
            :amount="row.price"
            :asset="row.toAsset"
            :decimals="priceDecimals(row.price)"
          />
        </template>
        <template #item.usdPrice="{ row }">
          <FiatDisplay
            :value="row.usdPrice"
            :loading="!row.usdPrice || row.usdPrice.lt(0)"
            :price-asset="row.fromAsset"
            :format="{ decimals: row.usdPrice ? priceDecimals(row.usdPrice) : undefined }"
          />
        </template>
        <template #item.actions="{ row }">
          <RowActions
            align="end"
            :disabled="loading"
            :delete-tooltip="t('price_table.actions.delete.tooltip')"
            :edit-tooltip="t('price_table.actions.edit.tooltip')"
            @delete-click="showDeleteConfirmation(row)"
            @edit-click="edit(row)"
          />
        </template>
      </RuiDataTable>
    </TableFrame>

    <LatestPriceFormDialog
      v-model:open="openDialog"
      :editable-item="editableItem"
      @refresh="refreshCurrentPrices()"
    />
  </TablePageLayout>
</template>
