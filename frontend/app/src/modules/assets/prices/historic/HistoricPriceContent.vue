<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { HistoricalPrice, HistoricalPriceFormPayload } from '@/modules/assets/prices/price-types';
import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import { AssetAmountDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import HistoricPriceFormDialog from '@/modules/assets/prices/historic/HistoricPriceFormDialog.vue';
import { priceDecimals } from '@/modules/assets/prices/price-decimals';
import { HistoricPriceFilterKeys, useHistoricPriceFields } from '@/modules/assets/prices/use-historic-price-fields';
import { useHistoricPrices } from '@/modules/assets/prices/use-historic-price-manager';
import { useAddQuery } from '@/modules/core/common/use-add-query';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { t } = useI18n({ useScope: 'global' });

const sort = ref<DataTableSortData<HistoricalPrice>>([
  {
    column: 'timestamp',
    direction: 'desc' as const,
  },
]);

const headers = computed<DataTableColumn<HistoricalPrice>[]>(() => [
  {
    key: 'fromAsset',
    label: t('price_table.headers.from_asset'),
    sortable: true,
  },
  // one amount, "0.03271 EUR", where "was worth", a number, an asset and "on" split one sentence
  {
    align: 'end',
    key: 'price',
    label: t('common.price'),
    sortable: true,
  },
  {
    key: 'timestamp',
    label: t('common.datetime'),
    sortable: true,
  },
  {
    align: 'end',
    class: 'w-12',
    key: 'actions',
    label: '',
  },
]);

useRememberTableSorting<HistoricalPrice>(TableId.HISTORIC_PRICES, sort, headers);

const emptyPrice: () => HistoricalPriceFormPayload = () => ({
  fromAsset: '',
  price: '',
  sourceType: PriceOracle.MANUAL,
  timestamp: Math.floor(Date.now() / 1000),
  toAsset: '',
});

const modelValue = ref<HistoricalPriceFormPayload>();
const editMode = ref<boolean>(false);

const fields = useHistoricPriceFields();
const pillLabels = usePillBarLabels();

/**
 * The bar owns the bag, and the table reads the pair out of it.
 *
 * Deliberately not a writable computed over a `{ fromAsset, toAsset }` ref: a pill exists before it
 * has a value, and a bridge that rebuilds the object from the two keys drops that pending state, so
 * the pill vanished the moment it was added.
 */
const matches = ref<MatchedKeywordWithBehaviour<string>>({});

const filter = computed<{ fromAsset?: string; toAsset?: string }>(() => {
  const bag = get(matches);
  const picked = (key: string): string | undefined => {
    const value = bag[key];
    return typeof value === 'string' && value !== '' ? value : undefined;
  };

  return {
    fromAsset: picked(HistoricPriceFilterKeys.FROM_ASSET),
    toAsset: picked(HistoricPriceFilterKeys.TO_ASSET),
  };
});

const { deletePrice, items, loading, refresh } = useHistoricPrices(t, filter);

function add() {
  set(modelValue, {
    ...emptyPrice(),
    fromAsset: get(filter).fromAsset ?? '',
    toAsset: get(filter).toAsset ?? '',
  });
  set(editMode, false);
}

function edit(item: HistoricalPrice) {
  set(modelValue, {
    ...item,
    price: item.price.toFixed() ?? '',
    sourceType: PriceOracle.MANUAL,
  });
  set(editMode, true);
}

const { show } = useConfirmStore();

function showDeleteConfirmation(item: HistoricalPrice) {
  show(
    {
      message: t('price_table.delete.dialog.message'),
      title: t('price_table.delete.dialog.title'),
    },
    () => deletePrice(item),
  );
}

const { consumeAddQuery } = useAddQuery(add);

onMounted(async () => {
  await consumeAddQuery();
});
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.manage_prices'), t('navigation_menu.manage_prices_sub.historic_prices')]"
  >
    <template #buttons>
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            :loading="loading"
            @click="refresh()"
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
        data-testid="historic-price-add"
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
          {{ t('price_management.historic.hint') }}
        </HintMenuIcon>
        <PillFilterBar
          v-model:matches="matches"
          class="flex-1 min-w-48 md:min-w-96"
          :fields="fields"
          :labels="pillLabels"
        />
      </template>
      <RuiDataTable
        v-model:sort="sort"
        dense
        :cols="headers"
        :loading="loading"
        :rows="items"
        row-attr="fromAsset"
        data-testid="historic-price-table"
      >
        <template #item.fromAsset="{ row }">
          <AssetDetails :asset="row.fromAsset" />
        </template>
        <template #item.timestamp="{ row }">
          <DateDisplay :timestamp="row.timestamp" />
        </template>
        <template #item.price="{ row }">
          <AssetAmountDisplay
            :amount="row.price"
            :asset="row.toAsset"
            :decimals="priceDecimals(row.price)"
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

    <HistoricPriceFormDialog
      v-model="modelValue"
      :edit-mode="editMode"
      @refresh="refresh({ modified: true })"
    />
  </TablePageLayout>
</template>
