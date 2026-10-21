<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { EditableMissingPrice, MissingPrice } from '@/modules/reports/report-types';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { useEditableMissingPrices } from '@/modules/assets/prices/use-editable-missing-prices';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import ScrollableDialogContent from '@/modules/core/table/ScrollableDialogContent.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import MissingPriceRefreshButton from '@/modules/reports/MissingPriceRefreshButton.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

const { items, isPinned } = defineProps<{
  items: MissingPrice[];
  isPinned: boolean;
}>();

defineSlots<{
  actions: (props: { items: EditableMissingPrice[] }) => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const sort = ref<DataTableSortData<EditableMissingPrice>>([]);

const { getAssetField } = useAssetInfoRetrieval();

const {
  clearError,
  errorMessages,
  formattedItems,
  getHistoricalPrices,
  refreshHistoricalPrice,
  refreshing,
  updatePrice,
} = useEditableMissingPrices({
  items: () => items,
  keyOf: createKey,
});

function createKey(item: MissingPrice): string {
  return item.fromAsset + item.toAsset + item.time;
}

const headers = computed<DataTableColumn<EditableMissingPrice>[]>(() => {
  const pinned = isPinned;
  return [
    {
      key: 'fromAsset',
      label: pinned ? t('common.asset') : t('profit_loss_report.actionable.missing_prices.headers.from_asset'),
      sortable: true,
    },
    ...(!pinned
      ? [
          {
            cellClass: pinned ? 'px-2' : '',
            key: 'toAsset',
            label: t('profit_loss_report.actionable.missing_prices.headers.to_asset'),
            sortable: true,
          },
          {
            key: 'time',
            label: t('common.datetime'),
            sortable: true,
          },
        ]
      : []),
    {
      align: 'end',
      cellClass: 'py-2',
      class: 'w-60',
      key: 'price',
      label: t('common.price'),
    },
  ];
});

useRememberTableSorting<EditableMissingPrice>(TableId.REPORTS_MISSING_PRICES, sort, headers);

onMounted(async () => {
  await getHistoricalPrices();
});
</script>

<template>
  <ScrollableDialogContent fill>
    <RuiDataTable
      v-model:sort="sort"
      :cols="headers"
      :rows="formattedItems"
      :dense="isPinned"
      row-attr="fromAsset"
      sticky-header
    >
      <template #item.fromAsset="{ row }">
        <template v-if="isPinned">
          <AssetDetails
            :asset="row.fromAsset"
            class="max-w-44!"
          />
          <div class="flex flex-wrap items-center gap-x-1.5 text-xs text-rui-text-secondary">
            <RuiIcon
              name="lu-arrow-right"
              size="12"
            />
            <span class="font-medium text-rui-text">{{ getAssetField(row.toAsset, 'symbol') || row.toAsset }}</span>
            <span
              aria-hidden="true"
              class="size-0.5 rounded-full bg-current"
            />
            <DateDisplay
              class="whitespace-nowrap"
              :timestamp="row.time"
            />
          </div>
        </template>
        <AssetDetails
          v-else
          :asset="row.fromAsset"
        />
      </template>
      <template #item.toAsset="{ row }">
        <AssetDetails
          :asset="row.toAsset"
          :display="{ inline: true, size: '20px' }"
        />
      </template>
      <template #item.time="{ row }">
        <DateDisplay
          class="whitespace-nowrap"
          :timestamp="row.time"
        />
      </template>
      <template #item.price="{ row }">
        <AmountInput
          v-model="row.price"
          class="text-left min-w-30"
          dense
          :disabled="row.useRefreshedHistoricalPrice"
          :label="t('profit_loss_report.actionable.missing_prices.input_price')"
          label-placement="hidden"
          :placeholder="t('profit_loss_report.actionable.missing_prices.input_price')"
          details="auto"
          :success-messages="row.saved ? [t('profit_loss_report.actionable.missing_prices.price_is_saved')] : []"
          :error-messages="errorMessages[createKey(row)]"
          data-testid="missing-price-input"
          @focus="clearError(row)"
          @update:model-value="clearError(row)"
          @blur="updatePrice(row)"
        >
          <template #append>
            <MissingPriceRefreshButton
              v-if="row.rateLimited"
              :disabled="!!row.price || refreshing"
              :loading="refreshing"
              @refresh="refreshHistoricalPrice(row)"
            />
          </template>
        </AmountInput>
      </template>
    </RuiDataTable>
    <template #footer>
      <slot
        name="actions"
        :items="formattedItems"
      />
    </template>
  </ScrollableDialogContent>
</template>
