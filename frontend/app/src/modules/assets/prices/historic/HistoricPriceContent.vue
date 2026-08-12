<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { HistoricalPrice, HistoricalPriceFormPayload } from '@/modules/assets/prices/price-types';
import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import dayjs from 'dayjs';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import HistoricPriceFormDialog from '@/modules/assets/prices/historic/HistoricPriceFormDialog.vue';
import { HistoricPriceFilterKeys, useHistoricPriceFields } from '@/modules/assets/prices/use-historic-price-fields';
import { useHistoricPrices } from '@/modules/assets/prices/use-historic-price-manager';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
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
  {
    cellClass: '!text-xs !text-rui-text-secondary',
    key: 'wasWorth',
    label: '',
  },
  {
    align: 'end',
    key: 'price',
    label: t('common.price'),
    sortable: true,
  },
  {
    key: 'toAsset',
    label: t('price_table.headers.to_asset'),
    sortable: true,
  },
  {
    cellClass: '!text-xs !text-rui-text-secondary',
    key: 'on',
    label: '',
  },
  {
    key: 'timestamp',
    label: t('common.datetime'),
    sortable: true,
  },
  {
    class: 'w-[3rem]',
    key: 'actions',
    label: '',
  },
]);

useRememberTableSorting<HistoricalPrice>(TableId.HISTORIC_PRICES, sort, headers);

const emptyPrice: () => HistoricalPriceFormPayload = () => ({
  fromAsset: '',
  price: '',
  sourceType: PriceOracle.MANUAL,
  timestamp: dayjs().unix(),
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

const router = useRouter();
const route = useRoute();

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

onMounted(async () => {
  const query = get(route).query;

  if (query.add) {
    add();
    await router.replace({ query: {} });
  }
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
            size="lg"
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
        size="lg"
        data-testid="historic-price-add"
        @click="add()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('price_management.dialog.add_title') }}
      </RuiButton>
    </template>
    <RuiCard>
      <PillFilterBar
        v-model:matches="matches"
        class="mb-4"
        :fields="fields"
        :labels="pillLabels"
      />
      <RuiDataTable
        v-model:sort="sort"
        outlined
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
        <template #item.toAsset="{ row }">
          <AssetDetails :asset="row.toAsset" />
        </template>
        <template #item.timestamp="{ row }">
          <DateDisplay :timestamp="row.timestamp" />
        </template>
        <template #item.price="{ row }">
          <ValueDisplay :value="row.price" />
        </template>
        <template #item.wasWorth>
          {{ t('price_table.was_worth') }}
        </template>
        <template #item.on>
          {{ t('price_table.on') }}
        </template>
        <template #item.actions="{ row }">
          <RowActions
            :disabled="loading"
            :delete-tooltip="t('price_table.actions.delete.tooltip')"
            :edit-tooltip="t('price_table.actions.edit.tooltip')"
            @delete-click="showDeleteConfirmation(row)"
            @edit-click="edit(row)"
          />
        </template>
      </RuiDataTable>
    </RuiCard>

    <HistoricPriceFormDialog
      v-model="modelValue"
      :edit-mode="editMode"
      @refresh="refresh({ modified: true })"
    />
  </TablePageLayout>
</template>
